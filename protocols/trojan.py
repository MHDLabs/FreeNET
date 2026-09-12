import os
import hashlib
import hmac
import struct
import asyncio
import ipaddress
from fastapi import WebSocket
from core import Target, relay_to_target, Relay

_TROJAN_PASSWORD = os.environ.get("TROJAN_PASSWORD", "")
_TROJAN_PASSWORD_HASH = hashlib.sha224(_TROJAN_PASSWORD.encode("utf-8")).hexdigest().encode("ascii")

async def handle(ws: WebSocket):
    await ws.accept()
    buffer = bytearray()

    async def recv_exact(n, timeout=15.0):
        nonlocal buffer
        while len(buffer) < n:
            if len(buffer) > 4096:
                raise ConnectionError("Handshake too large")
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
            except asyncio.TimeoutError:
                raise ConnectionError("Handshake timeout")
            except Exception:
                raise ConnectionError("Disconnected")

            if msg["type"] == "websocket.disconnect":
                raise ConnectionError("Disconnected")
            if msg["type"] == "websocket.receive":
                if "bytes" in msg and msg["bytes"]:
                    buffer.extend(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    buffer.extend(msg["text"].encode("utf-8"))
                else:
                    raise ConnectionError("Empty message")
            else:
                raise ConnectionError("Unexpected message type")

        res = bytes(buffer[:n])
        del buffer[:n]
        return res

    try:
        client_hash = await recv_exact(56)
        crlf1 = await recv_exact(2)
        if crlf1 != b"\r\n":
            return

        if not hmac.compare_digest(client_hash, _TROJAN_PASSWORD_HASH):
            return

        cmd = await recv_exact(1)
        if cmd != b"\x01":
            return

        atyp = await recv_exact(1)
        if atyp == b"\x01":
            addr_bytes = await recv_exact(4)
            host = str(ipaddress.IPv4Address(addr_bytes))
        elif atyp == b"\x03":
            domain_len = (await recv_exact(1))[0]
            if domain_len == 0:
                return
            addr_bytes = await recv_exact(domain_len)
            host = addr_bytes.decode("utf-8")
        elif atyp == b"\x04":
            addr_bytes = await recv_exact(16)
            host = str(ipaddress.IPv6Address(addr_bytes))
        else:
            return

        port_bytes = await recv_exact(2)
        port = struct.unpack("!H", port_bytes)[0]
        if not (1 <= port <= 65535):
            return

        crlf2 = await recv_exact(2)
        if crlf2 != b"\r\n":
            return

        initial_payload = bytes(buffer)
        buffer.clear()

    except Exception:
        return

    try:
        target = Target(host=host, port=port, network="tcp")
    except Exception:
        return

    initial_sent = False

    async def client_receive():
        nonlocal initial_sent
        if not initial_sent:
            initial_sent = True
            if initial_payload:
                return initial_payload
        try:
            msg = await ws.receive()
        except Exception:
            return None

        if msg["type"] == "websocket.disconnect":
            return None
        if msg["type"] == "websocket.receive":
            if "bytes" in msg and msg["bytes"]:
                return msg["bytes"]
            if "text" in msg and msg["text"]:
                return msg["text"].encode("utf-8")
        return None

    async def client_send(data: bytes):
        try:
            await ws.send_bytes(data)
        except Exception:
            pass

    async def client_close():
        try:
            await ws.close()
        except Exception:
            pass

    try:
        await relay_to_target(
            target,
            client_receive=client_receive,
            client_send=client_send,
            client_close=client_close,
            timeout=10.0,
            relay=Relay()
        )
    except Exception:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
