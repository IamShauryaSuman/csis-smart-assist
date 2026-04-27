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
- `GEMINI_API_KEY` (required for LLM generation)
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON` or `GOOGLE_CALENDAR_SERVICE_ACCOUNT_PATH` (preferred for booking event writes and Drive reads)
- `GOOGLE_CALENDAR_SUBJECT` (optional domain-wide delegation user)
- `GOOGLE_DRIVE_FOLDER_ID` (optional default source for Drive ingestion)
- `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_TOKEN_URI` (OAuth for Gmail API notifications)
- `GOOGLE_TOKEN_PATH` (fallback token JSON path)
- `GOOGLE_SENDER_EMAIL` (sender address for Gmail API notifications)
- `RAG_LOCAL_DATA_DIR` (default `data`)
- `RAG_AUTO_INGEST_LOCAL_DATA` (default `true`)
- `RAG_AUTO_INGEST_DRIVE_DATA` (default `false`)

For calendar bookings, service account credentials are preferred so approvals can inject events directly into your shared calendar.
Make sure the target calendar is shared with the service account email with permission to edit events.
Drive ingestion also prefers the same service account credentials (grant Drive folder/file access to that service account).
OAuth refresh-token credentials are used for Gmail notifications.

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

### 7) Google Drive RAG ingest

- Supported Drive types: Google Docs, Google Sheets, Google Slides, PDF, DOCX, HTML, TXT, MD.
- Manual ingest endpoint:

```bash
curl -X POST http://localhost:8000/rag/ingest-drive \
   -H "Content-Type: application/json" \
   -d '{"folder_id":"your-folder-id","recursive":true,"max_files":500}'
```

- If `GOOGLE_DRIVE_FOLDER_ID` is set, `folder_id` can be omitted in the request body.
- You can enable startup auto-sync using `RAG_AUTO_INGEST_DRIVE_DATA=true`.

### 8) Run API

```bash
source .venv/bin/activate
uvicorn Chatbot.main:app --host 127.0.0.1 --port 8000
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
   - `GEMINI_API_KEY` (if chat generation is enabled)
   - `GOOGLE_CALENDAR_ID`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_SENDER_EMAIL`
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
- `POST /rag/ingest-drive`
