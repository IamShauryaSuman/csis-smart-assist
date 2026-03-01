# CSIS SmartAssist - Backend

A RAG-powered chatbot for the CSIS Department at BITS Pilani Goa Campus.

## Quick Setup (For New Team Members)

### 1. Clone the repo
```bash
git clone https://github.com/IamShauryaSuman/csis-smart-assist.git
cd csis-smart-assist/backend
```

### 2. Create the virtual environment & install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Create your `.env` file
Copy the example and fill in your Gemini API key:
```bash
cp .env.example .env
```
Then edit `.env` and set:
```
GEMINI_API_KEY="your-actual-gemini-api-key"
```
You can get a free key from https://aistudio.google.com/apikey

### 4. Build the Vector Database from documents
The `data/` folder contains the source documents (PDFs, HTML, DOCX, TXT).
Run this to embed them into ChromaDB:
```bash
source .venv/bin/activate
python ingest_local.py --dir ./data
```
> ⚠️ **This step is REQUIRED.** The chatbot cannot answer questions until you run this.
> The first run will also download the embedding model (~400MB), which may take a few minutes.

### 5. Start the server
```bash
source .venv/bin/activate
uvicorn Chatbot.main:app --host 127.0.0.1 --port 8000
```
The API will be live at `http://127.0.0.1:8000`
Swagger docs at `http://127.0.0.1:8000/docs`

### 6. Test it
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is CSIS?", "user_id": "test"}'
```

## Adding New Documents
Just drop any `.pdf`, `.docx`, `.html`, or `.txt` files into the `backend/data/` folder, then re-run:
```bash
python ingest_local.py --dir ./data
```

## Important Notes
- **Always run commands from inside the `backend/` directory** (not the project root)
- The `RAG_db/` folder is auto-generated and gitignored — each person rebuilds it locally
- The `.env` file is gitignored — each person creates their own with their API key
- The `data/` folder IS tracked in git so everyone has the same source documents
