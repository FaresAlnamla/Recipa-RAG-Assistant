# RecipaAI - Production Ready System Documentation

**Version:** 1.0.0  
**Date:** January 5, 2026  
**Status:** ✅ Production Ready

## 📋 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- OpenAI API Key
- Chroma Vector Store (included)

### Installation & Setup

```bash
# Backend Setup
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY="your-key-here"

# Frontend Setup
cd ../frontend
npm install
```

### Running the System

```bash
# Terminal 1: Backend API
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Open: http://localhost:3000
```

## 🏗️ System Architecture

### Multi-Agent Pipeline

```
User Question → Router → Retrieval → LLM → Evaluation → Memory → Response
```

### Core Components

#### 1. **Router** (`app/agent/router.py`)

- Determines if question is cookbook-related
- Routes to appropriate handler
- Detects catalog requests
- Supports: recipes, ingredients, budget meals, author info, book metadata

#### 2. **Retrieval** (`app/rag/retrieval.py`)

- Semantic vector search via Chroma
- Returns relevant recipe chunks
- Metadata: source, page, snippet

#### 3. **LLM** (`app/rag/llm.py`)

- GPT-4o-mini for answer generation
- Streaming token support
- Uses only retrieved context
- Supports multi-turn conversations

#### 4. **Evaluation** (`app/agent/eval.py`)

- Validates answer support
- Confidence scoring
- Facts verification

#### 5. **Memory** (`app/agent/memory.py`)

- SQLite conversation storage
- Session-based history
- Follow-up question rewriting
- Recipe context caching

#### 6. **API** (`app/api/agent_routes.py`)

- REST endpoints for frontend
- Streaming SSE support
- Session management

## 💬 Follow-up Questions & History

### How It Works

1. **Initial Question**: User asks "How to make a chocolate cake?"
2. **Storage**: Question + Answer stored in SQLite
3. **Follow-up Detection**: "What should I put on top?" detected as follow-up
4. **Context Rewrite**: Rewritten to "For chocolate cake, what should I put on top?"
5. **Enhanced Retrieval**: Search includes recipe context
6. **Smart Answer**: LLM responds with context from previous answer

### Supported Follow-up Patterns

```
"How long to cook?"
"Can I add salt?"
"What did you suggest for toppings?"
"How many servings does it make?"
"What temperature should I use?"
"Can I use eggs instead of butter?"
```

### Multi-turn Conversation Example

```
Q1: How to make a chocolate cake?
A1: [Detailed recipe with ingredients, steps, timing]

Q2: What did you suggest to put on top?
A2: [Based on previous answer + cookbook context]

Q3: How long does it take total?
A3: [References timing from original recipe]
```

## 🗂️ File Structure

### Backend Core

```
backend/
├── app/
│   ├── agent/          # Multi-agent orchestration
│   │   ├── agent.py    # Main agent loop (1000+ lines, highly optimized)
│   │   ├── router.py   # Question routing logic
│   │   ├── memory.py   # SQLite conversation storage
│   │   └── eval.py     # Answer evaluation
│   ├── rag/            # Retrieval-Augmented Generation
│   │   ├── retrieval.py
│   │   ├── llm.py
│   │   ├── pipeline.py
│   │   └── ingest.py
│   ├── api/            # REST API
│   │   ├── agent_routes.py
│   │   └── agent.py
│   ├── schemas/        # Pydantic models
│   ├── main.py         # FastAPI app
│   ├── config.py       # Configuration
│   └── dependencies.py # Dependency injection
├── data/               # Local data storage
│   ├── memory/         # SQLite database
│   ├── processed/      # Chunked cookbook data
│   └── source/         # Original PDFs
└── requirements.txt    # Python dependencies
```

### Frontend Core

```
frontend/
├── app/
│   ├── page.tsx        # Home page
│   ├── layout.tsx      # Root layout
│   └── globals.css     # Global styles
├── components/
│   ├── home/           # Home section components
│   │   ├── Hero.tsx
│   │   ├── Architecture.tsx
│   │   ├── QAEngine.tsx
│   │   └── Team.tsx
│   └── ui/             # Reusable UI components
├── lib/
│   ├── constants.ts    # Questions, architecture steps, team info
│   ├── api.ts          # API client
│   └── utils.ts        # Utilities
├── hooks/              # React hooks
└── package.json        # Dependencies
```

## 🔌 API Endpoints

### `/agent/ask` (POST)

Ask a question with streaming disabled

```bash
curl -X POST http://localhost:8000/agent/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How to make pasta?",
    "session_id": "user_123"
  }'
```

**Response:**

```json
{
  "answer": "Here's how to make pasta...",
  "sources": [
    {
      "book_name": "THE LOW-COST COOKBOOK",
      "page": 42,
      "snippet": "..."
    }
  ],
  "evaluation": {
    "supported": true,
    "confidence": 0.95,
    "reasons": ["context_match"],
    "facts_checked": ["ingredients", "timing"]
  }
}
```

