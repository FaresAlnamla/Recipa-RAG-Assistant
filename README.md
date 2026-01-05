# RecipaAI — Intelligent Multi-Agent RAG System

A **production-grade multi-agent retrieval-augmented generation (RAG) system** that answers questions about _The Low-Cost Cookbook_ with conversation memory, intelligent routing, and follow-up question detection.

## 🎯 Project Overview

**RecipaAI** is an end-to-end application demonstrating advanced NLP and software engineering concepts:

- **Retrieval-Augmented Generation (RAG):** Grounds answers in real cookbook content, avoiding hallucinations
- **Multi-Agent Orchestration:** Router → Retrieval → LLM → Evaluation → Memory pipeline
- **Intelligent Follow-up Detection:** Automatically understands context ("How long?" → "For chocolate cake, how long to cook?")
- **Production-Grade Architecture:** Clean code, comprehensive documentation, error handling, cloud deployment
- **Full-Stack Development:** FastAPI backend, Next.js frontend, SQLite persistence, vector search with Chroma

**Perfect for:** Portfolio projects, academic demonstration, recruitment showcasing, learning full-stack development.

## 🏗️ System Architecture

### 6-Step Pipeline

```
┌─────────────┐
│   Question  │
└──────┬──────┘
       │
   1️⃣  ROUTER
   ├─ Classifies: Cookbook vs Out-of-Scope
   ├─ Keywords: recipes, ingredients, cooking, budget
   └─ Routes to appropriate handler
       │
   2️⃣  RETRIEVAL
   ├─ Semantic search via Chroma vector store
   ├─ Embedded with OpenAI embeddings
   └─ Returns top-k relevant chunks
       │
   3️⃣  LLM
   ├─ GPT-4o-mini generates answer
   ├─ Grounded in retrieved context only
   └─ Includes conversation history
       │
   4️⃣  EVALUATION
   ├─ Confidence scoring
   ├─ Fact verification against context
   └─ Determines answer quality
       │
   5️⃣  MEMORY
   ├─ SQLite conversation storage
   ├─ Session-based history
   └─ Follow-up context injection
       │
   6️⃣  RESPONSE
   ├─ Streams markdown to frontend
   ├─ Includes sources (book, page)
   └─ Real-time token delivery
       │
   ✅  Answer
```

### Key Innovation: Follow-Up Detection

The system understands conversational context:

```
User: "What recipes exist?"
AI: "Here are budget-friendly recipes: pasta, lentil soup, rice bowls..."

User: "How long to cook the pasta?"  ← System detects follow-up
AI: "For pasta, cook for 8-10 minutes..." ← Automatically adds context
```

## 📊 Technology Stack

### Backend

- **FastAPI** (Python 3.12) — High-performance async API
- **LangChain** — LLM orchestration and RAG pipeline
- **Chroma** — Vector database for semantic search
- **OpenAI API** — GPT-4o-mini for generation
- **SQLite** — Conversation persistence
- **Pydantic** — Data validation

### Frontend

- **Next.js 14** — React framework with server-side rendering
- **TypeScript** — Type-safe development
- **TailwindCSS** — Responsive UI styling
- **React Hooks** — State management (localStorage for history)

### Deployment

- **Render** — Backend hosting
- **Vercel** — Frontend hosting
- **GitHub** — Source control & CI/CD

## ✨ Key Features

| Feature                         | Implementation                                       |
| ------------------------------- | ---------------------------------------------------- |
| 🔄 **Multi-Turn Conversations** | SQLite session storage + automatic context rewriting |
| 💾 **Persistent Memory**        | SQLite database with session-based retrieval         |
| 🎯 **Smart Routing**            | Multi-pattern question classification                |
| 🔍 **Semantic Search**          | Chroma + OpenAI embeddings for relevance             |
| ⚡ **Streaming Responses**      | Real-time token delivery to frontend                 |
| 📚 **Source Attribution**       | Full book name and page numbers for every answer     |
| 🛡️ **Confidence Scoring**       | Evaluation module validates answer quality           |
| 🚀 **Production Ready**         | Error handling, logging, CORS, security checks       |
| 📱 **Responsive UI**            | Mobile-friendly React components                     |
| ☁️ **Cloud Deployment**         | One-click deployment to Render + Vercel              |

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** (backend)
- **Node.js 18+** (frontend)
- **OpenAI API Key** (free trial or paid account)
- **Git** (for version control)

### 1️⃣ Backend Setup (FastAPI)

```bash
# Navigate to backend
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
cat > .env << EOF
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EOF

# Run the server
uvicorn app.main:app --reload --port 8000
```

**Backend runs at:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs  
**Health Check:** http://localhost:8000/health

### 2️⃣ Frontend Setup (Next.js)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

**Frontend runs at:** http://localhost:3000

### 3️⃣ Test the System

1. Open http://localhost:3000 in your browser
2. Try asking: _"What cheap recipes are in the cookbook?"_
3. Follow up with: _"Can I use eggs instead?"_
4. Check the Architecture section on the homepage
5. View your conversation history

