# Docker Deployment Guide

## 🐳 Quick Start with Docker

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Ollama running on host (with models downloaded)
- Embedding model (BGE-M3) on host

### 1. Clone Repository

```bash
git clone https://github.com/ajnurjaya/finstat.git
cd finstat
```

### 2. Configure Environment

Create `.env` file from template:

```bash
cp .env.docker .env
```

Edit `.env` with your server configuration:

```bash
nano .env
```

**Required settings:**

```env
# Path to your BGE-M3 model on host machine
EMBEDDING_MODEL_PATH=/path/to/your/bge-m3

# Ollama URL (host.docker.internal accesses host from container)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Ollama model name
OLLAMA_MODEL=llama3.1:8b-instruct-q5_K_M
```

### 3. Deploy

**Option A: Without Nginx (Simple)**

```bash
docker-compose up -d
```

**Option B: With Nginx (Recommended for Production)**

```bash
docker-compose --profile with-nginx up -d
```

### 4. Access Application

- **Without Nginx:**
  - Frontend: http://localhost:3000
  - Backend API: http://localhost:8000/docs

- **With Nginx:**
  - Application: http://localhost
  - Backend API: http://localhost/api/docs

### 5. Verify Deployment

```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f

# Check backend health
curl http://localhost:8000/docs

# Check Ollama connection from container
docker exec finstat-backend curl http://host.docker.internal:11434/api/tags
```

## 📦 Docker Architecture

```
┌─────────────────────────────────────────┐
│         Host Machine                     │
│  ┌────────────┐     ┌──────────────┐   │
│  │   Ollama   │     │ BGE-M3 Model │   │
│  │ :11434     │     │   (mounted)  │   │
│  └────────────┘     └──────────────┘   │
│         │                   │           │
│         └───────┬───────────┘           │
│                 │                       │
│  ┌──────────────┴──────────────────┐   │
│  │      Docker Network             │   │
│  │  ┌────────────┐  ┌───────────┐ │   │
│  │  │  Backend   │  │ Frontend  │ │   │
│  │  │   :8000    │  │   :3000   │ │   │
│  │  └────────────┘  └───────────┘ │   │
│  │         │              │        │   │
│  │  ┌──────┴──────────────┴────┐  │   │
│  │  │      Nginx (optional)    │  │   │
│  │  │          :80             │  │   │
│  │  └──────────────────────────┘  │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 🔧 Configuration Details

### Volume Mounts

The following directories are persisted:

```yaml
volumes:
  - ./backend/uploads:/app/uploads      # Uploaded documents
  - ./backend/outputs:/app/outputs      # Exported Excel files
  - ./backend/data:/app/data            # ChromaDB database
  - ./backend/logs:/app/logs            # Application logs
  - ${EMBEDDING_MODEL_PATH}:/app/models/bge-m3  # Embedding model (read-only)
```

### Environment Variables

**Backend Container:**

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PROVIDER` | AI provider (ollama/anthropic/openai) | `ollama` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.1:8b-instruct-q5_K_M` |
| `EMBEDDING_MODEL_PATH` | Path to BGE-M3 model | `/app/models/bge-m3` |
| `CHROMA_PERSIST_DIR` | ChromaDB data directory | `/app/data/chroma_db` |

**Frontend Container:**

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Node environment | `production` |
| `PORT` | Frontend port | `3000` |
| `BACKEND_URL` | Backend API URL | `http://backend:8000` |

## 🚀 Production Deployment

### Using Docker Swarm

**1. Initialize Swarm:**

```bash
docker swarm init
```

**2. Create Stack File (`docker-stack.yml`):**

```yaml
version: '3.8'

services:
  backend:
    image: finstat-backend:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    networks:
      - finstat-network
    volumes:
      - backend-data:/app/data
      - backend-uploads:/app/uploads
      - backend-outputs:/app/outputs

  frontend:
    image: finstat-frontend:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    networks:
      - finstat-network
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    deploy:
      replicas: 1
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - finstat-network

networks:
  finstat-network:
    driver: overlay

volumes:
  backend-data:
  backend-uploads:
  backend-outputs:
```

**3. Deploy Stack:**

```bash
docker stack deploy -c docker-stack.yml finstat
```

### Using Kubernetes

**1. Build and Push Images:**

```bash
# Build images
docker build -t your-registry/finstat-backend:latest ./backend
docker build -t your-registry/finstat-frontend:latest ./frontend

# Push to registry
docker push your-registry/finstat-backend:latest
docker push your-registry/finstat-frontend:latest
```

**2. Create Kubernetes Manifests:**

See `kubernetes/` directory for example manifests (create if needed).

## 🔍 Troubleshooting

### Container fails to start

**Check logs:**
```bash
docker-compose logs backend
docker-compose logs frontend
```

**Check configuration:**
```bash
docker exec finstat-backend env | grep -E "(OLLAMA|EMBEDDING)"
```

### Cannot connect to Ollama

**Test from host:**
```bash
curl http://localhost:11434/api/tags
```

**Test from container:**
```bash
docker exec finstat-backend curl http://host.docker.internal:11434/api/tags
```

**If fails on Linux**, add to docker-compose.yml:
```yaml
services:
  backend:
    network_mode: host
```

### Embedding model not found

**Check mount:**
```bash
docker exec finstat-backend ls -la /app/models/bge-m3
```

**Verify path in .env:**
```bash
cat .env | grep EMBEDDING_MODEL_PATH
```

**Download model if needed:**
```bash
# On host machine
pip install huggingface-hub
huggingface-cli download BAAI/bge-m3 --local-dir /path/to/models/bge-m3
```

### Permission errors

**Fix permissions:**
```bash
sudo chown -R $(id -u):$(id -g) backend/uploads backend/outputs backend/data backend/logs
```

### Out of memory

**Increase Docker memory:**
```bash
# Docker Desktop: Settings → Resources → Memory
# Or in daemon.json:
{
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  }
}
```

**Reduce workers in Dockerfile:**
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

## 📊 Management Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
# All services
docker-compose restart

# Specific service
docker-compose restart backend
docker-compose restart frontend
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data

```bash
# Backup ChromaDB and uploads
docker run --rm -v finstat_backend-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/finstat-backup-$(date +%Y%m%d).tar.gz /data

# Restore
docker run --rm -v finstat_backend-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/finstat-backup-20241009.tar.gz -C /
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker rmi finstat-backend finstat-frontend

# Clean up unused resources
docker system prune -a
```

## 🔒 Security Best Practices

### 1. Use Secrets for Sensitive Data

```yaml
services:
  backend:
    secrets:
      - ollama_api_key
    environment:
      - OLLAMA_API_KEY_FILE=/run/secrets/ollama_api_key

secrets:
  ollama_api_key:
    file: ./secrets/ollama_api_key.txt
```

### 2. Run as Non-Root User

Add to Dockerfile:

```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### 3. Enable HTTPS with Nginx

Update nginx.conf:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    # ... rest of config
}
```

### 4. Limit Resource Usage

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## 📈 Monitoring

### Health Checks

Built-in health checks monitor:
- Backend: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

Check status:
```bash
docker-compose ps
```

### Prometheus Metrics (Optional)

Add to docker-compose.yml:

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

## 📞 Support

- **Documentation**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **GitHub Issues**: https://github.com/ajnurjaya/finstat/issues
- **Docker Hub**: (publish images here)