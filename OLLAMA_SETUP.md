# Using Local LLMs with Ollama

This guide explains how to use the Financial Statement Analyzer with **local LLMs** (Mistral, Llama 3.1, etc.) instead of cloud APIs.

## What is Ollama?

Ollama is a tool that lets you run large language models locally on your computer. No API keys needed, no cloud costs, and your data stays private!

## Installation

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

### 2. Verify Installation

```bash
ollama --version
```

### 3. Pull Your Model

You mentioned you have **Mistral (4.4GB)** and **Llama 3.1 (4.7GB)**. Let's pull them:

**For Mistral:**
```bash
ollama pull mistral
```

**For Llama 3.1:**
```bash
ollama pull llama3.1
```

This will download the models if you don't have them already.

### 4. Test the Model

```bash
ollama run mistral "Hello, how are you?"
```

You should see the model respond!

## Configure the Application

### 1. Create `.env` File

```bash
cd backend
cp .env.example .env
```

### 2. Edit `.env` File

Open `backend/.env` and configure for Ollama:

```env
# AI Provider - use ollama for local LLMs
AI_PROVIDER=ollama

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Leave these empty (not needed for Ollama)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Server Configuration
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:3000

# File Upload
MAX_FILE_SIZE=50000000
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
```

### 3. Start Ollama Server

Ollama needs to be running in the background:

```bash
ollama serve
```

You should see: `Listening on 127.0.0.1:11434`

**Keep this terminal open!**

## Switch Between Models

To use **Llama 3.1** instead of Mistral, just change the model in `.env`:

```env
OLLAMA_MODEL=llama3.1
```

Or use other models:
- `llama3.1:8b` - Llama 3.1 8B
- `llama3.1:70b` - Llama 3.1 70B (requires more RAM)
- `mistral` - Mistral 7B
- `codellama` - Code Llama
- `phi3` - Microsoft Phi-3

List all available models:
```bash
ollama list
```

## Running the Application

Now you can run the application normally:

**Terminal 1 - Ollama (must be running):**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm start
```

Open http://localhost:3000 and upload a financial document!

## Performance Tips

### 1. Model Size vs Performance

| Model | Size | Speed | Quality | RAM Needed |
|-------|------|-------|---------|------------|
| Mistral 7B | 4.4GB | Fast | Good | 8GB |
| Llama 3.1 8B | 4.7GB | Fast | Better | 8GB |
| Llama 3.1 70B | 40GB | Slower | Best | 64GB+ |

**Recommendation:** Start with `mistral` or `llama3.1:8b` for testing.

### 2. Speed Up Responses

If responses are slow, you can:

1. **Use a smaller model:**
   ```bash
   ollama pull phi3:mini
   ```
   Then set `OLLAMA_MODEL=phi3:mini`

2. **Enable GPU acceleration** (if you have NVIDIA GPU):
   Ollama automatically uses GPU if available

3. **Reduce context length** in `ai_analyzer.py`:
   Change `text[:15000]` to `text[:8000]` for faster processing

## Troubleshooting

### "Connection refused" error

**Problem:** Ollama server is not running

**Solution:**
```bash
ollama serve
```

### "Model not found" error

**Problem:** Model not downloaded

**Solution:**
```bash
ollama pull mistral
# or
ollama pull llama3.1
```

### Responses are very slow

**Problem:** Model is too large for your hardware

**Solution:** Use a smaller model
```bash
ollama pull phi3:mini
```
Then set `OLLAMA_MODEL=phi3:mini` in `.env`

### Out of memory error

**Problem:** Not enough RAM

**Solutions:**
1. Close other applications
2. Use a smaller model (phi3:mini, mistral, llama3.1:8b)
3. Restart your computer

## Verifying Ollama is Working

Test the API directly:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Hello, world!",
  "stream": false
}'
```

You should see a JSON response with the model's answer.

## Model Comparison

**Mistral 7B:**
- Size: 4.4GB
- Speed: Very fast
- Quality: Excellent for most tasks
- Best for: Quick analysis, testing

**Llama 3.1 8B:**
- Size: 4.7GB
- Speed: Fast
- Quality: Better reasoning
- Best for: Detailed financial analysis

**Choose based on:**
- **Mistral** if you want speed
- **Llama 3.1** if you want better quality analysis

## Privacy Benefits

✅ Your financial documents **never leave your computer**
✅ No API costs
✅ No internet required (after initial download)
✅ Complete data privacy
✅ Unlimited usage

## Next Steps

1. Install Ollama
2. Pull your preferred model (`mistral` or `llama3.1`)
3. Configure `.env` with `AI_PROVIDER=ollama`
4. Start Ollama server with `ollama serve`
5. Run the application!

For more models, visit: https://ollama.com/library

## Support

If you have issues:

1. Check Ollama is running: `curl http://localhost:11434`
2. Check model is installed: `ollama list`
3. Check backend logs for detailed errors
4. Try a different model

Enjoy analyzing financial statements with complete privacy! 🚀