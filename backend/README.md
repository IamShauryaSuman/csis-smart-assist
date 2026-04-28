# CSIS SmartAssist - Backend

A RAG-powered chatbot backend for the CSIS Department at BITS Pilani Goa Campus.

## Backend setup (Supabase + FastAPI)

### 1) Clone repository

```bash
git clone https://github.com/IamShauryaSuman/csis-smart-assist.git
cd csis-smart-assist/backend
```

### 2) Python version

- Recommended: **Python 3.11 or 3.12** for full stack setup (including local vector/RAG extras).
- Python 3.13 can run core API paths, but some optional AI/vector dependencies may require additional build tooling.

### 3) Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Environment

Create `.env` in `backend/` from `.env.example` and set:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (preferred server key)
- `SUPABASE_SERVICE_ROLE_KEY` (legacy fallback)
- `VECTOR_DIMENSIONS` (default `1536`)
- `FRONTEND_ORIGIN` (legacy single-origin fallback, default `http://localhost:3000`)
- `FRONTEND_ORIGINS` (preferred, comma-separated allowlist e.g. `http://localhost:3000,https://your-frontend.vercel.app`)
- `ADMIN_SEED_EMAILS` (comma-separated)
- `GEMINI_API_KEY` (required for chat and RAG embeddings)
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_CALENDAR_TOKEN_PATH` (default `calender/token.json`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER_EMAIL`, `SMTP_SENDER_PASSWORD` (for email notifications)
- `RAG_LOCAL_DATA_DIR` (default `data`)
- `RAG_AUTO_INGEST_LOCAL_DATA` (default `true`)

### 5) Database bootstrap

Run `supabase/schema.sql` in Supabase SQL editor.

This creates:

- `app_users`
- `roles`
- `user_roles`
- `booking_requests`
- `rag_documents`
- `rag_chunks` (pgvector)
- `match_rag_chunks` function

### 6) Local RAG data ingest

- Files in `backend/data/` are synced into `rag_documents` and `rag_chunks`.
- Supported local file types: `.pdf`, `.docx`, `.html`, `.htm`, `.txt`, `.md`.
- You can ingest via startup auto-sync (`RAG_AUTO_INGEST_LOCAL_DATA=true`) or manual endpoint:

```bash
curl -X POST http://localhost:8000/rag/ingest-local
```

### 7) Run API

```bash
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`  
Docs: `http://127.0.0.1:8000/docs`

## Deploy backend to Render

This repo includes a root `render.yaml` that deploys `backend/` as a Python web service.

1. Push this repository to GitHub.
2. In Render, create a **Blueprint** from the repository (it will detect `render.yaml`).
3. Set environment variables in Render service settings:
   - `SUPABASE_URL`
   - `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`)
   - `FRONTEND_ORIGINS` (include all frontend URLs that call the API, including Vercel preview/production and local dev)
   - `FRONTEND_ORIGIN` (optional legacy fallback)
   - `GEMINI_API_KEY`
   - `GOOGLE_CALENDAR_ID` and `GOOGLE_CALENDAR_TOKEN_PATH` (if calendar endpoints are used)
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER_EMAIL`, `SMTP_SENDER_PASSWORD` (if notifications are enabled)
4. Optional recommended values in Render:
   - `RAG_AUTO_INGEST_LOCAL_DATA=false`
   - `VECTOR_DIMENSIONS=1536`

The backend start command is:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## API summary

- `POST /chat`
- `POST /calendar/availability`
- `POST /calendar/nearby-slots`
- `POST /users/sync`
- `POST /users/sync-session`
- `POST /users/{user_id}/roles`
- `GET /users/{user_id}/roles`
- `GET /users/roles/by-email?email=...`
- `POST /booking-requests`
- `GET /booking-requests?status=pending|accepted|declined`
- `PATCH /booking-requests/{request_id}/decision`
- `POST /rag/documents`
- `POST /rag/chunks`
- `POST /rag/chunks/search`
- `POST /rag/ingest-local`
