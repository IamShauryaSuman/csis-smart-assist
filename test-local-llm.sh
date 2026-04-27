#!/bin/bash

# Test script for local LLM setup
echo "🧪 Testing CSIS Smart Assist Local LLM Setup"
echo "==========================================="

# Check if Ollama is running
echo "1. Checking Ollama service..."
if pgrep -f "ollama serve" > /dev/null; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running. Starting..."
    brew services start ollama
    sleep 5
fi

# Check available models
echo "2. Checking available models..."
ollama list

# Test model response
echo "3. Testing model response..."
echo "Testing with llama3.2:1b..."
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "prompt": "Hello, can you help me with information about CSIS?",
    "stream": false
  }' | jq -r '.response'

echo "4. Testing backend..."
cd backend
python -c "
import os
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'
os.environ['OLLAMA_MODEL'] = 'llama3.2:1b'
os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-MiniLM-L6-v2'

from app.chat_service import ChatService
from app.config import Settings

settings = Settings()
print('✅ Backend imports successful')
print(f'🔧 Using model: {settings.ollama_model}')
print(f'🔧 Embedding model: {settings.embedding_model}')
"

echo "🎉 Local LLM setup test complete!"