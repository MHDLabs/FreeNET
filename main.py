import logging
import os
import re

from fastapi import FastAPI

from subscription import router as sub_router
from tunnel import router as tunnel_router, ws_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FreeNET")

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

VLESS_UUID = os.environ.get("VLESS_UUID", "").strip()
if not VLESS_UUID:
    raise RuntimeError("VLESS_UUID environment variable is required")
if not UUID_RE.match(VLESS_UUID):
    raise RuntimeError("VLESS_UUID is not a valid UUID")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.include_router(sub_router)
app.include_router(tunnel_router)
app.add_api_websocket_route("/ws/{uuid}", ws_handler)


@app.get("/")
async def root():
    return "OK"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def _startup():
    host = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")
    logger.info("FreeNET started")
    logger.info(f"UUID: {VLESS_UUID}")
    logger.info(f"Subscription: https://{host}/sub/{VLESS_UUID}")
    logger.info("Protocols: vless-ws, xhttp-packet-up, xhttp-stream-up")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
        workers=1,
    )
