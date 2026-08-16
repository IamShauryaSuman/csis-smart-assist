#!/bin/bash
set -e

echo "==========================================="
echo "   CSIS SmartAssist Local Deploy Script    "
echo "==========================================="
echo ""

# 0. Ensure we are running from the persistent storage
PERSISTENT_DIR="/mnt/syncstore/smartassist"
if [[ "$PWD" != "$PERSISTENT_DIR"* ]]; then
    echo "⚠️ WARNING: You are running this from $PWD which may not be persistent!"
    echo "   Moving the application to $PERSISTENT_DIR/app..."
    mkdir -p $PERSISTENT_DIR/app
    cp -r . $PERSISTENT_DIR/app/
    echo "✅ Application moved. Please cd into $PERSISTENT_DIR/app and run ./deploy.sh again."
    exit 1
fi

# 1. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker is not installed."
    echo "   Please install Docker Engine first."
    exit 1
fi
echo "✅ Docker is installed."

# 3. Check for NVIDIA Driver & Container Toolkit
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️ WARNING: nvidia-smi not found. Are the NVIDIA drivers installed?"
else
    echo "✅ NVIDIA drivers detected."
fi

if ! docker info | grep -q "Runtimes.*nvidia"; then
    echo "❌ ERROR: NVIDIA Container Toolkit is not installed."
    echo "   Docker cannot access the GPU without it."
    echo "   Install it from: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html"
    exit 1
fi
echo "✅ NVIDIA Container Toolkit verified."

# 4. Create local .env file if it doesn't exist
if [ ! -f .env.local ]; then
    echo "Creating default .env.local configuration for local deployment..."
    cat <<EOF > .env.local
# Local AI Provider Overrides
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama

OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_MODEL=llama3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Postgres Database Setup
POSTGRES_USER=postgres
POSTGRES_PASSWORD=smartassist_local_pass
POSTGRES_DB=smartassist

# Add your Supabase / Next.js / FastAPI environment variables below as needed.
EOF
    echo "✅ .env.local created. (Please edit it later if you need to add Google API keys)."
else
    echo "✅ .env.local already exists."
fi

# 5. Create the required persistent directories
echo "Creating persistent storage directories at /mnt/syncstore/smartassist/data..."
mkdir -p /mnt/syncstore/smartassist/data/postgres
mkdir -p /mnt/syncstore/smartassist/data/ollama
# Grant docker permissions if needed (simplification)
chmod -R 777 /mnt/syncstore/smartassist/data

# 6. Bring up the stack
echo "Starting Docker Compose stack..."
docker compose -f docker-compose.local.yml up -d

# 7. Pull the AI Models
echo "Pulling Ollama models... (This may take several minutes depending on network speed)"
# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
sleep 10

echo "Pulling Llama 3 8B..."
docker exec smartassist-ollama ollama pull llama3:8b

echo "Pulling Nomic Embed Text..."
docker exec smartassist-ollama ollama pull nomic-embed-text

echo "==========================================="
echo "✅ Deployment Successful!"
echo "   - Frontend is running on http://localhost:3000"
echo "   - Backend is running on http://localhost:8000"
echo "   - Ollama is running on port 11434 using the 12GB GPU slice."
echo "==========================================="
