# Agentic RecipaAI — Execution Plan

## 1. Project Overview
RecipaAI is a production-style RAG-powered recipe assistant.  
This project extends RecipaAI into an **Agentic AI Application** using:
- CrewAI for multi-agent reasoning
- MCP Server for tool abstraction
- Existing FastAPI + Next.js stack

Priority: **portfolio & recruiter value**  
Constraint: **8 days**, team of **3 AI students**

---

## 2. Final Architecture

Next.js Frontend  
↓  
FastAPI Agent Gateway (`/agent/run`)  
↓  
CrewAI (Planner → Retriever → Writer)  
↓  
MCP Server (`recipe_rag_query`)  
↓  
Existing RAG (ChromaDB + Cookbook PDFs)

**Rule:** Existing RAG code is reused and wrapped, not rewritten.

---

## 3. Team Roles (Locked)

### Member 1 — Retrieval, MCP, Performance
**Primary focus:** RAG quality, speed, and tooling

Main folders:
- backend/app/rag/
- backend/app/mcp/

Responsibilities:
- Wrap RAG as MCP tool
- Improve retrieval latency
- Ensure citation correctness
- Warm-load vectorstore
- Cache embeddings

Deliverables:
- MCP server
- `recipe_rag_query` tool
- Latency logs

---

### Member 2 — Agent Architecture (CrewAI)
**Primary focus:** agent reasoning and orchestration

Main folders:
- backend/app/agent/
- backend/app/api/

Responsibilities:
- Design agent roles
- Implement CrewAI workflow
- Planning → tool use → synthesis
- Enforce guardrails (no hallucination, citations required)

Deliverables:
- CrewAI agents
- `/agent/run` API with streaming
- Structured planning output

---

### Member 3 — Frontend & AI Transparency
**Primary focus:** UX, explainability, demo quality

Main folders:
- frontend/app/
- frontend/components/

Responsibilities:
- Streaming UI for agent steps
- Plan / Tool / Sources / Answer panels
- Citations display
- Demo polish

Deliverables:
- Transparent agent UI
- Smooth streaming UX
- Video-ready demo

---

## 4. Agent Design

### Planner Agent
- Understands user intent
- Outputs structured JSON plan
- Decides constraints and steps

### Retriever Agent
- Calls MCP tool only
- Retrieves evidence
- Never answers user directly

### Writer Agent
- Synthesizes final response
- Uses citations only
- States clearly if info is not found

---

## 5. MCP Tooling

Tool name:
`recipe_rag_query`

Purpose:
- Abstract retrieval logic
- Return evidence + citations
- Enable agent tool usage

---

## 6. Performance Scope (RAG)

Target:
- Initial latency: 10–15s (acceptable)
- Improved latency: ~6–8s (goal)

Allowed optimizations:
- Vectorstore warm-load
- Embedding cache
- Top-k tuning
- Early streaming

No over-optimization required.

---

## 7. Timeline (8 Days)

Day 1: Freeze contracts, create folders  
Day 2: MCP tool + mock agents  
Day 3: Real agents + real retrieval  
Day 4: Performance + guardrails  
Day 5: Documentation + diagram  
Day 6: Transparency features  
Day 7: Demo video  
Day 8: Submission packaging

---

## 8. Blocking Rules

- No one edits another member’s folder
- All interfaces defined in `CONTRACTS.md`
- Mocks allowed until integration
- Daily 10-minute sync

---

## 9. Success Criteria

- Multi-agent reasoning visible
- MCP tool clearly integrated
- Citations shown in UI
- Clean architecture
- Strong recruiter narrative
