# 🚀 FreeNET

> Tiny, simple and lightweight VLESS server built for Railway.

FreeNET is a minimal, single-UUID VLESS server that speaks three transports — WebSocket, XHTTP `packet-up`, and XHTTP `stream-up` — and exposes all three through a single subscription endpoint. It has no admin panel, no bot, no user management and no per-user limits. You set one UUID, deploy it, and hand out a subscription link.

It is a stripped-down companion to a larger project (X4G), kept intentionally small.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-deploy-0B0D0E?logo=railway&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

- 🔐 **Single UUID** — configured entirely through an environment variable
- 🌐 **Three transports out of the box**
  - `vless-ws` (WebSocket)
  - `xhttp-packet-up` (XHTTP, sequence-numbered upload)
  - `xhttp-stream-up` (XHTTP, single continuous POST upload)
- 📦 **One subscription URL** — returns all three transports as base64 (with an optional `?raw=1` plain-text view)
- 🧵 **Adaptive flow control** for XHTTP `stream-up` to reduce syscall overhead under load
- ♻️ **Session reaper** that cleans idle XHTTP sessions automatically
- 🚫 **No panel. No bot. No database. No limits.**
- 🐳 **Dockerfile included**, ready for Railway

---

## 🚀 Quick Start

### Run locally with Docker

```bash
docker build -t freenet .

docker run --rm -p 8000:8000 \
  -e VLESS_UUID=00000000-0000-0000-0000-000000000000 \
  freenet
```

### Run locally with Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export VLESS_UUID=00000000-0000-0000-0000-000000000000
uvicorn main:app --host 0.0.0.0 --port 8000
```

Once it's running, the subscription is available at:

```
http://localhost:8000/sub/00000000-0000-0000-0000-000000000000
```

---

## ☁️ Railway Deployment

FreeNET is designed to run on Railway with zero extra configuration.

1. Fork or push this repository to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo**, then pick the repository.
3. Railway will detect the `Dockerfile` and build it automatically.
4. Open the service → **Variables** → add:

   | Key          | Value                                  |
   | ------------ | -------------------------------------- |
   | `VLESS_UUID` | a UUID you generate (see below)        |

5. Open the service → **Settings → Networking** → **Generate Domain**.
6. Railway sets `RAILWAY_PUBLIC_DOMAIN` automatically once a domain exists.
7. Healthcheck is already declared in `railway.json` (`/health`).

You can generate a UUID anywhere, e.g.:

```bash
python -c "import uuid; print(uuid.uuid4())"
```

After the service comes up, the subscription lives at:

```
https://<your-railway-domain>/sub/<VLESS_UUID>
```

---

## ⚙️ Configuration

All configuration is done through environment variables.

| Variable              | Required | Default        | Description                                                       |
| --------------------- | :------: | -------------- | ----------------------------------------------------------------- |
| `VLESS_UUID`          |    ✅    | —              | The UUID that clients connect with. Must be a valid UUID format.  |
| `VLESS_FP`            |    ❌    | `firefox`      | uTLS fingerprint embedded in the generated share links.           |
| `VLESS_PORT`          |    ❌    | `443`          | Port written into the share links.                                |
| `VLESS_SNI`           |    ❌    | request host   | SNI used in the share links. Falls back to the request `Host`.    |
| `VLESS_WS_ALPN`       |    ❌    | `http/1.1`     | ALPN for the WebSocket transport.                                 |
| `VLESS_XHTTP_ALPN`    |    ❌    | `h2,http/1.1`  | ALPN for both XHTTP transports.                                   |
| `PORT`                |    ❌    | `8000`         | HTTP port. Railway sets this automatically.                       |
| `RAILWAY_PUBLIC_DOMAIN` |  ❌    | `localhost`    | Used only for the startup log line. Set by Railway automatically. |

> ⚠️ **If `VLESS_UUID` is missing or malformed, the app refuses to start.** This is intentional — running with a random UUID would silently invalidate every previously shared subscription link.

---

## 📡 Subscription

The subscription endpoint returns **all three transports** for the same UUID, base64-encoded:

```
GET /sub/{uuid}
```

If `{uuid}` does not match `VLESS_UUID`, the server returns `404`.

You can also request the raw (non-base64) form for debugging:

```
GET /sub/{uuid}?raw=1
```

Example response (decoded):

```
vless://<uuid>@<host>:443?encryption=none&security=tls&type=ws&host=<host>&path=/ws/<uuid>&sni=<host>&fp=firefox&alpn=http/1.1#FreeNET-WS
vless://<uuid>@<host>:443?encryption=none&security=tls&type=xhttp&mode=packet-up&host=<host>&path=/xhttp-siz10/packet-up/<uuid>&sni=<host>&fp=firefox&alpn=h2,http/1.1#FreeNET-PacketUp
vless://<uuid>@<host>:443?encryption=none&security=tls&type=xhttp&mode=stream-up&host=<host>&path=/xhttp-siz10/stream-up/<uuid>&sni=<host>&fp=firefox&alpn=h2,http/1.1#FreeNET-StreamUp
```

### Endpoints

| Method | Path                                                  | Purpose                          |
| ------ | ----------------------------------------------------- | -------------------------------- |
| GET    | `/`                                                   | Liveness string (`OK`)           |
| GET    | `/health`                                             | Healthcheck JSON                 |
| GET    | `/sub/{uuid}`                                         | Subscription (base64 by default) |
| WS     | `/ws/{uuid}`                                          | VLESS over WebSocket             |
| GET    | `/xhttp-siz10/{mode}/{uuid}/{session_id}`             | XHTTP downlink (`packet-up` / `stream-up`) |
| POST   | `/xhttp-siz10/packet-up/{uuid}/{session_id}/{seq}`    | XHTTP `packet-up` uplink         |
| POST   | `/xhttp-siz10/stream-up/{uuid}/{session_id}`          | XHTTP `stream-up` uplink         |

---

## 🏗️ Project Structure

```text
FreeNET/
├── main.py           → App entrypoint, healthcheck, startup validation
├── tunnel.py         → VLESS WebSocket + XHTTP (packet-up / stream-up) relay
├── subscription.py   → Builds VLESS share links and serves /sub/{uuid}
├── requirements.txt  → Python dependencies
├── Dockerfile        → Python 3.11-slim image
├── railway.json      → Railway build/deploy configuration
├── .dockerignore     → Keeps the image small
├── .gitignore        → Keeps the repository clean
└── README.md         → You are here
```

---

## 🛠️ Local Development

FreeNET is intentionally small — there is nothing to migrate, seed, or admin.

```bash
git clone https://github.com/MHDLabs/FreeNET.git
cd FreeNET

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export VLESS_UUID="$(python -c 'import uuid; print(uuid.uuid4())')"
uvicorn main:app --reload --port 8000
```

Then hit `http://127.0.0.1:8000/sub/$VLESS_UUID` to see the generated subscription.

