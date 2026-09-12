import asyncio
import os
import struct
import ipaddress
import time
from typing import Dict, Optional
from uuid import UUID
from fastapi import Request
from fastapi.responses import Response, StreamingResponse
from core import Target, open_target, get_global_stats

_vless_uuid_str = os.environ.get("VLESS_UUID", "")
try:
    _VLESS_UUID_BYTES = UUID(_vless_uuid_str).bytes if _vless_uuid_str else b""
except Exception:
    _VLESS_UUID_BYTES = b""

MAX_SESSIONS = 10000
MAX_SEQ_GAP = 1000
MAX_PACKET_SIZE = 2 * 1024 * 1024
MAX_HEADER_SIZE = 4096
MAX_BUFFERED_BYTES = 8 * 1024 * 1024
SESSION_TIMEOUT = 300

_sessions: Dict[str, "XHTTPSession"] = {}
_cleanup_task_started = False

def _parse_vless_header(data: bytes):
    if len(data) < 18:
        return None, None, None
    if data[0] != 0:
        return None, None, None
    if data[1:17] != _VLESS_UUID_BYTES:
        return None, None, None
    opt_len = data[17]
    offset = 18 + opt_len
    if len(data) < offset + 4:
        return None, None, None
    if data[offset] != 0x01:
        return None, None, None
    port = struct.unpack("!H", data[offset+1:offset+3])[0]
    atyp = data[offset+3]
    offset += 4

    host = None
    if atyp == 0x01:
        if len(data) < offset + 4:
            return None, None, None
        host = ".".join(str(b) for b in data[offset:offset+4])
        offset += 4
    elif atyp == 0x02:
        if len(data) < offset + 1:
            return None, None, None
        domain_len = data[offset]
        offset += 1
        if len(data) < offset + domain_len:
            return None, None, None
        try:
            host = data[offset:offset+domain_len].decode("utf-8")
        except UnicodeDecodeError:
            return None, None, None
        offset += domain_len
    elif atyp == 0x03:
        if len(data) < offset + 16:
            return None, None, None
        host = str(ipaddress.IPv6Address(data[offset:offset+16]))
        offset += 16
    else:
        return None, None, None

    return host, port, data[offset:]

async def _target_pump(reader: asyncio.StreamReader, queue: asyncio.Queue, stats):
    try:
        while True:
            data = await reader.read(16384)
            if not data:
                break
            stats.add_download(len(data))
            await queue.put(data)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
    finally:
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

class XHTTPSession:
    def __init__(self, session_id: str, mode: str):
        self.session_id = session_id
        self.mode = mode
        self.created_at = time.time()
        self.last_seen = time.time()

        self.target_reader: Optional[asyncio.StreamReader] = None
        self.target_writer: Optional[asyncio.StreamWriter] = None
        self.target_connected = False

        self.downlink_queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self.downlink_connected = False
        self.downlink_task: Optional[asyncio.Task] = None

        self.next_seq = 0
        self.seq_buf: Dict[int, bytes] = {}
        self.buffered_bytes = 0

        self.closed = False
        self._lock = asyncio.Lock()

    async def close(self):
        if self.closed:
            return
        self.closed = True
        if self.downlink_task and not self.downlink_task.done():
            self.downlink_task.cancel()
        if self.target_writer:
            try:
                self.target_writer.close()
                await self.target_writer.wait_closed()
            except Exception:
                pass
        try:
            self.downlink_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

async def _cleanup_sessions():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        dead = [sid for sid, s in _sessions.items() if now - s.last_seen > SESSION_TIMEOUT]
        for sid in dead:
            sess = _sessions.pop(sid, None)
            if sess:
                await sess.close()

def _ensure_cleanup():
    global _cleanup_task_started
    if not _cleanup_task_started:
        asyncio.create_task(_cleanup_sessions())
        _cleanup_task_started = True

