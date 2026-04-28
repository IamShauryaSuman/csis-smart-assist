#!/bin/bash

# CSIS Smart Assist - Gemini Deployment Script
# This script helps deploy the application to Fly.io

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

# You may need to set other secrets like SUPABASE_URL and GEMINI_API_KEY.
echo "📝 Remember to set your other environment variables:"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_SECRET_KEY"
echo "   - FRONTEND_ORIGINS"
echo "   - GEMINI_API_KEY"
echo "   - And any other required variables"

# Deploy
echo "🚀 Deploying application..."
fly deploy

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://csis-smart-assist.fly.dev"