import asyncio
import os
import re
import socket
import time

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

XHTTP_BUF = 512 * 1024
DOWNLINK_QUEUE_MAX = 512
SESSION_IDLE_TIMEOUT = 60
REAPER_INTERVAL = 10
TCP_CONNECT_TIMEOUT = 10.0
SOCK_BUF_SIZE = 512 * 1024

FLOW_MIN_HW = 256 * 1024
FLOW_MAX_HW = 16 * 1024 * 1024
FLOW_START_HW = 2 * 1024 * 1024
FLOW_FAST_DRAIN_MS = 2.0
FLOW_SLOW_DRAIN_MS = 25.0

RELAY_BUF = 256 * 1024
PACKET_UP_HIGH_WATER = 2 * 1024 * 1024

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

VLESS_UUID_ENV = os.environ.get("VLESS_UUID", "").strip()

router = APIRouter()

xhttp_sessions = {}
XHTTP_LOCK = asyncio.Lock()
_reaper_started = False


def _match_uuid(uuid):
    if not UUID_RE.match(uuid):
        return False
    if VLESS_UUID_ENV and uuid.lower() != VLESS_UUID_ENV.lower():
        return False
    return True


async def parse_vless_header(chunk):
    if len(chunk) < 24:
        raise ValueError("chunk too small")
    pos = 1 + 16
    addon_len = chunk[pos]
    pos += 1 + addon_len
    command = chunk[pos]
    pos += 1
    port = int.from_bytes(chunk[pos:pos + 2], "big")
    pos += 2
    addr_type = chunk[pos]
    pos += 1
    if addr_type == 1:
        address = ".".join(str(b) for b in chunk[pos:pos + 4])
        pos += 4
    elif addr_type == 2:
        dlen = chunk[pos]
        pos += 1
        address = chunk[pos:pos + dlen].decode("utf-8", errors="ignore")
        pos += dlen
    elif addr_type == 3:
        ab = chunk[pos:pos + 16]
        pos += 16
        address = ":".join(f"{ab[i]:02x}{ab[i + 1]:02x}" for i in range(0, 16, 2))
    else:
        raise ValueError(f"unknown addr type: {addr_type}")
    return command, address, port, chunk[pos:]


def _tune_socket(writer):
    sock = writer.transport.get_extra_info("socket")
    if not sock:
        return
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCK_BUF_SIZE)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCK_BUF_SIZE)
    except OSError:
        pass


class _AdaptiveFlow:
    __slots__ = ("high_water", "last_drain_ms")

    def __init__(self):
        self.high_water = FLOW_START_HW
        self.last_drain_ms = 0.0

    def should_drain(self, buf_size):
        return buf_size > self.high_water

    async def drain(self, writer):
        t0 = time.monotonic()
        await writer.drain()
        elapsed_ms = (time.monotonic() - t0) * 1000
        self.last_drain_ms = elapsed_ms
        if elapsed_ms < FLOW_FAST_DRAIN_MS:
            self.high_water = min(FLOW_MAX_HW, int(self.high_water * 1.5) + 65536)
        elif elapsed_ms > FLOW_SLOW_DRAIN_MS:
            self.high_water = max(FLOW_MIN_HW, self.high_water // 2)


async def _open_tcp_from_header(first_chunk):
    _command, address, port, payload = await parse_vless_header(first_chunk)
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(address, port), timeout=TCP_CONNECT_TIMEOUT
    )
    _tune_socket(writer)
    if payload:
        writer.write(payload)
        await writer.drain()
    return reader, writer


async def _get_or_create_session(session_id):
    async with XHTTP_LOCK:
        sess = xhttp_sessions.get(session_id)
        if sess is not None:
            sess["last_seen"] = time.time()
            return sess
        sess = {
            "writer": None,
            "downlink_task": None,
            "down_q": asyncio.Queue(maxsize=DOWNLINK_QUEUE_MAX),
            "last_seen": time.time(),
            "tcp_open": False,
            "closed": False,
            "seq_buf": {},
            "next_seq": 0,
            "flow": None,
        }
        xhttp_sessions[session_id] = sess
        return sess


async def _teardown(session_id):
    async with XHTTP_LOCK:
        sess = xhttp_sessions.pop(session_id, None)
    if not sess:
        return
    sess["closed"] = True
    task = sess.get("downlink_task")
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    writer = sess.get("writer")
    if writer:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
    dq = sess.get("down_q")
    if dq:
        try:
            dq.put_nowait(None)
        except Exception:
            pass


async def _reaper():
    while True:
        await asyncio.sleep(REAPER_INTERVAL)
        now = time.time()
        async with XHTTP_LOCK:
            stale = [
                sid for sid, s in xhttp_sessions.items()
                if now - s["last_seen"] > SESSION_IDLE_TIMEOUT and not s.get("tcp_open")
            ]
        for sid in stale:
            await _teardown(sid)


def _ensure_reaper():
    global _reaper_started
    if not _reaper_started:
        asyncio.create_task(_reaper())
        _reaper_started = True


async def _pump_tcp_to_queue(session_id, reader, down_q):
    first = True
    try:
        while True:
            data = await reader.read(XHTTP_BUF)
            if not data:
                break
            payload = (b"\x00\x00" + data) if first else data
            first = False
            await down_q.put(payload)
    except (asyncio.CancelledError, Exception):
        pass
    finally:
        await _teardown(session_id)


async def _open_tcp_for_session(session_id, sess, first_chunk):
    reader, writer = await _open_tcp_from_header(first_chunk)
    sess["writer"] = writer
    sess["tcp_open"] = True
    sess["downlink_task"] = asyncio.create_task(
        _pump_tcp_to_queue(session_id, reader, sess["down_q"])
    )


