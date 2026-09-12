# 🚀 FreeNET

> یک پروکسی‌سرور کوچک، ساده و سبک مبتنی بر VLESS / XHTTP / Trojan برای Railway
> **Deploy → گرفتن Subscription → استفاده → فراموشش کن**

[🇬🇧 English](README.md)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi\&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker\&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-deploy-0B0D0E?logo=railway\&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 🚀 شروع سریع

FreeNET برای کسانی ساخته شده که فقط یک proxy server می‌خواهند و نمی‌خواهند درگیر یک پنل کامل شوند.

### 1. دیپلوی روی Railway

Repository را روی Railway دیپلوی کنید و یک Volume با مسیر زیر اضافه کنید:

```text
/data
```

این Volume مهم است، چون هویت سرویس و آمار مصرف در آن ذخیره می‌شوند.

### 2. بقیه چیزها خودکار ساخته می‌شوند

در اولین اجرا، FreeNET به‌صورت خودکار این فایل را ایجاد می‌کند:

```text
/data/identity.json
```

این فایل شامل موارد زیر است:

```json
{
  "uuid": "...",
  "trojan_password": "...",
  "subscription_token": "..."
}
```

لازم نیست هیچ‌کدام را دستی بسازید.

### 3. لینک Subscription را بگیرید

فایل:

```text
/data/identity.json
```

را باز کنید و مقدار:

```text
subscription_token
```

را بردارید.

بعد لینک زیر را باز کنید:

```text
https://<YOUR-RAILWAY-DOMAIN>/sub/<subscription_token>
```

و آن را به کلاینت خود به‌عنوان Subscription اضافه کنید.

تمام. ❤️

---

## ☁️ راه‌اندازی روی Railway

FreeNET از ابتدا با هدف اجرا روی Railway طراحی شده است.

### چیزهایی که نیاز دارید

* یک سرویس Railway
* `Dockerfile` موجود پروژه
* یک Volume روی مسیر `/data`
* یک Railway Domain عمومی

Railway پورت سرویس را از طریق:

```text
$PORT
```

در اختیار برنامه قرار می‌دهد.

FreeNET نیز روی:

```text
0.0.0.0
```

گوش می‌دهد.

Healthcheck:

```text
/health
```

### داده‌های پایدار

FreeNET از این فایل‌ها استفاده می‌کند:

```text
/data/identity.json
/data/stats.json
```

هویت سرویس باید باقی بماند، چون UUID، پسورد Trojan و Subscription Token یک‌بار ساخته می‌شوند و بعد دوباره استفاده می‌شوند.

اگر Volume پایدار نداشته باشید، ممکن است بعد از از دست رفتن داده‌ها هویت جدید ساخته شود و لینک‌های قبلی دیگر کار نکنند.

### TLS

TLS توسط Railway مدیریت می‌شود.

کلاینت‌ها از طریق Railway Domain و با HTTPS/WSS وصل می‌شوند.

---

## 🧩 FreeNET چیست؟

FreeNET یک proxy server مینیمال است.

این پروژه **یک VPN Panel کامل نیست**.

برای کسی ساخته شده که فقط می‌خواهد:

```text
Deploy
  ↓
گرفتن Subscription
  ↓
استفاده
```

بدون اینکه درگیر این موارد شود:

* مدیریت کاربر
* دیتابیس
* quota
* تاریخ انقضا
* پنل مدیریت
* سیستم billing
* مانیتورینگ per-user

FreeNET عمداً کوچک نگه داشته شده.

---

## ✨ قابلیت‌ها

* 🔐 ساخت خودکار VLESS UUID
* 🔑 ساخت خودکار Trojan Password
* 🎟️ ساخت خودکار Subscription Token
* 🌐 VLESS روی WebSocket
* ⚡ پشتیبانی از XHTTP
* 🐇 Trojan روی WebSocket
* 📡 یک لینک Subscription
* 📊 آمار کلی Upload / Download
* ⏱️ نمایش Uptime
* 💾 ذخیره دائمی اطلاعات در `/data`
* 🐳 آماده برای Docker
* ☁️ آماده برای Railway
* 🚫 بدون پنل
* 🚫 بدون دیتابیس
* 🚫 بدون مدیریت کاربر
* 🚫 بدون مانیتورینگ per-user

---

## 🆚 چرا FreeNET؟

پروژه‌های پنل‌محور قدرتمند زیادی وجود دارند، مثل:

* X4G
* RVG
* StanNG
* SpiderPanel
* Lunel

این پروژه‌ها برای مدیریت تعداد زیادی کاربر، quota، تاریخ انقضا، داشبورد، دیتابیس و امکانات مدیریتی مختلف ساخته شده‌اند.

FreeNET هدف متفاوتی دارد.