async def handle(request: Request):
    _ensure_cleanup()
    stats = get_global_stats()
    path = request.scope.get("path", "")
    parts = [p for p in path.split("/") if p]

    session_id = None
    seq_str = None

    if len(parts) >= 3:
        session_id = parts[2]
    if len(parts) >= 4:
        seq_str = parts[3]

    if not session_id:
        session_id = request.query_params.get("session_id")
    if not seq_str:
        seq_str = request.query_params.get("seq")

    mode = request.query_params.get("mode", "packet-up")

    if not session_id:
        return Response(content="Missing session_id", status_code=400)

    if len(session_id) < 8 or len(session_id) > 128:
        return Response(content="Invalid session_id", status_code=400)

    sess = _sessions.get(session_id)
    if not sess:
        if len(_sessions) >= MAX_SESSIONS:
            return Response(content="Too many sessions", status_code=503)
        sess = XHTTPSession(session_id, mode)
        _sessions[session_id] = sess

    sess.last_seen = time.time()
    method = request.method

    if method == "GET":
        if sess.downlink_connected:
            return Response(content="Downlink already connected", status_code=409)
        sess.downlink_connected = True

        async def downlink_stream():
            try:
                while True:
                    chunk = await sess.downlink_queue.get()
                    if chunk is None:
                        break
                    yield chunk
            except asyncio.CancelledError:
                pass
            finally:
                sess.downlink_connected = False
                asyncio.create_task(sess.close())

        return StreamingResponse(
            downlink_stream(),
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-cache, no-store",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked"
            }
        )

    elif method == "POST":
        if mode == "packet-up":
            body = bytearray()
            try:
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > MAX_PACKET_SIZE:
                        await sess.close()
                        return Response(content="Packet too large", status_code=413)
            except asyncio.CancelledError:
                await sess.close()
                raise
            except Exception:
                await sess.close()
                return Response(content="Upload error", status_code=400)

            if seq_str is None and sess.target_connected:
                return Response(content="Missing seq", status_code=400)

            try:
                seq = int(seq_str) if seq_str is not None else 0
                if seq < 0:
                    return Response(content="Invalid seq", status_code=400)
            except ValueError:
                return Response(content="Invalid seq", status_code=400)

            async with sess._lock:
                if sess.closed:
                    return Response(content="Session closed", status_code=410)

                if not sess.target_connected:
                    if seq == 0:
                        host, port, payload = _parse_vless_header(bytes(body))
                        if not host:
                            await sess.close()
                            return Response(content="Invalid VLESS header", status_code=400)
                        try:
                            target = Target(host=host, port=port, network="tcp")
                            t_reader, t_writer = await open_target(target, timeout=10.0)
                            sess.target_reader = t_reader
                            sess.target_writer = t_writer
                            sess.target_connected = True
                            sess.downlink_task = asyncio.create_task(_target_pump(t_reader, sess.downlink_queue, stats))
                            if payload:
                                stats.add_upload(len(payload))
                                t_writer.write(payload)
                                await t_writer.drain()
                            sess.next_seq = 1
                            while sess.next_seq in sess.seq_buf:
                                data = sess.seq_buf.pop(sess.next_seq)
                                sess.buffered_bytes -= len(data)
                                stats.add_upload(len(data))
                                t_writer.write(data)
                                await t_writer.drain()
                                sess.next_seq += 1
                        except Exception:
                            await sess.close()
                            return Response(content="Target connect failed", status_code=502)
                    else:
                        if seq - 1 > MAX_SEQ_GAP:
                            await sess.close()
                            return Response(content="Sequence gap too large", status_code=400)
                        if sess.buffered_bytes + len(body) > MAX_BUFFERED_BYTES:
                            await sess.close()
                            return Response(content="Buffer limit exceeded", status_code=400)
                        sess.seq_buf[seq] = bytes(body)
                        sess.buffered_bytes += len(body)
                else:
                    if seq < sess.next_seq:
                        pass
                    elif seq == sess.next_seq:
                        stats.add_upload(len(body))
                        sess.target_writer.write(bytes(body))
                        await sess.target_writer.drain()
                        sess.next_seq += 1
                        while sess.next_seq in sess.seq_buf:
                            data = sess.seq_buf.pop(sess.next_seq)
                            sess.buffered_bytes -= len(data)
                            stats.add_upload(len(data))
                            sess.target_writer.write(data)
                            await sess.target_writer.drain()
                            sess.next_seq += 1
                    else:
                        if seq - sess.next_seq > MAX_SEQ_GAP:
                            await sess.close()
                            return Response(content="Sequence gap too large", status_code=400)
                        if sess.buffered_bytes + len(body) > MAX_BUFFERED_BYTES:
                            await sess.close()
                            return Response(content="Buffer limit exceeded", status_code=400)
                        sess.seq_buf[seq] = bytes(body)
                        sess.buffered_bytes += len(body)
            return Response(content='{"ok":true}', media_type="application/json")

        elif mode == "stream-up":
            if not sess.target_connected:
                header_buf = bytearray()
                header_parsed = False
                try:
                    async for chunk in request.stream():
                        if not chunk:
                            break

                        if not header_parsed:
                            header_buf.extend(chunk)
                            host, port, payload = _parse_vless_header(bytes(header_buf))
                            if host is not None:
                                header_parsed = True
                                try:
                                    target = Target(host=host, port=port, network="tcp")
                                    t_reader, t_writer = await open_target(target, timeout=10.0)
                                    sess.target_reader = t_reader
                                    sess.target_writer = t_writer
                                    sess.target_connected = True
                                    sess.downlink_task = asyncio.create_task(_target_pump(t_reader, sess.downlink_queue, stats))
                                    if payload:
                                        stats.add_upload(len(payload))
                                        t_writer.write(payload)
                                        await t_writer.drain()
                                except Exception:
                                    await sess.close()
                                    return Response(content="Target connect failed", status_code=502)
                            else:
                                if len(header_buf) > MAX_HEADER_SIZE:
                                    await sess.close()
                                    return Response(content="Header too large or invalid", status_code=400)
                        else:
                            stats.add_upload(len(chunk))
                            sess.target_writer.write(chunk)
                            await sess.target_writer.drain()
                except asyncio.CancelledError:
                    await sess.close()
                    raise
                except Exception:
                    await sess.close()
                    return Response(content="Stream error", status_code=400)

                if not header_parsed:
                    await sess.close()
                    return Response(content="Invalid VLESS header", status_code=400)

                if sess.target_connected and sess.target_writer:
                    try:
                        sess.target_writer.close()
                        await sess.target_writer.wait_closed()
                    except Exception:
                        pass
            else:
                try:
                    async for chunk in request.stream():
                        if not chunk:
                            break
                        stats.add_upload(len(chunk))
                        sess.target_writer.write(chunk)
                        await sess.target_writer.drain()
                except asyncio.CancelledError:
                    await sess.close()
                    raise
                except Exception:
                    await sess.close()
                    return Response(content="Stream error", status_code=502)

                if sess.target_connected and sess.target_writer:
                    try:
                        sess.target_writer.close()
                        await sess.target_writer.wait_closed()
                    except Exception:
                        pass

            return Response(content='{"ok":true}', media_type="application/json")

        else:
            return Response(content="Unsupported mode", status_code=400)
    else:
        return Response(content="Method not allowed", status_code=405)