## 🧪 How It Works

### Example Interaction

```
User Input: "What are some budget-friendly dinner recipes?"

Step 1 (Router):
├─ Detects: question about recipes + budget
└─ Decision: COOKBOOK_RELATED → proceed

Step 2 (Retrieval):
├─ Search embedding: "budget friendly dinner recipes"
├─ Vector similarity search in Chroma
└─ Returns: [pasta_page_14, lentil_soup_page_22, rice_page_35]

Step 3 (LLM):
├─ Prompt: "Based on these cookbook sections, list budget recipes"
├─ Context: Actual text from pages 14, 22, 35
└─ Response: "The cookbook includes pasta ($1/serving), lentil soup ($0.80), rice bowls ($0.50)"

Step 4 (Evaluation):
├─ Check: Are all facts in retrieved context? ✅
├─ Confidence: 0.95 (very high)
└─ Quality: SUPPORTED

Step 5 (Memory):
├─ Store: question + answer in SQLite
├─ Session ID: user-123
└─ Timestamp: 2026-01-05 15:30:00

Step 6 (Response):
└─ Send to frontend with sources and confidence score
```

### Follow-Up Example

```
User: "How long to cook them?"

Step 1 (Follow-Up Detection):
├─ Input: "How long to cook them?"
├─ Keywords found: "how long", "cook"
├─ History: Last question was about recipes
└─ Rewrite: "For the recipes mentioned (pasta, lentil soup, rice), how long to cook?"

Step 2-6: Same pipeline with rewritten context
Result: "Pasta: 8-10 mins. Lentil soup: 30 mins. Rice: 20 mins."
```

## 📁 Project Structure

```
Recipa-RAG-Assistant/
│
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── main.py                # Entry point, CORS, routes
│   │   ├── config.py              # Environment variables, settings
│   │   │
│   │   ├── agent/                 # Multi-agent orchestration
│   │   │   ├── agent.py           # Main orchestration logic
│   │   │   ├── router.py          # Question routing (cookbook vs other)
│   │   │   ├── memory.py          # SQLite conversation storage
│   │   │   └── eval.py            # Answer evaluation & scoring
│   │   │
│   │   ├── rag/                   # Retrieval-Augmented Generation
│   │   │   ├── retrieval.py       # Semantic search pipeline
│   │   │   ├── llm.py             # LLM prompting and generation
│   │   │   └── ingest.py          # PDF ingestion (one-time setup)
│   │   │
│   │   └── api/                   # REST endpoints
│   │       └── agent_routes.py    # /agent/ask, /agent/history
│   │
│   ├── requirements.txt            # Python dependencies
│   └── .env                        # Environment variables (local only)
│
├── frontend/                       # Next.js 14 application
│   ├── app/
│   │   ├── page.tsx              # Home page
│   │   ├── layout.tsx            # Root layout
│   │   └── globals.css           # Global styles
│   │
│   ├── components/
│   │   ├── home/                 # Landing page sections
│   │   │   ├── Hero.tsx          # Header with badge
│   │   │   ├── QAEngine.tsx      # Question/answer interface
│   │   │   ├── Architecture.tsx  # 6-step pipeline visualization
│   │   │   └── Team.tsx          # Team members
│   │   │
│   │   ├── layout/               # Reusable layouts
│   │   │   ├── Navbar.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   └── ui/                   # Shadcn UI components
│   │
│   ├── lib/                      # Utilities
│   │   ├── api.ts               # API client
│   │   ├── constants.ts         # Configuration
│   │   └── utils.ts             # Helper functions
│   │
│   ├── package.json             # Node dependencies
│   └── .env.local               # Frontend config (local only)
│
├── 📚 Documentation
│   ├── README.md                    # This file
│   ├── PRODUCTION.md                # Architecture & API details
│   ├── SETUP.md                     # Deployment guides
│   ├── DEPLOYMENT_CHECKLIST.md      # Pre-deployment verification
│   └── render.yaml                  # Render configuration
│
└── .env.example                 # Environment template
```

## 🎓 Learning Outcomes

This project demonstrates:

### **For Students:**

- ✅ Full-stack development (backend + frontend)
- ✅ Multi-agent system orchestration
- ✅ Retrieval-augmented generation (RAG) patterns
- ✅ API design and REST best practices
- ✅ React and TypeScript patterns
- ✅ SQLite database design
- ✅ Environment variable management
- ✅ Git workflows and version control

### **For Tech Recruiters:**

- ✅ Production-grade code quality
- ✅ Comprehensive error handling
- ✅ Cloud deployment experience
- ✅ API documentation
- ✅ Type safety (TypeScript, Pydantic)
- ✅ Test coverage and verification
- ✅ Clean architecture patterns
- ✅ LLM integration (prompt engineering, token streaming)

### **For Supervisors/Evaluators:**