---

## 📦 Docker

Build and run without relying on any external tooling:

```bash
docker build -t freenet:latest .

docker run -d --name freenet \
  -p 8000:8000 \
  -e VLESS_UUID=00000000-0000-0000-0000-000000000000 \
  freenet:latest
```

The container runs as a non-root user (`freenet`) and listens on `$PORT` (defaults to `8000`).

---

## ❓ Troubleshooting

**The container exits immediately on startup.**
Check the logs. It almost certainly means `VLESS_UUID` is missing or malformed. FreeNET refuses to boot without a valid UUID.

**The subscription returns 404.**
The `{uuid}` in the URL must match `VLESS_UUID` exactly. Both are compared case-insensitively but everything else must line up.

**The client connects but no traffic flows on XHTTP.**
Some CDNs rewrite or buffer HTTP POST bodies. If `packet-up` misbehaves behind a particular proxy, try `stream-up` first, and vice versa.

**Links generated behind Railway point to `localhost`.**
Make sure you generated a public domain on the Railway service. The subscription endpoint uses the incoming request's `Host` header — if you access it through an internal URL, the host will be internal.

---

## ⚠️ Notes

- FreeNET holds **one UUID**. There is no per-user quota, no IP limit, no speed limit, no expiry, no rotation.
- If the UUID leaks, your only recovery is to change `VLESS_UUID` and restart the service — all existing clients will lose access.
- The `VLESS_UUID` value is a secret. Do not commit it to the repository, and do not paste it into a public issue. Store it as a Railway environment variable.
- FreeNET is meant to be tiny. If you need a panel, a Telegram bot, sub-groups, quotas or per-user limits, use the larger X4G project instead.

---

## 📄 License

This project is licensed under the MIT License.

---

Made with ❤️ and a little bit of ☕ by **MHDLabs**

