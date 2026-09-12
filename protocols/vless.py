import os
import struct
import asyncio
import ipaddress
from uuid import UUID
from fastapi import WebSocket
from core import Target, relay_to_target, Relay

_vless_uuid_str = os.environ.get("VLESS_UUID", "")
try:
    _VLESS_UUID_BYTES = UUID(_vless_uuid_str).bytes if _vless_uuid_str else b""
except Exception:
    _VLESS_UUID_BYTES = b""

class WSReader:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.buffer = bytearray()

    async def read(self, n: int) -> bytes:
        while len(self.buffer) < n:
            if len(self.buffer) > 4096:
                raise ConnectionError("Header too large")
            try:
                msg = await asyncio.wait_for(self.ws.receive(), timeout=30.0)
            except asyncio.TimeoutError:
                raise ConnectionError("Timeout")
            if msg["type"] == "websocket.disconnect":
                raise ConnectionError("Disconnected")
            if msg["type"] == "websocket.receive":
                if "bytes" in msg and msg["bytes"]:
                    self.buffer.extend(msg["bytes"])
                elif "text" in msg and msg["text"]:
                    raise ConnectionError("Text message not supported")
                else:
                    raise ConnectionError("Empty message")
            else:
                raise ConnectionError("Unexpected message type")
        res = bytes(self.buffer[:n])
        del self.buffer[:n]
        return res

    def get_remaining(self) -> bytes:
        return bytes(self.buffer)

async def handle(ws: WebSocket):
    await ws.accept()
    reader = WSReader(ws)

    try:
        version = (await reader.read(1))[0]
        if version != 0:
            return

        req_uuid = await reader.read(16)
        if req_uuid != _VLESS_UUID_BYTES:
            return

        opt_len = (await reader.read(1))[0]
        if opt_len > 0:
            await reader.read(opt_len)

        command = (await reader.read(1))[0]
        if command != 0x01:
            return

        port = struct.unpack("!H", await reader.read(2))[0]
        if not (1 <= port <= 65535):
            return

        atyp = (await reader.read(1))[0]
        if atyp == 0x01:
            addr_bytes = await reader.read(4)
            host = str(ipaddress.IPv4Address(addr_bytes))
        elif atyp == 0x02:
            domain_len = (await reader.read(1))[0]
            if domain_len == 0:
                return
            addr_bytes = await reader.read(domain_len)
            try:
                host = addr_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return
        elif atyp == 0x03:
            addr_bytes = await reader.read(16)
            host = str(ipaddress.IPv6Address(addr_bytes))
        else:
            return

        initial_payload = reader.get_remaining()
    except Exception:
        return

    try:
        target = Target(host=host, port=port, network="tcp")
    except Exception:
        return

    try:
        await ws.send_bytes(b'\x00\x00')
    except Exception:
        return

    initial_sent = False

    async def client_receive():
        nonlocal initial_sent
        if not initial_sent:
            initial_sent = True
            if initial_payload:
                return initial_payload

        while True:
            try:
                msg = await ws.receive()
            except Exception:
                return None
            if msg["type"] == "websocket.disconnect":
                return None
            if msg["type"] == "websocket.receive":
                if "bytes" in msg:
                    if msg["bytes"]:
                        return msg["bytes"]
                    else:
                        return None
                if "text" in msg:
                    continue
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