```text
پروژه‌های پنل‌محور:

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

اما:

```text
FreeNET:

Deploy
 ↓
Subscription
 ↓
Done
```

FreeNET قرار نیست جایگزین پنل‌های کامل باشد.

برای کسی است که می‌گوید:

> **«من پنل نمی‌خواهم؛ فقط یک proxy server سالم می‌خواهم.»**

---

## 🌐 پروتکل‌های پشتیبانی‌شده

FreeNET در حال حاضر این موارد را ارائه می‌دهد:

```text
VLESS
XHTTP
Trojan
```

تمام ترافیک proxy در نهایت روی TCP relay می‌شود.

### VLESS

VLESS روی WebSocket ارائه می‌شود.

Endpoint:

```text
/vless/{uuid}
```

Subscription از:

```text
type=ws
security=tls
```

استفاده می‌کند.

TLS توسط Railway انجام می‌شود.

---

### XHTTP

XHTTP از طریق درخواست‌های HTTP ارائه می‌شود.

Endpointها:

```text
/xhttp/{uuid}
/xhttp/{uuid}/{path}
```

متدهای پشتیبانی‌شده:

```text
GET
POST
```

Modeهای موجود:

```text
packet-up
stream-up
```

در حال حاضر Subscription، کانفیگ `packet-up` را ارائه می‌کند.

XHTTP به TCP Port عمومی جداگانه نیاز ندارد.

---

### Trojan

Trojan روی WebSocket ارائه می‌شود.

Endpoint:

```text
/trojan/{uuid}
```

پسورد Trojan به‌صورت خودکار ساخته می‌شود و در این فایل ذخیره می‌شود:

```text
/data/identity.json
```

برای Trojan نیز TCP Port جداگانه لازم نیست.

---

## 📡 Subscription

Endpoint مربوط به Subscription:

```text
/sub/{token}
```

Subscription Token از VLESS UUID جداست.

نمونه:

```text
https://example.up.railway.app/sub/AbCdEfGhIjKlMnOpQrStUvWx
```

پاسخ Subscription به‌صورت Base64-encoded برگردانده می‌شود و شامل کانفیگ‌های فعال FreeNET است:

```text
VLESS WebSocket
Trojan WebSocket
XHTTP packet-up
```

---

### 📊 وضعیت سرویس

Subscription یک node نمایشی کوچک هم دارد، مثلاً:

```text
📊 FreeNET • 18d • ↑42.6GB ↓183.2GB
```

که وضعیت همین instance را نشان می‌دهد:

* Uptime
* Total Upload
* Total Download

این یک node واقعی برای اتصال نیست و فقط برای نمایش وضعیت در لیست کلاینت استفاده می‌شود.

---

### اطلاعات Subscription

FreeNET همچنین metadataهایی مانند:

```text
Subscription-Userinfo
Profile-Title
```

را برمی‌گرداند.

کلاینت‌هایی مثل v2rayN می‌توانند مستقیماً از لینک Subscription استفاده کنند.

---

## 📊 آمار کلی

FreeNET فقط آمار کلی instance را ثبت می‌کند.

هیچ مانیتورینگ per-user وجود ندارد.

موارد ثبت‌شده:

```text
Total Upload
Total Download
Uptime
```

آمار در این فایل ذخیره می‌شود:

```text
/data/stats.json
```

رفتار آن:

* Upload و Download در صورت وجود Volume باقی می‌مانند.
* Uptime مربوط به process فعلی است.
* Uptime بعد از restart از نو شروع می‌شود.
* آمار کلی هستند، نه مربوط به هر کاربر.

---

## ⚙️ تنظیمات

FreeNET عمداً تنظیمات زیادی ندارد.

| متغیر              |       الزامی | مقدار پیش‌فرض        | کاربرد                    |
| ------------------ | -----------: | -------------------- | ------------------------- |
| `PORT`             | توسط Railway | `8000` در حالت local | پورت اجرای HTTP           |
| `FREENET_DATA_DIR` |          خیر | `/data`              | محل ذخیره identity و آمار |

### مقادیر خودکار

این موارد توسط خود برنامه مدیریت می‌شوند:

```text
VLESS UUID
Trojan Password
Subscription Token
```

و در این مسیر قرار دارند:

```text
/data/identity.json
```

نیازی به تنظیم دستی آن‌ها نیست.

---

## 🗂️ اطلاعات ذخیره‌شده

مسیر:

```text
/data
```

شامل این فایل‌هاست:

```text
/data/identity.json
/data/stats.json
```

`identity.json` هویت اصلی سرویس را نگه می‌دارد و `stats.json` آمار مصرف را.

برای حفظ لینک‌های فعلی، Volume باید پایدار بماند.

---

## 🛠️ اجرای محلی

Repository را clone کنید:

```bash
git clone https://github.com/MHDLabs/FreeNET.git
cd FreeNET
```

محیط مجازی بسازید:

```bash
python -m venv .venv
source .venv/bin/activate
```

Dependencyها را نصب کنید:

```bash
pip install -r requirements.txt
```

پوشه داده را بسازید:

```bash
mkdir -p data
```

سرویس را اجرا کنید:

```bash
FREENET_DATA_DIR=./data PORT=8000 python main.py
```

Identity ساخته‌شده را ببینید:

```bash
cat data/identity.json
```

Subscription محلی:

```text
http://localhost:8000/sub/<subscription_token>
```

برای استفاده واقعی از کلاینت، بهتر است پروژه را روی یک سرویس دارای HTTPS عمومی اجرا کنید.

---

## 🐳 Docker

ساخت image:

```bash
docker build -t freenet .
```

ساخت Volume:

```bash
docker volume create freenet-data
```

اجرای container:

```bash
docker run --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  -v freenet-data:/data \
  freenet
