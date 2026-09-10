import base64
import os
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter()

UUID_RE = __import__("re").compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

FP = os.environ.get("VLESS_FP", "firefox").strip() or "firefox"
PORT = int(os.environ.get("VLESS_PORT", "443"))
WS_ALPN = os.environ.get("VLESS_WS_ALPN", "http/1.1").strip() or "http/1.1"
XHTTP_ALPN = os.environ.get("VLESS_XHTTP_ALPN", "h2,http/1.1").strip() or "h2,http/1.1"


def _host(request: Request) -> str:
    h = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if h:
        return h.split(":")[0]
    return os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")


def _sni(request: Request) -> str:
    return os.environ.get("VLESS_SNI", "").strip() or _host(request)


def _build_link(uuid: str, host: str, sni: str, protocol: str, remark: str) -> str:
    if protocol == "vless-ws":
        path = f"/ws/{uuid}"
        params = {
            "encryption": "none",
            "security": "tls",
            "type": "ws",
            "host": host,
            "path": path,
            "sni": sni,
            "fp": FP,
            "alpn": WS_ALPN,
        }
    else:
        mode = protocol.replace("xhttp-", "")
        path = f"/xhttp-siz10/{mode}/{uuid}"
        params = {
            "encryption": "none",
            "security": "tls",
            "type": "xhttp",
            "mode": mode,
            "host": host,
            "path": path,
            "sni": sni,
            "fp": FP,
            "alpn": XHTTP_ALPN,
        }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"vless://{uuid}@{host}:{PORT}?{query}#{quote(remark)}"


@router.get("/sub/{uuid}")
async def subscription(uuid: str, request: Request):
    if not UUID_RE.match(uuid):
        raise HTTPException(status_code=404, detail="not found")

    configured = os.environ.get("VLESS_UUID", "").strip()
    if configured and uuid.lower() != configured.lower():
        raise HTTPException(status_code=404, detail="not found")

    host = _host(request)
    sni = _sni(request)

    links = [
        _build_link(uuid, host, sni, "vless-ws", "FreeNET-WS"),
        _build_link(uuid, host, sni, "xhttp-packet-up", "FreeNET-PacketUp"),
        _build_link(uuid, host, sni, "xhttp-stream-up", "FreeNET-StreamUp"),
    ]

    raw = "\n".join(links)

    if request.query_params.get("raw") == "1":
        return Response(
            content=raw,
            media_type="text/plain; charset=utf-8",
            headers={"cache-control": "no-store"},
        )

    content = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "cache-control": "no-store",
            "profile-title": quote("FreeNET"),
            "profile-update-interval": "12",
        },
    )
