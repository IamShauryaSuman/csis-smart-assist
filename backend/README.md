## Backend setup (Supabase)

### 1) Environment

Create `.env` in `backend/` from `.env.example`:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (preferred server key)
- `SUPABASE_SERVICE_ROLE_KEY` (legacy fallback)
- `VECTOR_DIMENSIONS` (default `1536`)
- `FRONTEND_ORIGIN` (for CORS, default `http://localhost:3000`)
- `ADMIN_SEED_EMAILS` (comma-separated emails auto-assigned `admin`; all synced users get `user` role)
- `GEMINI_API_KEY` (required for LLM answer generation)
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_CALENDAR_TOKEN_PATH` (default `calender/token.json`)

### 2) Database bootstrap

Run `supabase/schema.sql` in your Supabase SQL editor.

Note: frontend does not need any Supabase key in this architecture because all DB access flows through the backend.

If you previously created `app_users` with a foreign key to `auth.users`, remove that constraint for NextAuth-based login flows.

This creates:

- `app_users`
- `roles`
- `user_roles`
- `booking_requests`
- `rag_documents`
- `rag_chunks` (pgvector)
- `match_rag_chunks` function

### 3) Run API

```bash
uvicorn main:app --reload
```

### 4) API summary

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
