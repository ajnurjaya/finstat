# Finstat Deployment Guide - On-Premise Server

## Prerequisites on Server

✅ **Already Provided on Server:**
- Ollama (running)
- Embedding model (BGE-M3 or similar)

📦 **Required Software:**
- Python 3.11+
- Node.js 18+
- Git

## Deployment Steps

### 1. Clone Repository

```bash
cd /path/to/deployment
git clone https://github.com/ajnurjaya/finstat.git
cd finstat
```

### 2. Backend Setup

#### A. Create Python Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows
```

#### B. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### C. Configure Environment Variables

Create `.env` file in `backend/` directory:

```bash
cp .env.example .env
nano .env  # or use vi, vim, or any text editor
```

**Edit `.env` with your server configuration:**

```env
# === SERVER CONFIGURATION ===
HOST=0.0.0.0
PORT=8000

# === AI PROVIDER (Ollama on your server) ===
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434  # Change if Ollama is on different host/port
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M  # Change to your model

# Alternative providers (commented out)
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_key_here
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# AI_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
# OPENAI_MODEL=gpt-4o-mini

# === EMBEDDING MODEL (on your server) ===
EMBEDDING_MODEL_PATH=/path/to/your/embedding/model  # e.g., /models/bge-m3
# If model is not downloaded yet, use HuggingFace name:
# EMBEDDING_MODEL_PATH=BAAI/bge-m3

# === DIRECTORIES ===
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
DATA_DIR=./data

# === DATABASE ===
CHROMA_PERSIST_DIR=./data/chroma_db

# === OPTIONAL: Logging ===
LOG_LEVEL=INFO
```

#### D. Download Embedding Model (if not already on server)

**Option 1: If model already exists on server**
```bash
# Just point EMBEDDING_MODEL_PATH to the model directory
# Example: EMBEDDING_MODEL_PATH=/opt/models/bge-m3
```

**Option 2: Download to server**
```bash
# Install huggingface-cli
pip install huggingface-hub[cli]

# Download model
huggingface-cli download BAAI/bge-m3 --local-dir ./models/bge-m3

# Update .env
# EMBEDDING_MODEL_PATH=./models/bge-m3
```

#### E. Create Required Directories

```bash
mkdir -p uploads outputs data/chroma_db data/cache
touch uploads/.gitkeep outputs/.gitkeep
```

#### F. Test Backend

```bash
# Test import and configuration
python -c "from app.utils import AIAnalyzer; print('✅ Backend setup OK')"

# Start backend server (test mode)
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Test in browser:** `http://your-server-ip:8000/docs`

### 3. Frontend Setup

#### A. Install Node Dependencies

```bash
cd ../frontend
npm install
```

#### B. Configure Frontend Environment

Create `.env` file in `frontend/` directory:

```bash
cp .env.example .env
nano .env
```

**Edit `.env`:**

```env
# Frontend server
PORT=3000

# Backend API URL (change to your server IP)
BACKEND_URL=http://your-server-ip:8000
```

#### C. Test Frontend

```bash
# Development mode
npm run dev

# Production build (recommended for deployment)
npm run build
npm start
```

**Test in browser:** `http://your-server-ip:3000`

### 4. Production Deployment

#### Option A: Using PM2 (Recommended)

**Install PM2:**
```bash
npm install -g pm2
```

**Create PM2 ecosystem file** `ecosystem.config.js` in project root:

```javascript
module.exports = {
  apps: [
    {
      name: 'finstat-backend',
      cwd: './backend',
      script: 'venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
      },
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
    {
      name: 'finstat-frontend',
      cwd: './frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
```

**Start services:**
```bash
# Create logs directory
mkdir -p logs

# Start both services
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup auto-start on server reboot
pm2 startup
# Follow the instructions shown

# Monitor services
pm2 status
pm2 logs finstat-backend
pm2 logs finstat-frontend
```

**PM2 Management Commands:**
```bash
pm2 restart finstat-backend   # Restart backend
pm2 restart finstat-frontend  # Restart frontend
pm2 stop all                   # Stop all services
pm2 delete all                 # Remove all services
pm2 monit                      # Real-time monitoring
```

#### Option B: Using Systemd (Linux)

**Create backend service** `/etc/systemd/system/finstat-backend.service`:

