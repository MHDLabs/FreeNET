import os
import sys
import json
import uuid
import secrets
import string
import logging
import base64
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FreeNET")

DATA_DIR = Path(os.environ.get("FREENET_DATA_DIR") or "/data")
os.environ["FREENET_DATA_DIR"] = str(DATA_DIR)
IDENTITY_PATH = DATA_DIR / "identity.json"


def generate_token(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def load_or_create_identity() -> dict:
    if not DATA_DIR.exists() or not DATA_DIR.is_dir():
        logger.error(
            "Data directory %s is not available. A persistent volume is required.",
            DATA_DIR,
        )
        sys.exit(1)

    if IDENTITY_PATH.exists():
        try:
            with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Identity is not a JSON object")

            required_keys = ("uuid", "trojan_password", "subscription_token")
            if not all(k in data for k in required_keys):
                raise ValueError("Missing required identity fields")

            if (
                not isinstance(data["uuid"], str)
                or not isinstance(data["trojan_password"], str)
                or not isinstance(data["subscription_token"], str)
            ):
                raise ValueError("Identity fields must be strings")

            parsed_uuid = uuid.UUID(data["uuid"])

            if not data["trojan_password"] or not data["subscription_token"]:
                raise ValueError("Secrets cannot be empty")

            return {
                "uuid": str(parsed_uuid),
                "trojan_password": data["trojan_password"],
                "subscription_token": data["subscription_token"],
            }
        except Exception as e:
            logger.error(
                "Identity file is corrupted or invalid. Refusing to regenerate to protect existing links. Error: %s",
                e,
            )
            sys.exit(1)

    logger.info("Generating new identity...")
    identity = {
        "uuid": str(uuid.uuid4()),
        "trojan_password": secrets.token_urlsafe(24),
        "subscription_token": generate_token(24),
    }

    tmp_path = IDENTITY_PATH.with_name(IDENTITY_PATH.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(identity, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, IDENTITY_PATH)
    except Exception as e:
        logger.error(
            "Failed to persist identity file. Refusing to start with ephemeral identity. Error: %s",
            e,
        )
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        sys.exit(1)

    return identity


IDENTITY = load_or_create_identity()
os.environ["VLESS_UUID"] = IDENTITY["uuid"]
os.environ["TROJAN_PASSWORD"] = IDENTITY["trojan_password"]

try:
    _IDENTITY_UUID = uuid.UUID(IDENTITY["uuid"])
except Exception as e:
    logger.error("Invalid identity UUID. Error: %s", e)
    sys.exit(1)

from protocols import vless, xhttp, trojan
import core

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _uuid_matches(value: str) -> bool:
    try:
        return uuid.UUID(value) == _IDENTITY_UUID
    except Exception:
        return False


@app.on_event("startup")
async def startup() -> None:
    logger.info("FreeNET started")
    logger.info("Subscription URL: /sub/%s...", IDENTITY["subscription_token"][:4])


@app.get("/")
async def root():
    return PlainTextResponse("FreeNET")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/vless/{client_uuid}")
async def ws_vless(ws: WebSocket, client_uuid: str):
    if not _uuid_matches(client_uuid):
        await ws.close(code=1008, reason="Invalid UUID")
        return
    await vless.handle(ws)


@app.websocket("/trojan/{client_uuid}")
async def ws_trojan(ws: WebSocket, client_uuid: str):
    if not _uuid_matches(client_uuid):
        await ws.close(code=1008, reason="Invalid UUID")
        return
    await trojan.handle(ws)


async def _handle_xhttp_request(client_uuid: str, request: Request):
    if not _uuid_matches(client_uuid):
        return Response(content="Not Found", status_code=404)
    return await xhttp.handle(request)


@app.api_route("/xhttp/{client_uuid}", methods=["GET", "POST"])
async def xhttp_base(client_uuid: str, request: Request):
    return await _handle_xhttp_request(client_uuid, request)


@app.api_route("/xhttp/{client_uuid}/{path:path}", methods=["GET", "POST"])
async def xhttp_path(client_uuid: str, request: Request):
    return await _handle_xhttp_request(client_uuid, request)


def _extract_public_host(request: Request) -> str:
    raw = request.headers.get("x-forwarded-host")
    if not raw:
        raw = request.headers.get("host", "localhost")

    raw = raw.split(",", 1)[0].strip()
    if not raw:
        return "localhost"

    if "://" in raw:
        raw = raw.split("://", 1)[1].split("/", 1)[0]

    if raw.startswith("["):
        end = raw.find("]")
        if end != -1:
            return raw[1:end]
        return raw.strip("[]")

    if raw.count(":") == 1:
        return raw.rsplit(":", 1)[0]

    return raw


def _format_url_host(host: str) -> str:
    return f"[{host}]" if ":" in host else host


def _build_query(params: dict) -> str:
    return "&".join(f"{key}={quote(str(value))}" for key, value in params.items())


@app.get("/sub/{token}")
async def subscription(token: str, request: Request):
    try:
        token_valid = secrets.compare_digest(
            token.encode("utf-8"),
            IDENTITY["subscription_token"].encode("utf-8"),
        )
    except Exception:
        token_valid = False

    if not token_valid:
        return Response(content="Not Found", status_code=404)

    host = _extract_public_host(request)
    url_host = _format_url_host(host)
    links = []

    vless_params = {
        "encryption": "none",
        "security": "tls",
        "type": "ws",
        "host": url_host,
        "path": f"/vless/{IDENTITY['uuid']}",
        "sni": host,
        "fp": "chrome",
        "alpn": "h2,http/1.1",
    }
    links.append(
        f"vless://{IDENTITY['uuid']}@{url_host}:443?{_build_query(vless_params)}#FreeNET-VLESS"
    )

    trojan_params = {
        "security": "tls",
        "type": "ws",
        "host": url_host,
        "path": f"/trojan/{IDENTITY['uuid']}",
        "sni": host,
        "fp": "chrome",
        "alpn": "h2,http/1.1",
    }
    links.append(
        f"trojan://{IDENTITY['trojan_password']}@{url_host}:443?{_build_query(trojan_params)}#FreeNET-Trojan"
    )

    xhttp_params = {
        "encryption": "none",
        "security": "tls",
        "type": "xhttp",
        "mode": "packet-up",
        "host": url_host,
        "path": f"/xhttp/{IDENTITY['uuid']}",
        "sni": host,
        "fp": "chrome",
        "alpn": "h2,http/1.1",
    }
    links.append(
        f"vless://{IDENTITY['uuid']}@{url_host}:443?{_build_query(xhttp_params)}#FreeNET-XHTTP"
    )

    try:
        stats = core.get_global_stats()
        uptime = core.format_uptime(stats.uptime_seconds())
        up = core.format_bytes(stats.total_upload)
        down = core.format_bytes(stats.total_download)
        up_bytes = int(stats.total_upload)
        down_bytes = int(stats.total_download)
    except Exception:
        uptime, up, down = "0m", "0B", "0B"
        up_bytes, down_bytes = 0, 0

    status_text = f"📊 FreeNET • {uptime} • ↑{up} ↓{down}"
    status_link = (
        "vless://00000000-0000-0000-0000-000000000000@127.0.0.1:1"
        f"?type=tcp&security=none&encryption=none#{quote(status_text)}"
    )
    links.append(status_link)

    payload = "\n".join(links)
    encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

    headers = {
        "Subscription-Userinfo": f"upload={up_bytes}; download={down_bytes}; total=0; expire=0",
        "Profile-Title": base64.b64encode(status_text.encode("utf-8")).decode("utf-8"),
        "Cache-Control": "no-store",
    }

    return Response(content=encoded, media_type="text/plain", headers=headers)


if __name__ == "__main__":
    import uvicorn

    try:
        port = int(os.environ.get("PORT", "8000"))
    except (TypeError, ValueError):
        port = 8000

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        workers=1,
    )
