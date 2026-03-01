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

Optional RAG extras (embeddings/vector tooling):

```bash
pip install -r requirements-rag.txt
```

### 4) Environment

Create `.env` in `backend/` from `.env.example` and set:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (preferred server key)
- `SUPABASE_SERVICE_ROLE_KEY` (legacy fallback)
- `VECTOR_DIMENSIONS` (default `1536`)
- `FRONTEND_ORIGIN` (default `http://localhost:3000`)
- `ADMIN_SEED_EMAILS` (comma-separated)
- `GEMINI_API_KEY` (required for LLM generation)
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

Legacy/local vector build script:

```bash
python ingest_local.py --dir ./data
```

### 7) Run API

```bash
source .venv/bin/activate
uvicorn Chatbot.main:app --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000`  
Docs: `http://127.0.0.1:8000/docs`

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
