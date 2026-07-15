# Complete Setup Guide

Welcome to the CSIS SmartAssist setup guide! This document outlines how to configure the local environment, external APIs (Google & Gemini), and the database so you can run the application on your machine.

---

## 1. Local Database Setup (Supabase)

The easiest way to replicate our production database is using Docker. Our repository includes a `docker-compose.yml` file that spins up a local Supabase stack (Postgres + Auth + pgvector).

1. Install [Docker](https://docs.docker.com/get-docker/) on your system.
2. From the root of the repository, run:
   ```bash
   docker compose up -d
   ```
3. Your local Postgres database is now accessible at `localhost:5432` and the Supabase API is running on `localhost:54321`.
4. *Note: You will need to run the initial schema migrations (found in `supabase/migrations`) to create the `profiles`, `chat_sessions`, `messages`, and `rag_chunks` tables.*

---

## 2. Environment Variables

Copy the example environment file to create your local secrets configuration:

```bash
cp .env.example .env
```

### Next.js (Frontend) Environment Variables
* `NEXT_PUBLIC_API_URL`: Set this to `http://localhost:8000` (FastAPI backend).
* `NEXT_PUBLIC_SUPABASE_URL`: Your local or production Supabase URL.
* `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your local or production Supabase Anon Key.
* `NEXT_PUBLIC_GOOGLE_CLIENT_ID`: Your Google OAuth Client ID (used for native OIDC authentication).

### FastAPI (Backend) Environment Variables
* `FRONTEND_URL`: URL of the frontend (e.g., `http://localhost:3000`). Used for CORS.
* `ALLOWED_EMAIL_DOMAIN`: Email domain restriction (e.g., `goa.bits-pilani.ac.in`).
* `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`: For backend admin operations.
* `GEMINI_API_KEY`: See Section 4 below.
* `GROQ_API_KEY` / `OPENROUTER_API_KEY`: Optional fallback keys for the Hybrid LLM.
* `GOOGLE_SERVICE_ACCOUNT_JSON_B64`: See Section 3 below.
* `GOOGLE_DRIVE_FOLDER_ID`: The ID of the Drive folder containing the RAG knowledge base.
* `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` / `GMAIL_SENDER_ADDRESS`: OAuth credentials for sending automated booking emails.

---

## 3. Google Workspace Service Account Setup

CSIS SmartAssist uses a centralized Google Service Account to interface with Google Calendar (for lab bookings), Google Drive (for RAG document fetching), and Gmail (for automated email notifications).

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the following APIs:
   - **Google Calendar API**
   - **Google Drive API**
   - **Gmail API**
4. Navigate to **IAM & Admin > Service Accounts**.
5. Create a new Service Account (e.g., `smartassist-service@your-project.iam.gserviceaccount.com`).
6. Generate a JSON key for this account.
7. To safely store this in your `.env` file without breaking formatting, encode the entire JSON file in Base64:
   ```bash
   # On Mac/Linux
   base64 -i path/to/your/service-account.json | pbcopy
   ```
8. Paste the encoded string into `.env` as `GOOGLE_SERVICE_ACCOUNT_B64`.

**Important:** For the Service Account to act on behalf of the department, a Google Workspace Admin must grant it **Domain-Wide Delegation** in the Google Admin Console, specifically enabling scopes for Calendar and Gmail read/write access.

### 3.1 Google OAuth Client ID (Frontend Authentication)
In addition to the Service Account, you must create a standard **OAuth Client ID** for the frontend login.
1. In the Google Cloud Console, navigate to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Set application type to **Web application**.
4. Add your frontend URL (e.g., `http://localhost:3000`) to the **Authorized JavaScript origins**.
5. Add the callback URL (e.g., `http://localhost:3000/auth-callback`) to the **Authorized redirect URIs**.
6. Copy the Client ID and add it to your `.env` as `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.
7. You must also configure this exact Client ID as a Google Auth Provider inside your Supabase project dashboard.

> **Note on Consent Screen Branding:** If your deployed app shows the raw domain (e.g., `csis-smartassist.vercel.app`) instead of "CSIS SmartAssist" on the Google login screen, it is because your Google Cloud project is set to "External" and is unverified. To fix this, go to the **OAuth consent screen** tab in Google Cloud Console and either set the User Type to **Internal** (recommended for university projects), or verify your production domain.

---

## 4. Google Gemini API Setup

The primary LLM driving intent classification and RAG synthesis is Google Gemini (specifically `gemini-2.5-flash`).

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in and navigate to "Get API key".
3. Generate a new key and add it to your `.env` as `GEMINI_API_KEY`.

---

## 5. Booting the Application

Once your `.env` is fully populated, you can start the application servers.

**Terminal 1 (Backend):**
```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd ui
npm install
npm run dev
```

The frontend will now be available at `http://localhost:3000` and the backend Swagger documentation at `http://localhost:8000/docs`.

---

## 6. Production Deployment

The platform is designed to be hosted entirely on free-tier cloud services.

### Backend (Render)
We recommend deploying the backend to **Render** using their free Docker tier.

1. Go to [dashboard.render.com](https://dashboard.render.com/) -> **New Web Service**.
2. Connect your GitHub repository.
3. Set **Root Directory** to `api` and **Environment** to `Docker`.
4. Under **Advanced**, add your `.env` variables (e.g. `SUPABASE_URL`, `GEMINI_API_KEY`, etc.).
5. Click **Create Web Service**.

Once deployed, Render will provide a live URL (e.g., `https://csis-smartassist-api.onrender.com`). Use this URL as your `NEXT_PUBLIC_API_URL` for the frontend.

### Frontend (Vercel)
The Next.js frontend deploys seamlessly on **Vercel**.

1. Go to [Vercel.com](https://vercel.com/) and click **Add New...** -> **Project**.
2. Import your GitHub repository.
3. In the configuration, click **Edit** next to **Root Directory** and select the `ui` folder.
4. Under **Environment Variables**, add the three required variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` (Set this to your live Render backend URL)
5. Click **Deploy**.

Once your frontend is live, remember to add its URL to your Render backend environment variables as `FRONTEND_URL` to ensure CORS policies allow cross-origin requests.