def _downstream_gen(sess):
    async def gen():
        while True:
            chunk = await sess["down_q"].get()
            if chunk is None:
                break
            sess["last_seen"] = time.time()
            yield chunk
    return gen()


_RESP_HEADERS = {
    "content-type": "application/grpc",
    "cache-control": "no-cache, no-store",
    "x-accel-buffering": "no",
    "server": "cloudflare",
}


@router.get("/xhttp-siz10/{mode}/{uuid}/{session_id}")
async def xhttp_downlink(mode: str, uuid: str, session_id: str, request: Request):
    _ensure_reaper()
    if mode not in ("packet-up", "stream-up"):
        raise HTTPException(status_code=404, detail="unknown mode")
    if not _match_uuid(uuid):
        raise HTTPException(status_code=404, detail="not found")
    sess = await _get_or_create_session(session_id)
    if sess.get("closed"):
        raise HTTPException(status_code=404, detail="session closed")
    return StreamingResponse(
        _downstream_gen(sess),
        headers=_RESP_HEADERS,
        media_type=_RESP_HEADERS["content-type"],
    )


@router.post("/xhttp-siz10/packet-up/{uuid}/{session_id}/{seq}")
async def packet_up_upload(uuid: str, session_id: str, seq: int, request: Request):
    _ensure_reaper()
    if not _match_uuid(uuid):
        raise HTTPException(status_code=404, detail="not found")
    sess = await _get_or_create_session(session_id)
    if sess.get("closed"):
        raise HTTPException(status_code=404, detail="session closed")

    sess["last_seen"] = time.time()
    body = await request.body()
    if not body:
        return {"ok": True}

    try:
        if sess["writer"] is None:
            if seq != 0:
                sess["seq_buf"][seq] = body
                return {"ok": True, "buffered": True}
            await _open_tcp_for_session(session_id, sess, body)
            nxt = 1
            while nxt in sess["seq_buf"]:
                pending = sess["seq_buf"].pop(nxt)
                sess["writer"].write(pending)
                nxt += 1
            sess["next_seq"] = nxt
            return {"ok": True, "connected": True}

        if seq == sess["next_seq"]:
            sess["writer"].write(body)
            sess["next_seq"] += 1
            while sess["next_seq"] in sess["seq_buf"]:
                pending = sess["seq_buf"].pop(sess["next_seq"])
                sess["writer"].write(pending)
                sess["next_seq"] += 1
        else:
            sess["seq_buf"][seq] = body

        if sess["writer"].transport.get_write_buffer_size() > PACKET_UP_HIGH_WATER:
            await sess["writer"].drain()
    except Exception:
        await _teardown(session_id)
        raise HTTPException(status_code=502, detail="write failed")

    return {"ok": True}


@router.post("/xhttp-siz10/stream-up/{uuid}/{session_id}")
async def stream_up_upload(uuid: str, session_id: str, request: Request):
    _ensure_reaper()
    if not _match_uuid(uuid):
        raise HTTPException(status_code=404, detail="not found")
    sess = await _get_or_create_session(session_id)
    if sess.get("closed"):
        raise HTTPException(status_code=404, detail="session closed")

    flow = sess.get("flow")
    if flow is None:
        flow = _AdaptiveFlow()
        sess["flow"] = flow

    writer = sess["writer"]

    try:
        async for chunk in request.stream():
            if not chunk:
                continue
            sess["last_seen"] = time.time()

            if writer is None:
                await _open_tcp_for_session(session_id, sess, chunk)
                writer = sess["writer"]
                continue

            writer.write(chunk)
            if flow.should_drain(writer.transport.get_write_buffer_size()):
                await flow.drain(writer)
    except HTTPException:
        await _teardown(session_id)
        raise
    except Exception:
        await _teardown(session_id)
        raise HTTPException(status_code=502, detail="stream error")

    return {"ok": True}


async def _relay_ws_to_tcp(websocket, writer):
    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes") or (msg.get("text") or "").encode()
            if not data:
                continue
            writer.write(data)
            if writer.transport.get_write_buffer_size() > RELAY_BUF:
                await writer.drain()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        try:
            writer.write_eof()
        except Exception:
            pass


async def _relay_tcp_to_ws(websocket, reader):
    first = True
    try:
        while True:
            data = await reader.read(RELAY_BUF)
            if not data:
                break
            payload = (b"\x00\x00" + data) if first else data
            first = False
            await websocket.send_bytes(payload)
    except Exception:
        pass


async def ws_handler(websocket: WebSocket, uuid: str):
    await websocket.accept()

    if not _match_uuid(uuid):
        await websocket.close(code=1008, reason="not authorized")
        return

    writer = None
    try:
        first_msg = await asyncio.wait_for(websocket.receive(), timeout=15.0)
        if first_msg["type"] == "websocket.disconnect":
            return
        first_chunk = first_msg.get("bytes") or (first_msg.get("text") or "").encode()
        if not first_chunk:
            return

        _command, address, port, payload = await parse_vless_header(first_chunk)

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), timeout=TCP_CONNECT_TIMEOUT
        )
        _tune_socket(writer)

        if payload:
            writer.write(payload)
            await writer.drain()

        done, pending = await asyncio.wait(
            {
                asyncio.create_task(_relay_ws_to_tcp(websocket, writer)),
                asyncio.create_task(_relay_tcp_to_ws(websocket, reader)),
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        pass
    except Exception:
        pass
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
