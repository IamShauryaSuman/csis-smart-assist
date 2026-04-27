# CSIS Smart Assist - Local LLM Deployment Guide

## Overview
This guide helps you deploy the CSIS Smart Assist application with local LLM support using Ollama to Fly.io.

## Prerequisites
- Fly.io account (free tier available)
- Supabase project (for database)
- Google OAuth credentials (for authentication)
- Google Calendar API credentials (for calendar features)

## Quick Deployment

### Option 1: Automated Script (Recommended)
```bash
./deploy.sh
```

### Option 2: Manual Deployment

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**
   ```bash
   fly auth login
   ```

3. **Launch the application**
   ```bash
   fly launch --name csis-smart-assist
   ```
   - Choose your region (e.g., `iad` for US East)
   - Answer "Yes" to create and deploy a Postgres database (optional, you can use Supabase instead)

4. **Set environment variables**
   ```bash
   # Required for LLM
   fly secrets set OLLAMA_BASE_URL="http://localhost:11434"
   fly secrets set OLLAMA_MODEL="gemma2:2b"
   fly secrets set EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

   # Required for app
   fly secrets set SUPABASE_URL="your-supabase-url"
   fly secrets set SUPABASE_SECRET_KEY="your-supabase-secret"
   fly secrets set FRONTEND_ORIGINS="https://your-frontend-domain.fly.dev,http://localhost:3000"

   # Optional but recommended
   fly secrets set GOOGLE_CALENDAR_ID="your-calendar-id@group.calendar.google.com"
   fly secrets set GOOGLE_CALENDAR_REFRESH_TOKEN="your-refresh-token"
   fly secrets set ADMIN_SEED_EMAILS="admin@csis.edu"
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OLLAMA_BASE_URL` | Yes | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Yes | Model to use (default: `gemma2:2b`) |
| `EMBEDDING_MODEL` | Yes | Embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`) |
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SECRET_KEY` | Yes | Supabase server key |
| `FRONTEND_ORIGINS` | Yes | Allowed frontend URLs (comma-separated) |
| `GOOGLE_CALENDAR_ID` | Optional | Google Calendar ID for booking features |
| `ADMIN_SEED_EMAILS` | Optional | Admin email addresses |

### Model Options

You can use different models based on your needs:

- **Small/Fast**: `gemma2:2b`, `llama3.2:1b`, `phi3:3.8b`
- **Balanced**: `gemma2:9b`, `llama3.2:3b`
- **Large**: `llama3.1:8b`, `mistral:7b`

To change models after deployment:
```bash
fly secrets set OLLAMA_MODEL="new-model-name"
fly deploy
```

## Scaling

### Free Tier Limits
- 256MB-1GB RAM per VM
- Shared CPU
- 100GB data transfer/month

### Upgrading for Better Performance
```bash
# Upgrade to performance CPU with more RAM
fly scale vm performance-1x

# Or scale memory
fly scale memory 2048
```

## Troubleshooting

### Common Issues

1. **Ollama model download fails**
   - Check Fly.io logs: `fly logs`
   - Ensure model name is correct
   - Try a smaller model

2. **Out of memory errors**
   - Use a smaller model like `gemma2:2b`
   - Upgrade to paid plan for more RAM

3. **Slow responses**
   - CPU inference is slower than GPU
   - Consider upgrading to performance VMs

### Checking Logs
```bash
fly logs
```

### Restarting the app
```bash
fly restart
```

## Local Development

For local testing before deployment:

1. **Install Ollama locally**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull a model**
   ```bash
   ollama pull gemma2:2b
   ```

3. **Start Ollama server**
   ```bash
   ollama serve
   ```

4. **Run the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

## Cost Estimation

- **Free tier**: $0 (with limits)
- **Performance 1x**: ~$0.02/hour for 2GB RAM
- **Data transfer**: $0.02/GB after free allowance

## Next Steps

1. Deploy your frontend to Fly.io or Vercel
2. Set up Supabase database
3. Configure Google OAuth and Calendar API
4. Test the chat functionality with local LLM

## Support

If you encounter issues:
1. Check Fly.io documentation: https://fly.io/docs/
2. Review Ollama documentation: https://github.com/ollama/ollama
3. Check application logs for errors