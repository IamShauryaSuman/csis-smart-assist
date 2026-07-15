<div align="center">
  <h1>🎓 CSIS SmartAssist</h1>
  <p><strong>A production-grade, full-stack, AI-powered departmental platform for BITS Pilani, K K Birla Goa Campus.</strong></p>

  <p><em>🏆 1st Place at Hackenza 3.0 Hackathon • Officially adopted by the CSIS Department • Showcased at the Imaginarium Inauguration</em></p>
  <p>Built by <strong>Shaurya Suman</strong> (<a href="https://github.com/IamShauryaSuman">@IamShauryaSuman</a>) • <strong>Arnav Gupta</strong> (<a href="https://github.com/ArnavGupta-codes">@ArnavGupta-codes</a>) • <strong>Satvik Srinivas</strong> (<a href="https://github.com/filo8856">@filo8856</a>) • <strong>Abhinav Reddy</strong> (<a href="https://github.com/abhinavrdy4">@abhinavrdy4</a>)</p>

  <p>
    <img src="https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" />
    <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
    <img src="https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google%20gemini&logoColor=white" alt="Google Gemini" />
  </p>
</div>

---

## 📖 Overview

**CSIS SmartAssist** serves a dual purpose for the Computer Science & Information Systems (CSIS) Department:
1. **Institutional Knowledge Graph:** Provides students and faculty with immediate, context-aware access to syllabi, policies, and prerequisites through an advanced Retrieval-Augmented Generation (RAG) system.
2. **Automated Laboratory Reservations:** Automates classroom and lab reservations via a structured, admin-approved calendar allocation workflow utilizing Google Workspace APIs and optimistic concurrency locking.

The platform relies on a heavily decoupled client-server architecture designed to be fast, utilitarian, and fully compatible with 100% free-tier cloud hosting capabilities (Vercel + Render + Supabase).

---

## 🏗 Architecture

- **Frontend (`ui/`)**: A Next.js App Router application utilizing React Server Components, styled with atomic SCSS Modules for maximum speed and presentation control.
- **Backend (`api/`)**: A robust FastAPI service responsible for executing Intent Routing (determining whether a query requires RAG, Calendar booking, or general LLM generation) and orchestrating third-party services.
- **Database**: Supabase providing native Google OAuth, relational tables, `pgvector` for embedding storage, and Realtime WebSockets for live UI updates.

For a deep dive into the engineering principles, vector management, and component architecture, please read the [Engineering Specification (`docs/SPEC.md`)](./docs/SPEC.md).

---

## 🚀 Quick Start & Development

To run this project locally, you will need Node.js (for the frontend), Python 3.10+ (for the backend), and Docker (to spin up the local database).

### 1. Database Setup
```bash
docker compose up -d
```
This spins up a complete, local Supabase environment (Postgres + Auth + Storage).

### 2. Backend (FastAPI)
```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Frontend (Next.js)
```bash
cd ui
npm install
npm run dev
```

For comprehensive, step-by-step setup instructions, including how to configure Google Workspace Service Accounts and obtain Gemini API keys, please refer to the **[Setup Guide (`docs/SETUP.md`)](./docs/SETUP.md)**.

---

## 🧪 Testing

The repository maintains strict open-source engineering standards, backed by comprehensive automated test suites achieving >80% coverage.

**Frontend (Vitest & React Testing Library):**
```bash
cd ui
npm test
```

**Backend (Pytest):**
```bash
cd api
.venv/bin/pytest tests/ -v
```

---

## 🤝 Contributing

We welcome contributions from students, alumni, and open-source developers! 

Before opening a pull request, please read our **[Contributing Guidelines (`CONTRIBUTING.md`)](./CONTRIBUTING.md)** to understand our PR standards, linting requirements (Ruff, ESLint), and architectural philosophy.

---

<div align="center">
  <sub>Built with ❤️ for the CSIS Department @ BITS Pilani Goa.</sub>
</div>
