## CSIS SmartAssist Frontend

Next.js frontend for authentication, chat, calendar slot suggestions, and booking request workflows.

### 1) Install

```bash
npm install
```

### 2) Environment

Create `.env.local` in `frontend/` with:

- `NEXT_PUBLIC_BACKEND_URL` (default `http://localhost:8000`)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL` (for local: `http://localhost:3000`)

### 3) Run

```bash
npm run dev
```

Open `http://localhost:3000`.

### 4) Quality checks

```bash
npm run lint
npm run build
```
