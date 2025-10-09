#!/bin/bash

# Finstat Quick Deployment Script
# This script helps deploy Finstat to your on-premise server

set -e  # Exit on error

echo "🚀 Finstat Deployment Script"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ Please do not run as root${NC}"
   exit 1
fi

echo "📋 Step 1: Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION}${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js ${NODE_VERSION}${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm ${NPM_VERSION}${NC}"

echo ""
echo "📦 Step 2: Setting up backend..."

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
echo "Installing Python dependencies (this may take a few minutes)..."
pip install -r requirements.txt -q

# Create directories
mkdir -p uploads outputs data/chroma_db data/cache logs
touch uploads/.gitkeep outputs/.gitkeep

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit backend/.env with your configuration${NC}"
    echo -e "${YELLOW}   - Set OLLAMA_BASE_URL if Ollama is on different host${NC}"
    echo -e "${YELLOW}   - Set EMBEDDING_MODEL_PATH to your model location${NC}"
fi

cd ..

echo ""
echo "🎨 Step 3: Setting up frontend..."

cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${YELLOW}📝 Please edit frontend/.env with your server IP/domain${NC}"
fi

cd ..

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Configure backend environment:"
echo "   ${YELLOW}nano backend/.env${NC}"
echo "   - Set EMBEDDING_MODEL_PATH to your model location"
echo "   - Verify OLLAMA_BASE_URL"
echo ""
echo "2. Configure frontend environment:"
echo "   ${YELLOW}nano frontend/.env${NC}"
echo "   - Set BACKEND_URL to your server address"
echo ""
echo "3. Start services:"
echo ""
echo "   Option A - Development mode:"
echo "   ${GREEN}# Terminal 1 - Backend${NC}"
echo "   ${YELLOW}cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000${NC}"
echo ""
echo "   ${GREEN}# Terminal 2 - Frontend${NC}"
echo "   ${YELLOW}cd frontend && npm run dev${NC}"
echo ""
echo "   Option B - Production with PM2:"
echo "   ${YELLOW}npm install -g pm2${NC}"
echo "   ${YELLOW}pm2 start ecosystem.config.js${NC}"
echo "   ${YELLOW}pm2 save${NC}"
echo "   ${YELLOW}pm2 startup${NC}"
echo ""
echo "4. Access application:"
echo "   Frontend: ${GREEN}http://localhost:3000${NC}"
echo "   Backend API: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo "📖 For detailed deployment guide, see: ${YELLOW}DEPLOYMENT.md${NC}"
echo ""
