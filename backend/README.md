## Backend setup (Supabase)

### 1) Environment

Create `.env` in `backend/` from `.env.example`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `VECTOR_DIMENSIONS` (default `1536`)

### 2) Database bootstrap

Run `supabase/schema.sql` in your Supabase SQL editor.

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

- `POST /users/sync`
- `POST /users/{user_id}/roles`
- `GET /users/{user_id}/roles`
- `POST /booking-requests`
- `GET /booking-requests?status=pending|accepted|declined`
- `PATCH /booking-requests/{request_id}/decision`
- `POST /rag/documents`
- `POST /rag/chunks`
- `POST /rag/chunks/search`
