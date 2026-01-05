# RecipaAI Setup & Deployment Guide

## 🚀 Local Development Setup

### Step 1: Clone & Navigate

```bash
git clone <repository>
cd Recipa-RAG-Assistant
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EOF
```

### Step 3: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Verify build
npm run build
```

### Step 4: Run Development Servers

**Terminal 1 - Backend:**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
```

**Access:**

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## ✅ Verification

### Run Tests

```bash
cd /path/to/project
python verify_system.py
```

### Quick API Test

```bash
# Test backend is running
curl http://localhost:8000/docs

# Test agent endpoint
curl -X POST http://localhost:8000/agent/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What recipes exist?","session_id":"test"}'
```

### Frontend Check

1. Open http://localhost:3000
2. Verify hero section loads
3. Test suggesting a question
4. Check architecture section displays
5. Verify team info shows correct roles

## 🐳 Docker Deployment

### Backend Docker

```dockerfile
# Dockerfile.backend
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

ENV OPENAI_API_KEY=""
ENV OPENAI_MODEL="gpt-4o-mini"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Docker

```dockerfile
# Dockerfile.frontend
FROM node:18-alpine

WORKDIR /app

COPY frontend/package*.json .
RUN npm install

COPY frontend .

RUN npm run build

ENV NEXT_PUBLIC_API_URL=http://localhost:8000

CMD ["npm", "start"]
```

### Docker Compose

```yaml
version: "3.8"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend/data:/app/data

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

### Run with Docker Compose

```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

## ☁️ Cloud Deployment (Vercel + Render)

### Frontend on Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel

# Set environment variable in Vercel dashboard
NEXT_PUBLIC_API_URL=https://your-backend-domain.onrender.com
```

### Backend on Render (Recommended)

**Option 1: Using Render Dashboard**

1. Create account at https://render.com
2. Connect GitHub repository
3. Click "New +" → "Web Service"
4. Configure:

   - **Name:** recipa-backend
   - **Environment:** Python 3.12
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or Starter for production)

5. Add Environment Variables (in Render dashboard):

   ```bash
   OPENAI_API_KEY=sk-your-key-here
   FRONTEND_URL=https://your-vercel-frontend.vercel.app
   ENVIRONMENT=production
   VECTORSTORE_DIR=./vectorstore/chroma
   PYTHONUNBUFFERED=1
   ```

6. Deploy: Click "Create Web Service" and watch logs

**Option 2: Using render.yaml**

Create `render.yaml` in root directory (already provided):

```bash
# File location: ./render.yaml
# Simply push to GitHub, Render reads this automatically
```

**Option 3: Using Render CLI**

```bash
# Install Render CLI
npm install -g @render-com/render-cli

# Login
render login

# Deploy
render deploy
```

### Backend on Railway (Alternative)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
cd backend
railway init

# Set environment
railway variables set OPENAI_API_KEY=sk-...
railway variables set ENVIRONMENT=production
railway variables set FRONTEND_URL=https://your-vercel-domain.vercel.app

# Deploy
railway up
```

## 🔧 Environment Variables

### Backend (.env)

```bash
# ========== REQUIRED ==========
OPENAI_API_KEY=sk-your-key-here

# ========== OPTIONAL (with defaults) ==========
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_COLLECTION=cookbook-recipes
VECTORSTORE_DIR=./vectorstore/chroma

# ========== PRODUCTION ==========
ENVIRONMENT=production
FRONTEND_URL=https://your-vercel-frontend.vercel.app
PORT=8000
PYTHONUNBUFFERED=1
```

### Frontend (.env.local)

```bash
# Point to your backend
# Local: http://localhost:8000
# Production: https://your-backend.onrender.com
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Render Dashboard Configuration

Set these in **Render Dashboard** → **Environment**:

| Variable           | Value                                | Notes                      |
| ------------------ | ------------------------------------ | -------------------------- |
| `OPENAI_API_KEY`   | `sk-...`                             | Your OpenAI API key        |
| `FRONTEND_URL`     | `https://your-vercel-app.vercel.app` | Your Vercel frontend URL   |
| `ENVIRONMENT`      | `production`                         | Set to `production`        |
| `PYTHONUNBUFFERED` | `1`                                  | Required for log streaming |
| `VECTORSTORE_DIR`  | `./vectorstore/chroma`               | Default is fine            |

### Vercel Dashboard Configuration

Set these in **Vercel Dashboard** → **Settings** → **Environment Variables**:

| Variable              | Value                               | Notes                   |
| --------------------- | ----------------------------------- | ----------------------- |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.onrender.com` | Your Render backend URL |

## 📦 Production Checklist

Before deploying to production, verify:

- [ ] `OPENAI_API_KEY` is set in Render/Railway dashboard (not in code)
- [ ] `FRONTEND_URL` is set to your Vercel domain
- [ ] CORS origins are configured correctly (updated via FRONTEND_URL env var)
- [ ] Database directory (`backend/data/memory/`) is writable
- [ ] Vectorstore path is accessible and initialized
- [ ] HTTPS is enabled (automatic on Render/Vercel)
- [ ] Error logging is configured to use stdout
- [ ] No debug logging in production
- [ ] API rate limiting considered (add if needed)
- [ ] Team has access to monitoring dashboards
- [ ] Rollback procedure documented

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for comprehensive pre-deployment checklist.

- [ ] Documentation updated
- [ ] Team trained on deployment process
- [ ] Rollback procedure documented

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: python verify_system.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        run: |
          npm install -g @railway/cli
          railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## 🆘 Troubleshooting

### Backend Won't Start

```bash
# Check port 8000 is free
lsof -i :8000

# Clear cache
find . -type d -name __pycache__ -exec rm -r {} +

# Reinstall
pip install --force-reinstall -r requirements.txt
```

### Frontend Build Fails

```bash
# Clear node_modules
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

### API Connection Issues

```bash
# Verify backend is running
curl http://localhost:8000/docs

# Check frontend API URL
cat frontend/.env.local
```

### LLM API Errors

```bash
# Verify API key
echo $OPENAI_API_KEY

# Check OpenAI quota
# Visit https://platform.openai.com/account/billing

# Try with smaller query
curl -X POST http://localhost:8000/agent/ask \
  -d '{"question":"Hi","session_id":"test"}'
```

## 📈 Scaling

### Load Balancing

```bash
# Run multiple backend instances
for i in {8001..8003}; do
  uvicorn app.main:app --port $i &
done
```

### Database Optimization

```bash
# Backup SQLite
cp backend/data/memory/agent_memory.sqlite3 backup_$(date +%s).db

# Consider PostgreSQL for production
# Update DATABASE_URL in config.py
```

### Caching Layer

```bash
# Add Redis for response caching
# Update backend/app/config.py to use Redis client
# Cache follow-up rewrites and frequently asked questions
```

## 🔒 Security Hardening

### API Protection

```bash
# Add API key requirement
# Implement rate limiting
# Add request validation
```

### Database Security

```bash
# Use environment variable for database path
# Enable SQLite encryption for sensitive data
# Regular backups with encrypted storage
```

### Frontend Security

```bash
# Enable CSP headers
# CORS configuration
# Input sanitization
```

**Last Updated:** January 5, 2026
