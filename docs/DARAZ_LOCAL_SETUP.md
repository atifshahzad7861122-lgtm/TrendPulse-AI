# TrendPulse AI — Daraz Official Open Platform Local HTTPS Setup

This guide walks you through connecting your local TrendPulse AI FastAPI backend to the **Official Daraz Open Platform** using a secure **Cloudflare Quick Tunnel** for HTTPS callbacks.

---

## ⚡ Overview & Architecture

Daraz Open Platform requires a public **HTTPS** callback URL to deliver OAuth 2.0 authorization codes when an approved seller authorizes the TrendPulse AI application.

Because TrendPulse AI runs locally in development (`http://127.0.0.1:8000`), we use **Cloudflare Quick Tunnel** (`cloudflared`) to expose the local API via a temporary, free HTTPS endpoint without deploying permanently, purchasing domains, or configuring port forwarding.

```
┌─────────────────────────┐         ┌───────────────────────────────┐         ┌─────────────────────────┐
│   Daraz Open Platform   │ ──────> │   Cloudflare Quick Tunnel     │ ──────> │  TrendPulse AI Backend  │
│  (OAuth Authorization)  │  HTTPS  │  (xxxx.trycloudflare.com)     │  HTTP   │   (127.0.0.1:8000)      │
└─────────────────────────┘         └───────────────────────────────┘         └─────────────────────────┘
```

---

## 🛠️ Step-by-Step Setup Guide

### Step 1: Start the FastAPI Backend (Terminal 1)

Open **Terminal 1** and start the backend service:

```cmd
scripts\start_backend_daraz.cmd
```

Or start manually with uvicorn:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### Step 2: Verify Backend Swagger UI

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

Confirm that the `/api/v1/platforms/daraz/callback` and `/api/v1/platforms/daraz/status` endpoints are listed and active.

---

### Step 3: Install Cloudflare Tunnel (`cloudflared`) on Windows

If you don't already have `cloudflared` installed:

**Option A — Via Windows Package Manager (winget):**
```powershell
winget install --id Cloudflare.cloudflared
```

**Option B — Direct Download:**
1. Download `cloudflared-windows-amd64.exe` from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases).
2. Rename to `cloudflared.exe` and add it to your system `PATH`.

---

### Step 4: Verify `cloudflared` Installation

In your terminal, test:

```powershell
cloudflared --version
```

*Expected output: `cloudflared version 202x.x.x (built ...)`*

---

### Step 5: Launch Cloudflare Quick Tunnel (Terminal 2)

Open a **separate Terminal 2** (leave Terminal 1 running the backend):

```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare will generate an ephemeral HTTPS URL in the console output, for example:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://sweet-mango-delight.trycloudflare.com                                             |
+--------------------------------------------------------------------------------------------+
```

> [!IMPORTANT]
> **Ephemeral URL Notice:** Quick Tunnel URLs are temporary. If you stop or restart `cloudflared`, Cloudflare will assign a new subdomain. You must update your `DARAZ_CALLBACK_URL` and Daraz App Console accordingly whenever the tunnel restarts.

---

### Step 6: Configure Environment Variables

Open `backend/.env` and update the Daraz configuration:

```env
# Daraz Official Open Platform Configuration
DARAZ_APP_KEY=your_daraz_app_key_here
DARAZ_APP_SECRET=your_daraz_app_secret_here
DARAZ_CALLBACK_URL=https://your-generated-subdomain.trycloudflare.com/api/v1/platforms/daraz/callback
DARAZ_API_BASE_URL=https://api.daraz.pk/rest
```

> [!CAUTION]
> **Security Rules:**
> - Never commit `backend/.env` to Git.
> - Never hardcode `DARAZ_APP_SECRET` or tokens in frontend code or templates.
> - The frontend never receives `DARAZ_APP_KEY`, `DARAZ_APP_SECRET`, or `DARAZ_ACCESS_TOKEN`.

---

### Step 7: Restart the Backend (Terminal 1)

After modifying `backend/.env`, restart the backend server so the new configuration takes effect.

---

### Step 8: Configure Daraz Open Platform App Console

1. Log in to the [Daraz Open Platform Developer Console](https://open.daraz.com/).
2. Navigate to **App Management** → Select your approved App.
3. In **App Settings** → **Callback URL / Redirect URI**, enter:
   ```
   https://your-generated-subdomain.trycloudflare.com/api/v1/platforms/daraz/callback
   ```
4. Save the configuration.

---

### Step 9: Authorize Seller Account & Test Callback

1. Initiate the OAuth authorization URL:
   ```
   https://api.daraz.pk/oauth/authorize?response_type=code&force_auth=true&redirect_uri=https://your-generated-subdomain.trycloudflare.com/api/v1/platforms/daraz/callback&client_id=YOUR_DARAZ_APP_KEY
   ```
2. Log in with your authorized Daraz seller credentials and click **Authorize**.
3. Daraz will redirect to your tunnel endpoint with the authorization code:
   ```
   https://your-generated-subdomain.trycloudflare.com/api/v1/platforms/daraz/callback?code=0_xxxxxx&state=xyz
   ```
4. TrendPulse AI automatically:
   - Validates the `code` parameter.
   - Performs HMAC-SHA256 signed token exchange server-side (`/auth/token/create`).
   - Securely stores the `access_token` and `refresh_token` in the backend repository.
   - Returns a sanitized JSON success response.

---

## 🔄 Two-Terminal Development Workflow

| Terminal | Purpose | Command |
| :--- | :--- | :--- |
| **Terminal 1** | FastAPI Application Server | `scripts\start_backend_daraz.cmd` |
| **Terminal 2** | Cloudflare HTTPS Tunnel | `cloudflared tunnel --url http://localhost:8000` |

---

## 🛡️ Multi-Provider Ingestion & Failover Architecture

TrendPulse AI utilizes an automated 4-tier failover mechanism for Daraz catalog ingestion:

1. **Priority 1 (P1)**: **Official Daraz Open Platform API** (`daraz_official_open_platform`) — Direct signed REST API using developer credentials.
2. **Priority 2 (P2)**: **Parse Daraz Scraper API** (`parse_daraz_api`) — High-speed scraper connector.
3. **Priority 3 (P3)**: **Direct Fallback Provider** (`daraz_direct_fallback`) — Secondary network fallback.
4. **Priority 4 (P4)**: **Database Cache** (`database_cache`) — Persistent offline catalog cache from PostgreSQL / in-memory repository.

Whenever a provider encounters a rate limit (HTTP 429), timeout, or upstream error, the system automatically falls over to the next tier and initiates an exponential backoff cooldown before safely restoring the primary provider.
