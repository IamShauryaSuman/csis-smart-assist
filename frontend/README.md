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

Use the same Google OAuth client (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`) in backend and frontend so one Google Cloud app manages sign-in and backend Google APIs.

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

## Deploy frontend to Vercel

1. Import this repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Keep framework preset as **Next.js**.
4. Configure production environment variables in Vercel:
   - `NEXT_PUBLIC_BACKEND_URL` = your Render backend URL (for example: `https://your-backend.onrender.com`)
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `NEXTAUTH_SECRET`
   - `NEXTAUTH_URL` = your Vercel app URL (for example: `https://your-app.vercel.app`)
5. Deploy.

After deployment, set backend `FRONTEND_ORIGIN` on Render to your Vercel app URL.