```ini
[Unit]
Description=Finstat Backend API
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/finstat/backend
Environment="PATH=/path/to/finstat/backend/venv/bin"
ExecStart=/path/to/finstat/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Create frontend service** `/etc/systemd/system/finstat-frontend.service`:

```ini
[Unit]
Description=Finstat Frontend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/finstat/frontend
ExecStart=/usr/bin/npm start
Environment="NODE_ENV=production"
Environment="PORT=3000"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable finstat-backend finstat-frontend
sudo systemctl start finstat-backend finstat-frontend

# Check status
sudo systemctl status finstat-backend
sudo systemctl status finstat-frontend

# View logs
sudo journalctl -u finstat-backend -f
sudo journalctl -u finstat-frontend -f
```

### 5. Reverse Proxy with Nginx (Optional but Recommended)

**Install Nginx:**
```bash
sudo apt install nginx  # Ubuntu/Debian
sudo yum install nginx  # CentOS/RHEL
```

**Create Nginx configuration** `/etc/nginx/sites-available/finstat`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your-server-ip

    client_max_body_size 100M;  # Allow large PDF uploads

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout for long-running requests (document parsing)
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
    }
}
```

**Enable and restart Nginx:**
```bash
sudo ln -s /etc/nginx/sites-available/finstat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Firewall Configuration

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# If accessing directly (without Nginx)
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend

sudo ufw enable
```

### 7. Verify Deployment

**Check all services are running:**
```bash
pm2 status
# OR
sudo systemctl status finstat-backend finstat-frontend nginx
```

**Test endpoints:**
```bash
# Backend health check
curl http://localhost:8000/docs

# Frontend
curl http://localhost:3000

# Through Nginx
curl http://your-server-ip/
curl http://your-server-ip/api/docs
```

**Test Ollama connection:**
```bash
curl http://localhost:11434/api/tags
```

**Test embedding model loading:**
```bash
cd backend
source venv/bin/activate
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('/path/to/your/model'); print('✅ Model loaded')"
```

## Troubleshooting

### Backend won't start

**Check Python environment:**
```bash
cd backend
source venv/bin/activate
python -c "import sys; print(sys.version)"
pip list | grep -E "(fastapi|uvicorn|sentence-transformers)"
```

**Check .env configuration:**
```bash
cat .env | grep -E "(OLLAMA|EMBEDDING)"
```

**Test Ollama connection:**
```bash
curl http://localhost:11434/api/tags
```

### Embedding model not loading

**Option 1: Use model from server location**
```bash
# Find where model is stored on server
find / -name "bge-m3" -type d 2>/dev/null
# Update EMBEDDING_MODEL_PATH in .env
```

**Option 2: Download model**
```bash
pip install huggingface-hub
huggingface-cli download BAAI/bge-m3 --local-dir ./models/bge-m3
```

### Permission errors

```bash
# Fix directory permissions
chmod -R 755 uploads outputs data
chown -R your-username:your-group finstat/
```

### Out of memory

**For embedding model:**
- Use quantized model (smaller size)
- Increase swap space
- Use CPU-only mode

**Edit backend/.env:**
```env
# Force CPU usage (if GPU memory issues)
CUDA_VISIBLE_DEVICES=-1
```

### Ollama connection refused

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama logs
journalctl -u ollama -f

# Restart Ollama
sudo systemctl restart ollama
```

## Maintenance

### Update application

```bash
cd finstat
git pull origin main

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
pm2 restart finstat-backend

# Frontend
cd ../frontend
npm install
npm run build
pm2 restart finstat-frontend
```

### Backup data

```bash
# Backup ChromaDB and uploaded files
tar -czf finstat-backup-$(date +%Y%m%d).tar.gz \
  backend/data/chroma_db \
  backend/uploads \
  backend/outputs
```

### Monitor logs

```bash
# PM2
pm2 logs finstat-backend --lines 100
pm2 logs finstat-frontend --lines 100

# Systemd
sudo journalctl -u finstat-backend -f
sudo journalctl -u finstat-frontend -f
```

## Performance Tuning

### Backend (main.py)

Add workers for better performance:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### ChromaDB

Optimize batch size in `.env`:
```env
CHROMA_BATCH_SIZE=1000
```

### Nginx Caching

Add to Nginx config:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g inactive=60m;
proxy_cache my_cache;
```

## Support

For issues, check:
- Application logs in `logs/` directory
- Ollama status: `systemctl status ollama`
- Nginx logs: `/var/log/nginx/error.log`
- GitHub issues: https://github.com/ajnurjaya/finstat/issues