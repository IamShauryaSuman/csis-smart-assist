#!/bin/bash

# Smoke test script for Google APIs and Gemini-backed RAG
echo "🧪 Testing CSIS Smart Assist Google APIs and RAG"
echo "==============================================="

echo "1. Testing backend imports, Google client initialization, Gemini embeddings, and RAG ingestion..."
cd backend
python -c "
from pathlib import Path
from tempfile import TemporaryDirectory

from app.chat_service import ChatService
from app.config import Settings
from app.google_client import get_google_calendar_client, get_google_drive_client, get_google_gmail_client
from app.rag_local_ingest import _get_embeddings, sync_local_rag_to_chromadb

settings = Settings()
print('✅ Backend imports successful')

calendar_service, calendar_id = get_google_calendar_client(settings)
print(f'✅ Google Calendar client ready: {calendar_id}')
print(f'   calendarList count: {len(calendar_service.calendarList().list(maxResults=1).execute().get("items", []))}')

drive_service = get_google_drive_client(settings)
print('✅ Google Drive client ready')
print(f'   file count sample: {len(drive_service.files().list(pageSize=1, fields="files(id)").execute().get("files", []))}')

gmail_service = get_google_gmail_client(settings)
print('✅ Gmail client ready')
print(f'   label count sample: {len(gmail_service.users().labels().list(userId="me").execute().get("labels", []))}')

embeddings = _get_embeddings(['CSIS smoke test'], gemini_key=settings.gemini_api_key)
print(f'✅ Gemini embeddings generated: {len(embeddings)} x {len(embeddings[0]) if embeddings else 0}')

with TemporaryDirectory() as temp_dir:
    data_dir = Path(temp_dir) / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'sample.md').write_text('# CSIS\nThis is a Gemini RAG smoke test.\n', encoding='utf-8')
    summary = sync_local_rag_to_chromadb(
        data_dir=str(data_dir),
        db_path=str(Path(temp_dir) / 'rag_db'),
        gemini_key=settings.gemini_api_key,
    )
    print(f'✅ RAG ingestion summary: {summary}')

print('🎉 Gemini and Google API smoke test complete!')
"