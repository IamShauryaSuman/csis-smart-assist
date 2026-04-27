#!/bin/bash

# CSIS Smart Assist - Local LLM Deployment Script
# This script helps deploy the application with Ollama to Fly.io

echo "🚀 CSIS Smart Assist - Local LLM Deployment"
echo "=========================================="

# Check if Fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

# Login to Fly.io
echo "🔐 Logging into Fly.io..."
fly auth login

# Launch the app
echo "📦 Deploying to Fly.io..."
fly launch --name csis-smart-assist

# Set environment variables
echo "⚙️  Setting environment variables..."
fly secrets set OLLAMA_BASE_URL="http://localhost:11434"
fly secrets set OLLAMA_MODEL="gemma2:2b"
fly secrets set EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

# You may need to set other secrets like SUPABASE_URL, etc.
echo "📝 Remember to set your other environment variables:"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_SECRET_KEY"
echo "   - FRONTEND_ORIGINS"
echo "   - And any other required variables"

# Deploy
echo "🚀 Deploying application..."
fly deploy

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://csis-smart-assist.fly.dev"