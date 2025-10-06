# Financial Statement Analyzer

A full-stack application for analyzing financial statements with AI-powered summarization, insights, and table extraction.

## Features

- **Multi-format Support**: Process PDF, TXT, and Word documents
- **AI Summarization**: Automatic summarization of financial statements
- **Insight Generation**: Extract key financial insights and metrics
- **Table Extraction**: Extract all tables and export to Excel
- **Local & Cloud AI**: Works with local LLMs (Ollama) or cloud APIs (OpenAI, Anthropic)
- **Web Interface**: User-friendly Node.js frontend
- **REST API**: Python backend with FastAPI

## Architecture

- **Frontend**: Node.js + Express + HTML/CSS/JavaScript
- **Backend**: Python + FastAPI
- **Document Processing**: PyPDF2, python-docx, pdfplumber
- **AI Options**:
  - **Local LLMs via Ollama** (Mistral, Llama 3.1, etc.) - **FREE & Private** ✨
  - OpenAI API (GPT-4, GPT-3.5)
  - Anthropic Claude API
- **Table Extraction**: pdfplumber, python-docx
- **Excel Export**: openpyxl

## Directory Structure

```
Finstat/
├── backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── services/ # Business logic
│   │   └── utils/    # Utilities
│   ├── requirements.txt
│   └── main.py
├── frontend/         # Node.js frontend
│   ├── public/       # Static files
│   ├── src/          # Source code
│   ├── package.json
│   └── server.js
└── README.md

```

## Quick Start

### Option 1: Using Local LLM (FREE - Recommended for Testing) 🚀

**Perfect if you have Mistral or Llama 3.1 installed!**

See **[OLLAMA_SETUP.md](OLLAMA_SETUP.md)** for detailed instructions.

Quick version:
```bash
# 1. Install and start Ollama
ollama serve

# 2. Pull your model (in another terminal)
ollama pull mistral
# or
ollama pull llama3.1

# 3. Setup backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: Set AI_PROVIDER=ollama and OLLAMA_MODEL=mistral
python main.py

# 4. Setup frontend (in another terminal)
cd frontend
npm install
npm start
```

Open http://localhost:3000

### Option 2: Using Cloud APIs (OpenAI or Anthropic)

```bash
# 1. Setup backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: Set AI_PROVIDER=openai or anthropic and add your API key

# 2. Setup frontend
cd frontend
npm install
cp .env.example .env
npm start
```

## Configuration

**For Local LLM (Ollama):**
```env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

**For OpenAI:**
```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

**For Anthropic:**
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

See [SETUP.md](SETUP.md) for detailed configuration options.

## Usage

1. Start the backend server (runs on port 8000)
2. Start the frontend server (runs on port 3000)
3. Open browser to http://localhost:3000
4. Upload a financial statement document
5. View summary, insights, and download extracted tables

## API Endpoints

- `POST /api/upload` - Upload document
- `POST /api/analyze` - Analyze document and get summary
- `POST /api/extract-tables` - Extract tables to Excel
- `GET /api/download/{file_id}` - Download Excel file