```

فایل identity داخل:

```text
/data/identity.json
```

ذخیره می‌شود.

---

## 🗂️ ساختار پروژه

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

| فایل                  | کاربرد                                  |
| --------------------- | --------------------------------------- |
| `main.py`             | FastAPI، مدیریت identity و Subscription |
| `core.py`             | TCP Relay و آمار کلی                    |
| `protocols/vless.py`  | پیاده‌سازی VLESS روی WebSocket          |
| `protocols/xhttp.py`  | پیاده‌سازی XHTTP                        |
| `protocols/trojan.py` | پیاده‌سازی Trojan روی WebSocket         |
| `Dockerfile`          | ساخت Container                          |
| `railway.json`        | تنظیمات Deploy روی Railway              |
| `requirements.txt`    | Dependencyهای runtime                   |

---

## 🔐 نکات امنیتی

فایل هویت خصوصی است:

```text
/data/identity.json
```

و شامل:

```text
uuid
trojan_password
subscription_token
```

است.

هر کسی که Subscription Token شما را داشته باشد، می‌تواند لینک‌های proxy را دریافت کند.

پس:

* `/data` را commit نکنید.
* `identity.json` را عمومی نکنید.
* Subscription Token را منتشر نکنید.
* Trojan Password را منتشر نکنید.
* Volume را پایدار نگه دارید.

### از دست رفتن Identity

اگر:

```text
/data/identity.json
```

حذف شود، FreeNET یک identity جدید می‌سازد.

در نتیجه لینک‌های قدیمی دیگر کار نخواهند کرد.

اگر فایل خراب شده باشد، FreeNET به‌صورت خودکار identity جدید نمی‌سازد و startup را متوقف می‌کند تا هویت قبلی ناخواسته از بین نرود.

---

## ❓ رفع اشکال

### خطای `Data directory is not available`

مطمئن شوید مسیر:

```text
/data
```

وجود دارد و قابل نوشتن است.

برای اجرای local نیز می‌توانید:

```text
FREENET_DATA_DIR
```

را روی یک مسیر قابل‌نوشتن قرار دهید.

---

### Subscription خطای `404` می‌دهد

مقدار دقیق:

```text
subscription_token
```

را از:

```text
/data/identity.json
```

بردارید.

فرمت درست:

```text
/sub/<subscription_token>
```

است، نه UUID.

---

### Host اشتباه داخل Subscription

FreeNET host را از درخواست ورودی تشخیص می‌دهد.

اگر Subscription را از `localhost` باز کنید، ممکن است لینک‌ها نیز `localhost` داشته باشند.

برای استفاده واقعی، Subscription را از Railway Domain عمومی باز کنید.

---

### کلاینت وصل نمی‌شود

این موارد را بررسی کنید:

* Railway Domain عمومی باشد.
* TLS فعال باشد.
* UUID درست باشد.
* Trojan Password درست باشد.
* path درست باشد.
* کلاینت transport مربوطه را پشتیبانی کند.
* برای XHTTP از mode پشتیبانی‌شده مثل `packet-up` استفاده شود.

Pathهای اصلی:

```text
/vless/{uuid}
/trojan/{uuid}
/xhttp/{uuid}
```

---

### آمار reset شده

مطمئن شوید Volume همچنان روی:

```text
/data
```

mount شده باشد.

آمار در:

```text
/data/stats.json
```

ذخیره می‌شود.

---

## 📣 MHDLabs

پروژه‌ها و آپدیت‌های بیشتر:

**Telegram:** https://t.me/MHDLabs

---

## 📄 مجوز

FreeNET تحت مجوز **MIT** منتشر شده است.

---

Made with ❤️ in **MHDLabs**