- ✅ Clear project scope (RAG system for cookbook)
- ✅ Measurable features (6-step pipeline, follow-up detection)
- ✅ Documentation (README, PRODUCTION.md, comments)
- ✅ Testing approach (automated verification)
- ✅ Deployment readiness (production checklist)
- ✅ Team collaboration (clear roles)

## 🔒 API Reference

### **Ask Question (with History)**

```http
POST /agent/ask
Content-Type: application/json

{
  "question": "What are cheap recipes?",
  "session_id": "user-123"
}

Response:
{
  "answer": "## Budget Recipes\n\n1. Pasta...",
  "sources": [
    {
      "book_name": "THE LOW-COST COOKBOOK",
      "page": 14,
      "snippet": "Pasta is a budget..."
    }
  ],
  "evaluation": {
    "supported": true,
    "confidence": 0.95
  }
}
```

### **Get Conversation History**

```http
GET /agent/history/user-123

Response:
{
  "session_id": "user-123",
  "history": [
    { "role": "user", "content": "What are cheap recipes?" },
    { "role": "assistant", "content": "Here are..." },
    { "role": "user", "content": "How long to cook pasta?" },
    { "role": "assistant", "content": "Pasta takes..." }
  ]
}
```

### **Clear Session**

```http
POST /agent/memory/clear

{
  "session_id": "user-123"
}
```

**Full API Docs:** Visit http://localhost:8000/docs (Swagger UI)

## ☁️ Deployment

### **Quick Deploy to Production**

**Backend (Render):**

```bash
1. Go to https://render.com
2. Connect GitHub repository
3. Create Web Service with:
   - Runtime: Python 3.12
   - Build: cd backend && pip install -r requirements.txt
   - Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
4. Set environment variables (OPENAI_API_KEY, etc.)
5. Deploy!
```

**Frontend (Vercel):**

```bash
1. Go to https://vercel.com
2. Import GitHub repository
3. Set build directory: frontend/
4. Set NEXT_PUBLIC_API_URL to your Render backend
5. Deploy!
```

See [SETUP.md](./SETUP.md) for detailed deployment guide.

## 🧪 Testing & Verification

### **Run Automated Checks**

```bash
# Verify production readiness
python verify_production_ready.py

# Expected output:
# ✅ Root Files - PASS
# ✅ Documentation - PASS
# ✅ Configuration - PASS
# ✅ Dependencies - PASS
# ✅ Code Quality - PASS
```

### **Manual Testing**

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open http://localhost:3000
4. Ask a question and verify response
5. Check browser console for errors
6. Test follow-up questions

## 👥 Team & Roles

| Member    | Role                                                |
| --------- | --------------------------------------------------- |
| **Walid** | RAG System Architecture & Multi-Agent Orchestration |
| **Fares** | AI Agent System & Intelligent Router                |
| **Ahmed** | Frontend Development & UI/UX Design                 |

## 📚 Documentation

- **[README.md](./README.md)** (this file) — Project overview and quick start
- **[PRODUCTION.md](./PRODUCTION.md)** — Complete architecture, API reference, testing strategies
- **[SETUP.md](./SETUP.md)** — Local development, Docker, cloud deployment (Render, Railway, Vercel)
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** — Pre-deployment verification and monitoring

## 🤔 FAQ

### **How is this different from ChatGPT?**

RecipaAI is grounded in _actual cookbook content_. It won't make up recipes. Every answer includes source references.

### **Can I use a different LLM?**

Yes! Edit `backend/app/config.py` to use OpenAI, Anthropic, Ollama, or any LangChain-supported model.

### **How do follow-ups work?**

The system detects contextual questions using keywords + conversation history, then automatically rewrites them with context before passing to the LLM.

### **Is conversation data saved?**

Yes, in SQLite at `backend/data/memory/agent_memory.sqlite3`. Each session has its own conversation history.

### **Can I deploy to AWS/GCP instead of Render?**

Absolutely! See [SETUP.md](./SETUP.md) for Docker setup, which works on any cloud platform.

### **How do I add a different cookbook?**

1. Place your PDF in `backend/data/source/`
2. Update `COOKBOOK_PDF` path in `backend/app/config.py`
3. Run `python -m scripts.run_ingest`
4. Restart the backend

## 📄 License

See [LICENSE](./LICENSE) file.

## 🚀 Ready to Get Started?

```bash
# 1. Clone repository
git clone https://github.com/WalidAlsafadi/Recipa-RAG-Assistant
cd Recipa-RAG-Assistant

# 2. Backend setup (see above)
cd backend && pip install -r requirements.txt && echo "OPENAI_API_KEY=sk-..." > .env

# 3. Frontend setup (see above)
cd ../frontend && npm install && echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 4. Run both
# Terminal 1: cd backend && uvicorn app.main:app --reload
# Terminal 2: cd frontend && npm run dev

# 5. Open http://localhost:3000 and start asking questions!
```

**Questions?** Check [PRODUCTION.md](./PRODUCTION.md) for architecture details or [SETUP.md](./SETUP.md) for deployment help.

**Want to contribute?** Open a GitHub issue or pull request!

**Impressed?** Star ⭐ this repository!