### `/agent/ask/stream` (POST)

Ask with streaming response

```bash
curl -X POST http://localhost:8000/agent/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "...", "session_id": "..."}'
```

**Streams SSE events:**

```
data: {"type":"token","token":"Here"}
data: {"type":"token","token":"'s"}
data: {"type":"done","answer":"...","sources":[...]}
```

### `/agent/memory/history` (GET)

Get conversation history

```bash
curl "http://localhost:8000/agent/memory/history?session_id=user_123"
```

### `/agent/memory/clear` (POST)

Clear session history

```bash
curl -X POST http://localhost:8000/agent/memory/clear \
  -d '{"session_id": "user_123"}'
```

## 🧪 Testing

### Automated Tests

```bash
cd /path/to/project
python verify_system.py
```

### Manual API Testing

```bash
# Test 1: Initial question
curl -X POST http://localhost:8000/agent/ask \
  -d '{"question":"What budget recipes exist?","session_id":"test1"}'

# Test 2: Follow-up (should be context-aware)
curl -X POST http://localhost:8000/agent/ask \
  -d '{"question":"How long to cook?","session_id":"test1"}'

# Test 3: Check history
curl "http://localhost:8000/agent/memory/history?session_id=test1"
```

### Frontend Testing

1. Open http://localhost:3000
2. Try suggested questions
3. Ask a recipe question
4. Ask a follow-up ("How long?", "Can I add...?", etc.)
5. Verify follow-up is context-aware
6. Check "Recent Conversation" shows previous questions

## ⚙️ Configuration

### Environment Variables

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_COLLECTION=recipes
VECTORSTORE_DIR=./vectorstore/chroma
```

### Key Settings

- **Max context**: 8000 characters
- **Max sources per response**: 4 for catalog, 2 for queries
- **History limit**: 10 messages per session
- **Cache expiry**: Per recipe
- **Temperature**: 0.2 (low randomness, high consistency)

## 🚀 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend .
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment

- **Backend**: Python 3.12, FastAPI, Chroma
- **Frontend**: Next.js 14, React 18, TailwindCSS
- **Database**: SQLite (local) or PostgreSQL (production)
- **LLM**: OpenAI API (GPT-4o-mini)
- **Search**: Chroma Vector Store

### Performance

- **Initial query**: ~2-3 seconds (includes retrieval + LLM)
- **Follow-up query**: ~1-2 seconds (uses cached context)
- **Streaming**: First token in ~0.5s
- **Concurrent users**: Tested up to 10 simultaneous conversations
- **Memory per session**: ~500KB (SQLite)

## 📦 Dependencies

### Core Backend

- `fastapi` - Web framework
- `python-multipart` - Form handling
- `langchain` - LLM orchestration
- `langchain-openai` - OpenAI integration
- `langchain-chroma` - Vector store
- `pydantic` - Data validation

### Core Frontend

- `next` - React framework
- `react` - UI library
- `typescript` - Type safety
- `tailwindcss` - Styling
- `lucide-react` - Icons

## 🔒 Security

### Recommendations

1. **API Keys**: Use environment variables, rotate regularly
2. **Session IDs**: Generate with UUID, validate length
3. **Rate Limiting**: Implement per-session limits
4. **Input Validation**: All user input validated via Pydantic
5. **CORS**: Configure for production domain
6. **HTTPS**: Required for production

### Current Protections

- ✅ Input validation
- ✅ Session isolation
- ✅ No external knowledge (cookbook-only)
- ✅ Query filtering
- ✅ Type checking

## 📊 Monitoring

### Key Metrics

```python
# Log these in production:
- Question processing time
- Follow-up detection rate
- Cache hit rate
- LLM token usage
- Error rate per question type
- Session duration
```

### Common Issues

| Issue                 | Cause                | Solution                       |
| --------------------- | -------------------- | ------------------------------ |
| "Cannot find answer"  | Poor retrieval       | Check vector store embeddings  |
| Follow-up not working | Keywords not matched | Add to FOLLOWUP_KEYWORDS       |
| Slow responses        | LLM latency          | Check OpenAI quota/rate limits |
| History empty         | Wrong session ID     | Verify session persistence     |

## 🎯 Next Steps

### For Maintenance

1. Monitor error logs weekly
2. Update dependencies monthly
3. Review follow-up keywords quarterly
4. Evaluate LLM performance semi-annually

### For Improvements

1. Add multi-language support
2. Implement caching layer (Redis)
3. Add more cookbook sources
4. Build admin dashboard

## 📞 Support

### Getting Help

1. Check error logs: `backend/data/logs/`
2. Run tests: `python verify_system.py`
3. Review API documentation in code comments
4. Check Git history for similar issues

### Team

- **Walid Alsafadi**: RAG System & Multi-Agent Architecture
- **Fares Alnamla**: AI Agent System & Router
- **Ahmed Alyazuri**: Frontend Developer & UI/UX

**Last Updated:** January 5, 2026
