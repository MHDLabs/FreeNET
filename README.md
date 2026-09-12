# 🚀 FreeNET

> Tiny, simple and lightweight VLESS / XHTTP / Trojan proxy server built for Railway.
> **Deploy → Get Subscription → Use → Forget**

[🇮🇷 فارسی](README-fa.md)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi\&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker\&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-deploy-0B0D0E?logo=railway\&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 🚀 Quick Start

FreeNET is made for people who want a proxy server without managing a full panel.

### 1. Deploy to Railway

Deploy this repository to Railway and add a persistent Volume mounted at:

```text
/data
```

The volume is important because FreeNET stores its identity and traffic statistics there.

### 2. Let FreeNET generate everything

On the first start, FreeNET automatically creates:

```text
/data/identity.json
```

It contains:

```json
{
  "uuid": "...",
  "trojan_password": "...",
  "subscription_token": "..."
}
```

You do **not** need to create these manually.

### 3. Get your subscription

Read:

```text
/data/identity.json
```

and copy the value of:

```text
subscription_token
```

Then open:

```text
https://<YOUR-RAILWAY-DOMAIN>/sub/<subscription_token>
```

Add that URL to your client as a subscription.

That's it. ❤️

---

## ☁️ Railway Deployment

FreeNET is designed around Railway's HTTP/HTTPS networking.

### What you need

* A Railway service
* The included `Dockerfile`
* A persistent Volume mounted at `/data`
* A public Railway domain

Railway provides the listening port through:

```text
$PORT
```

FreeNET binds to:

```text
0.0.0.0
```

Healthcheck:

```text
/health
```

### Persistent data

FreeNET uses:

```text
/data/identity.json
/data/stats.json
```

The identity must persist because your VLESS UUID, Trojan password and subscription token are generated once and reused.

Without persistent storage, a new identity can be generated after the data is lost and previously shared links may stop working.

### TLS

TLS is handled by Railway.

Clients connect through the Railway domain using HTTPS/WSS.

---

## 🧩 What is FreeNET?

FreeNET is a minimal proxy server for people who simply want one working deployment.

It is **not** a full VPN panel.

There is no need to manage:

* users
* databases
* quotas
* expiry dates
* admin dashboards
* billing systems
* per-user monitoring

The idea is simple:

```text
Deploy
  ↓
Get subscription
  ↓
Use it
```

FreeNET intentionally stays small.

---

## ✨ Features

* 🔐 Automatic VLESS UUID generation
* 🔑 Automatic Trojan password generation
* 🎟️ Automatic subscription token generation
* 🌐 VLESS over WebSocket
* ⚡ XHTTP support
* 🐇 Trojan over WebSocket
* 📡 One subscription URL
* 📊 Global upload/download statistics
* ⏱️ Uptime display
* 💾 Persistent `/data` storage
* 🐳 Docker-ready
* ☁️ Railway-ready
* 🚫 No panel
* 🚫 No database
* 🚫 No user management
* 🚫 No per-user monitoring

---

## 🆚 Why FreeNET?

There are already many capable panel-based projects such as:

* X4G
* RVG
* StanNG
* SpiderPanel
* Lunel

They solve a different problem: managing users, quotas, expiry, dashboards, subscriptions and other operational features.

FreeNET intentionally does less.

```text
Panel-style projects:

Panel
 ↓
Users
 ↓
Database
 ↓
Management
 ↓
Monitoring
```

FreeNET:

```text
Deploy
 ↓
Subscription
 ↓
Done
```

FreeNET is not trying to replace full-featured panels.

It is for the person who says:

> **"I don't need a panel. I just want a working proxy server."**

---

## 🌐 Supported Protocols

FreeNET currently provides:

```text
VLESS
XHTTP
Trojan
```

All proxy traffic is relayed over TCP.

### VLESS

VLESS is served over WebSocket.

Endpoint:

```text
/vless/{uuid}
```

The subscription uses:

```text
type=ws
security=tls
```

TLS is provided by Railway.

---

### XHTTP

XHTTP is served through HTTP requests.

Endpoints:

```text
/xhttp/{uuid}
/xhttp/{uuid}/{path}
```

Supported methods:

```text
GET
POST
```

Supported modes:

```text
packet-up
stream-up
```

The subscription currently provides the `packet-up` configuration.

XHTTP does not require a separate public TCP port.

---

### Trojan

Trojan is served over WebSocket.

Endpoint:

```text
/trojan/{uuid}
```

The Trojan password is generated automatically and stored in:

```text
/data/identity.json
```

No separate public TCP port is required.

---

## 📡 Subscription

Subscription endpoint:

```text
/sub/{token}
```

The subscription token is separate from the VLESS UUID.

Example:

```text
https://example.up.railway.app/sub/AbCdEfGhIjKlMnOpQrStUvWx
```

The response is Base64-encoded and contains the available proxy configurations.

Currently:

