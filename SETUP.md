# Setup Guide - Financial Statement Analyzer

## Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** (for frontend)
- **API Key** from either:
  - Anthropic Claude API
  - OpenAI API

## Quick Start

### 1. Clone and Navigate

```bash
cd Finstat
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

**Edit `backend/.env`** and add your API key:

```env
# Choose your AI provider
AI_PROVIDER=anthropic  # or openai

# Add your API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here

# Server settings
PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### 3. Frontend Setup

Open a **new terminal** window:

```bash
cd Finstat/frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

**Edit `frontend/.env`** (usually no changes needed):

```env
PORT=3000
BACKEND_URL=http://localhost:8000
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # if not already activated
python main.py
```

You should see: `INFO: Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

You should see: `Frontend server running on http://localhost:3000`

### 5. Access the Application

Open your browser and go to:
```
http://localhost:3000
```

## How to Use

1. **Upload Document**
   - Click "Select File" or drag and drop
   - Supported formats: PDF, DOCX, TXT
   - Max size: 50MB

2. **AI Analysis**
   - Automatic AI-powered analysis
   - View Executive Summary, Insights, or Full Analysis
   - Check extracted document text

3. **Extract Tables**
   - Click "Extract Tables to Excel"
   - Download the Excel file with all tables

## API Endpoints

### Backend API (Port 8000)

- `POST /api/upload` - Upload document
- `POST /api/analyze` - Analyze document
- `GET /api/analyze/{file_id}/text` - Get extracted text
- `POST /api/extract-tables` - Extract tables
- `GET /api/download/{file_id}` - Download Excel file
- `GET /api/tables/{file_id}/preview` - Preview tables

### Frontend (Port 3000)

- `GET /` - Home page (upload)
- `GET /analyze/:fileId` - Analysis results page

## Troubleshooting

### Backend won't start

1. Check if port 8000 is available:
   ```bash
   lsof -i :8000  # macOS/Linux
   netstat -ano | findstr :8000  # Windows
   ```

2. Verify API key is set correctly in `.env`

3. Check all dependencies are installed:
   ```bash
   pip list
   ```

### Frontend won't start

1. Check if port 3000 is available

2. Verify `node_modules` installed:
   ```bash
   npm install
   ```

3. Check backend URL in `.env` matches running backend

### AI Analysis fails

1. Verify API key is correct
2. Check AI provider setting matches your API key
3. Ensure you have API credits/quota available
4. Check backend logs for detailed error

### Table extraction fails

1. Ensure document contains actual tables
2. PDF tables should be text-based (not images)
3. Check backend logs for specific errors

### CORS errors

1. Verify `CORS_ORIGINS` in backend `.env` includes frontend URL
2. Make sure both servers are running
3. Try restarting both backend and frontend

## Development Mode

For development with auto-reload:

**Backend:**
```bash
# Already enabled in main.py with reload=True
python main.py
```

**Frontend:**
```bash
npm install -g nodemon  # if not installed
npm run dev  # uses nodemon for auto-reload
```

## Production Deployment

### Backend

```bash
# Use gunicorn for production
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Frontend

```bash
# Set NODE_ENV
export NODE_ENV=production

# Update BACKEND_URL to production backend
node server.js
```

## Environment Variables Reference

### Backend `.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `AI_PROVIDER` | AI provider: `anthropic` or `openai` | `anthropic` |
| `ANTHROPIC_MODEL` | Claude model name | `claude-3-5-sonnet-20241022` |
| `OPENAI_MODEL` | GPT model name | `gpt-4-turbo-preview` |
| `PORT` | Backend server port | `8000` |
| `HOST` | Backend host | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `MAX_FILE_SIZE` | Max upload size in bytes | `50000000` (50MB) |
| `UPLOAD_DIR` | Upload directory | `./uploads` |
| `OUTPUT_DIR` | Output directory | `./outputs` |

### Frontend `.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Frontend server port | `3000` |
| `BACKEND_URL` | Backend API URL | `http://localhost:8000` |
| `NODE_ENV` | Environment | `development` |

## Getting API Keys

### Anthropic Claude API

1. Visit https://console.anthropic.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy and paste into `.env`

### OpenAI API

1. Visit https://platform.openai.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy and paste into `.env`

## Support

For issues or questions:
- Check the logs in both backend and frontend terminals
- Verify all environment variables are set correctly
- Ensure API keys have available credits
- Check that all dependencies are installed

## Next Steps

- Customize the UI in `frontend/public/css/style.css`
- Add more AI prompts in `backend/app/utils/ai_analyzer.py`
- Enhance table detection in `backend/app/utils/table_extractor.py`
- Add authentication for multi-user support
