# Contributing to CSIS SmartAssist

First off, thank you for considering contributing to CSIS SmartAssist! It's people like you that make this platform an incredible resource for the department.

This document serves as a set of guidelines for contributing to this repository. These are guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

---

## Code of Conduct

By participating in this project, you are expected to uphold a welcoming, inclusive, and professional environment. Treat all contributors, maintainers, and users with respect. Constructive criticism is welcome; personal attacks are not.

---

## How Can I Contribute?

### 🐛 Reporting Bugs
Before creating bug reports, please check the issue tracker to avoid duplicates. When filing a bug, ensure you include:
- A clear, descriptive title.
- Exact steps to reproduce the problem.
- Expected behavior vs. actual behavior.
- Any relevant logs, screenshots, or stack traces.

### ✨ Proposing Enhancements
If you have an idea for a new feature or improvement:
- Open an issue describing your proposal.
- Detail the problem it solves and how the CSIS department will benefit from it.
- Wait for feedback from maintainers before writing significant amounts of code.

### 🛠 Your First Pull Request
We label accessible issues with `good first issue` or `help wanted`. These are great starting points if you're new to the codebase.

---

## Local Development Setup

We highly recommend using our Docker setup for local development. This ensures your database, authentication, and vector extensions match production exactly.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/csis-smartassist.git
   cd csis-smartassist
   ```

2. **Start the Database Infrastructure:**
   ```bash
   docker compose up -d
   ```
   *This spins up the Supabase stack locally on port 54321.*

3. **Set up Environment Variables:**
   Copy `.env.example` to `.env` and fill in the necessary dummy keys for local development (detailed in `docs/SETUP.md`).

4. **Boot the Backend:**
   ```bash
   cd api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

5. **Boot the Frontend:**
   ```bash
   cd ../ui
   npm install
   npm run dev
   ```

---

## Pull Request Standards

To maintain a production-grade codebase, all Pull Requests are subjected to strict CI/CD pipelines. Please ensure your PR meets the following criteria before requesting a review:

### 1. Automated Tests Must Pass
We do not merge code that breaks existing functionality.
* **Frontend:** Run `npm test` inside the `ui/` directory. All 60+ Vitest specifications must pass. If you write a new React Component or Hook, **you must write a test for it.**
* **Backend:** Run `pytest tests/ -v` inside the `api/` directory. All 35+ Python specifications must pass.

### 2. Strict Linting & Code Style
* **Python Backend:** We use **Ruff** and **Flake8** to maintain PEP-8 compliance and enforce clean imports. 
  ```bash
  cd api && ruff check .
  ```
* **TypeScript Frontend:** We use strict TypeScript configurations and ESLint.
  ```bash
  cd ui && npm run lint
  ```

### 3. Commit Message Formatting
Please write clean, descriptive commit messages. We prefer the [Conventional Commits](https://www.conventionalcommits.org/) format:
* `feat:` (new feature for the user)
* `fix:` (bug fix for the user)
* `docs:` (changes to the documentation)
* `style:` (formatting, missing semi colons, etc; no production code change)
* `refactor:` (refactoring production code, eg. renaming a variable)
* `test:` (adding missing tests, refactoring tests)

---

## Adding New Third-Party Integrations
If your PR involves interacting with a new external API or building a new LLM pipeline, you **must** abstract the logic into the `api/services/` directory. Do not write raw external API calls inside endpoint controllers (`api/routes/`).

---

Thank you for contributing to the betterment of the CSIS Department!