```text
VLESS WebSocket
Trojan WebSocket
XHTTP packet-up
```

---

### 📊 Status Node

The subscription also includes a small display-only node such as:

```text
📊 FreeNET • 18d • ↑42.6GB ↓183.2GB
```

It shows the instance's:

* uptime
* total upload
* total download

This is **not a real proxy node** and is not intended for connecting.

---

### Subscription Headers

FreeNET also returns subscription metadata such as:

```text
Subscription-Userinfo
Profile-Title
```

Clients such as v2rayN can use the subscription URL directly.

---

## 📊 Global Statistics

FreeNET only tracks statistics for the whole instance.

There is **no per-user tracking**.

Tracked values:

```text
Total Upload
Total Download
Uptime
```

Statistics are stored in:

```text
/data/stats.json
```

Upload and download counters persist when the `/data` volume persists.

Uptime represents the current process uptime and resets after a service restart.

---

## ⚙️ Configuration

FreeNET is intentionally light on configuration.

| Variable           |         Required | Default        | Purpose                                    |
| ------------------ | ---------------: | -------------- | ------------------------------------------ |
| `PORT`             | Railway-provided | `8000` locally | HTTP listen port                           |
| `FREENET_DATA_DIR` |               No | `/data`        | Directory used for identity and statistics |

### Automatically managed identity

These values are generated and managed automatically:

```text
VLESS UUID
Trojan Password
Subscription Token
```

They are stored in:

```text
/data/identity.json
```

You should not manually configure them.

---

## 🛠️ Local Development

Clone the repository:

```bash
git clone https://github.com/MHDLabs/FreeNET.git
cd FreeNET
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local data directory:

```bash
mkdir -p data
```

Run FreeNET:

```bash
FREENET_DATA_DIR=./data PORT=8000 python main.py
```

The generated identity will be available at:

```bash
cat data/identity.json
```

Local subscription:

```text
http://localhost:8000/sub/<subscription_token>
```

For actual client usage, use a public HTTPS domain.

---

## 🐳 Docker

Build:

```bash
docker build -t freenet .
```

Create persistent storage:

```bash
docker volume create freenet-data
```

Run:

```bash
docker run --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  -v freenet-data:/data \
  freenet
```

The identity file will be stored inside:

```text
/data/identity.json
```

---

## 🗂️ Project Structure

```text
FreeNET/
├── main.py
├── core.py
├── protocols/
│   ├── vless.py
│   ├── xhttp.py
│   └── trojan.py
├── Dockerfile
├── railway.json
├── requirements.txt
├── .dockerignore
├── .gitignore
├── README.md
└── README-fa.md
```

| File                  | Purpose                                        |
| --------------------- | ---------------------------------------------- |
| `main.py`             | FastAPI application, identity and subscription |
| `core.py`             | TCP relay and global statistics                |
| `protocols/vless.py`  | VLESS over WebSocket                           |
| `protocols/xhttp.py`  | XHTTP transport                                |
| `protocols/trojan.py` | Trojan over WebSocket                          |
| `Dockerfile`          | Container image                                |
| `railway.json`        | Railway deployment configuration               |
| `requirements.txt`    | Python runtime dependencies                    |

---

## 🔐 Security / Notes

Your identity file is private:

```text
/data/identity.json
```

It contains:

```text
uuid
trojan_password
subscription_token
```

Anyone with your subscription token can access the subscription and obtain your proxy configurations.

Keep these values private.

Do not:

* commit `/data`
* publish `identity.json`
* share your subscription token publicly
* share your Trojan password publicly

### Losing the identity

If:

```text
/data/identity.json
```

is deleted, FreeNET generates a new identity.

That means existing proxy links will stop working.

If the identity file is corrupted, FreeNET refuses to silently regenerate it.

Keep a backup if preserving existing links matters to you.

---

## ❓ Troubleshooting

### `Data directory is not available`

Make sure a writable directory or Railway Volume exists at:

```text
/data
```

For local usage, you can set:

```text
FREENET_DATA_DIR
```

to another writable directory.

### Subscription returns `404`

Make sure you are using the exact:

```text
subscription_token
```

from:

```text
/data/identity.json
```

The subscription URL uses the token, not the UUID:

```text
/sub/<subscription_token>
```

### Subscription uses the wrong host

FreeNET builds subscription links from the incoming request host.

Use your public Railway domain when opening the subscription.

### Client cannot connect

Check:

* Railway domain is public
* TLS is enabled
* the UUID is correct
* the Trojan password is correct
* the configured path is correct
* the client supports the selected transport
* XHTTP is using the supported mode

### Statistics reset

Make sure the Railway Volume is still mounted at:

```text
/data
```

Statistics are stored in:

```text
/data/stats.json
```

---

## 📣 MHDLabs

More projects and updates:

**Telegram:** https://t.me/MHDLabs

---

## 📄 License

FreeNET is released under the **MIT License**.

---

Made with ❤️ in **MHDLabs**
