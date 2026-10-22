# 🔍 Codebase Assistant — RAG-Powered Code Intelligence

> Ask questions about any GitHub repository in plain English. Get accurate answers with exact file and line references.

---

## 🧠 What is this?

Codebase Assistant is an AI-powered tool that lets you **chat with any codebase** using natural language.

Instead of manually searching through files, you simply ask:

- *"How does the crash recovery work in pgq?"*
- *"Where is JWT authentication implemented?"*
- *"Explain the rate limiting algorithm used here"*
- *"Find all places Redis is used"*
- *"What happens when a job fails?"*

The system finds the exact relevant code and gives you a precise, grounded answer — with the file name and line number so you can jump straight to it.

---

## 🎯 The Problem it Solves

Every developer has experienced this:

```
You join a new codebase
         ↓
You need to understand how something works
         ↓
You search through 50 files manually
         ↓
You read irrelevant code for 2 hours
         ↓
You finally find it — buried in a utility file
```

Codebase Assistant eliminates this. Point it at any repo, ask your question, get your answer in seconds.

---

## ✨ Features

### Core Features
- **Index any GitHub repo** — public or private (with token)
- **Natural language queries** — ask in plain English
- **Source attribution** — every answer shows exact file + line number
- **Streaming responses** — see answers as they generate
- **Multi-repo support** — index and query multiple repos simultaneously

### Search Intelligence
- **Hybrid search** — combines semantic understanding + keyword matching
- **Code-aware chunking** — preserves function and class boundaries
- **Smart retrieval** — finds relevant code even when you use different words than the code

### Developer Experience
- **Clean chat UI** — simple, fast, distraction-free
- **Code highlighting** — answers include syntax-highlighted code snippets
- **File explorer** — see which files were used to generate the answer
- **History** — conversation history within a session

---

## 🏗️ How it Works

```
                        INDEXING (one time per repo)
                        ─────────────────────────────
GitHub Repo URL
      ↓
Clone repository locally
      ↓
Parse all code files (.py, .js, .ts, .go, .java, .cpp, .sql, .md)
      ↓
Smart chunking (preserve functions, classes, methods)
      ↓
Embed each chunk using Voyage AI
      ↓
Store chunk + embedding + metadata in pgvector
      ↓
Build BM25 keyword index in memory
      ↓
Ready to query ✅


                        QUERYING (every user question)
                        ──────────────────────────────
User asks: "How does crash recovery work?"
      ↓
Convert question to embedding (Voyage AI)
      ↓
Dense search  → find semantically similar code chunks
Sparse search → find keyword-matching code chunks
      ↓
Combine results using Reciprocal Rank Fusion (RRF)
      ↓
Send top 5 chunks + question to Claude API
      ↓
Claude generates answer grounded in actual code
      ↓
Return answer + source files + line numbers
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | FastAPI + Python | Async, fast, you already know it |
| **Database** | PostgreSQL + pgvector | Vector search without a separate DB |
| **Embeddings** | Voyage AI (voyage-code-3) | Best for code, Anthropic recommended |
| **LLM** | Claude API (claude-sonnet) | Best reasoning, source grounding |
| **Keyword Search** | BM25 (rank-bm25) | Exact keyword matching |
| **Code Parsing** | Tree-sitter | Parse code respecting structure |
| **Repo Cloning** | GitPython | Clone any GitHub repo |
| **Frontend** | React + Tailwind CSS | Clean chat UI |
| **Containerization** | Docker + Docker Compose | Easy setup |

---

## 📁 Project Structure

```
codebase-assistant/
│
├── backend/
│   ├── main.py                     ← FastAPI app entry point
│   ├── config.py                   ← Environment variables
│   ├── requirements.txt
│   │
│   ├── indexer/                    ← Indexing pipeline
│   │   ├── __init__.py
│   │   ├── cloner.py               ← Clone GitHub repos
│   │   ├── parser.py               ← Parse code files by language
│   │   ├── chunker.py              ← Smart code chunking
│   │   └── embedder.py             ← Embed + store in pgvector
│   │
│   ├── retriever/                  ← Search pipeline
│   │   ├── __init__.py
│   │   ├── dense.py                ← Vector similarity search
│   │   ├── sparse.py               ← BM25 keyword search
│   │   └── hybrid.py               ← RRF combination
│   │
│   ├── generator/                  ← Answer generation
│   │   ├── __init__.py
│   │   ├── prompt.py               ← Prompt construction
│   │   └── answer.py               ← Claude API integration
│   │
│   ├── api/                        ← FastAPI routes
│   │   ├── __init__.py
│   │   ├── index.py                ← POST /api/index
│   │   └── query.py                ← POST /api/query
│   │
│   ├── db/                         ← Database layer
│   │   ├── __init__.py
│   │   └── setup.py                ← pgvector setup + migrations
│   │
│   └── evaluator/                  ← RAG evaluation
│       ├── __init__.py
│       └── metrics.py              ← Faithfulness, relevance scores
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Chat.tsx            ← Main chat interface
│   │   │   ├── Message.tsx         ← Individual message bubble
│   │   │   ├── RepoInput.tsx       ← GitHub URL input + index button
│   │   │   ├── SourceCard.tsx      ← File + line reference card
│   │   │   └── CodeBlock.tsx       ← Syntax highlighted code
│   │   ├── hooks/
│   │   │   └── useChat.ts          ← Chat state management
│   │   └── services/
│   │       └── api.ts              ← Backend API calls
│   ├── package.json
│   └── tailwind.config.js
│
├── docker-compose.yml              ← PostgreSQL + pgvector + app
├── .env.example                    ← Environment variables template
└── README.md
```

---

## 🗄️ Database Schema

```sql
-- Indexed repositories
CREATE TABLE repositories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    indexed_at  TIMESTAMPTZ DEFAULT NOW(),
    chunk_count INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'indexing'  -- indexing, ready, failed
);

-- Code chunks with embeddings
CREATE TABLE code_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id     UUID REFERENCES repositories(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,
    language    TEXT,
    content     TEXT NOT NULL,
    start_line  INTEGER,
    end_line    INTEGER,
    chunk_type  TEXT,  -- function, class, module, block
    chunk_name  TEXT,  -- function name, class name if applicable
    embedding   vector(1024),  -- voyage-code-3 dimensions
    indexed_at  TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX ON code_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full text search index
CREATE INDEX ON code_chunks USING gin(to_tsvector('english', content));

-- Query history
CREATE TABLE query_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id     UUID REFERENCES repositories(id),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    sources     JSONB,
    latency_ms  INTEGER,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🔌 API Endpoints

### Index a Repository
```http
POST /api/index
Content-Type: application/json

{
  "url": "https://github.com/manassingh9220/pgq",
  "github_token": "optional_for_private_repos"
}

Response:
{
  "repo_id": "uuid",
  "name": "pgq",
  "status": "indexing",
  "message": "Indexing started. Poll /api/repos/{repo_id} for status."
}
```

### Query a Repository
```http
POST /api/query
Content-Type: application/json

{
  "repo_id": "uuid",
  "question": "How does crash recovery work?",
  "stream": true
}

Response (streaming):
{
  "answer": "Crash recovery in pgq works through...",
  "sources": [
    {
      "file": "pgq/worker.py",
      "start_line": 42,
      "end_line": 67,
      "chunk_type": "function",
      "chunk_name": "claim_job",
      "snippet": "def claim_job(self):\n    ..."
    }
  ],
  "latency_ms": 187
}
```

### Get Repository Status
```http
GET /api/repos/{repo_id}

Response:
{
  "id": "uuid",
  "name": "pgq",
  "url": "https://github.com/...",
  "status": "ready",
  "chunk_count": 234,
  "indexed_at": "2025-01-01T00:00:00Z"
}
```

### List Indexed Repositories
```http
GET /api/repos

Response:
{
  "repos": [
    { "id": "...", "name": "pgq", "status": "ready", "chunk_count": 234 },
    { "id": "...", "name": "ratelimiter", "status": "ready", "chunk_count": 187 }
  ]
}
```

---

## 🧩 Core Concepts Used

### 1. Code-Aware Chunking
Unlike plain text, code has structure — functions, classes, methods. Splitting in the middle of a function loses context.

```
❌ Fixed size chunking:
  def calculate_payment(order):
      total = order.subtotal +
  # SPLIT HERE — loses rest of function

✅ Code-aware chunking:
  Chunk 1: entire calculate_payment function
  Chunk 2: entire process_refund function
```

### 2. Hybrid Search (Dense + Sparse)
```
Query: "SELECT FOR UPDATE SKIP LOCKED"

Dense search finds:    "job claiming with locking mechanism" (semantic)
Sparse search finds:   exact "SELECT FOR UPDATE SKIP LOCKED" (keyword)

Combined → best of both worlds
```

### 3. Source Attribution
Every answer is grounded — the system only answers from actual code:
```
Answer: "Crash recovery uses lease-based timeouts..."
Source: worker.py, lines 42-67, function: claim_job
```

### 4. Reciprocal Rank Fusion (RRF)
Combines dense and sparse results intelligently without manual weight tuning.

---

## 🗺️ Roadmap

### ✅ Phase 1 — Core Pipeline (Week 1)
- [ ] Project setup + Docker Compose
- [ ] PostgreSQL + pgvector setup
- [ ] GitHub repo cloning (GitPython)
- [ ] File parsing by language
- [ ] Basic fixed-size chunking
- [ ] Voyage AI embedding integration
- [ ] Store chunks in pgvector
- [ ] Basic dense vector search
- [ ] FastAPI endpoints (index + query)
- [ ] Basic Claude integration

### 🔄 Phase 2 — Intelligence (Week 2)
- [ ] Tree-sitter code-aware chunking
- [ ] BM25 sparse search
- [ ] Hybrid search with RRF
- [ ] Streaming responses
- [ ] Source attribution (file + line)
- [ ] Multi-repo support
- [ ] Repo indexing status tracking

### 🎨 Phase 3 — Frontend (Week 2-3)
- [ ] React chat interface
- [ ] GitHub URL input + index button
- [ ] Streaming message display
- [ ] Source file cards
- [ ] Syntax highlighted code blocks
- [ ] Repo selector
- [ ] Indexing progress indicator

### 📊 Phase 4 — Quality & Polish (Week 3)
- [ ] RAGAS evaluation pipeline
- [ ] Benchmark on your own repos (pgq, ratelimiter)
- [ ] Performance optimization
- [ ] Error handling + retries
- [ ] README with benchmark results
- [ ] Deploy (Railway or Render)
- [ ] Record demo video

### 🚀 Phase 5 — Extras (if time allows)
- [ ] Private repo support (GitHub token)
- [ ] File type filtering
- [ ] Conversation history
- [ ] Answer quality feedback (thumbs up/down)
- [ ] Export conversation as markdown

---

## ⚙️ Setup

### Prerequisites
```
Python 3.11+
Node.js 18+
Docker + Docker Compose
PostgreSQL 16 (via Docker)
```

### Environment Variables
```env
# .env
CODEBASE_DB_URL=postgresql://user:pass@localhost:5433/codebase_assistant
ANTHROPIC_API_KEY=your_anthropic_key
VOYAGE_API_KEY=your_voyage_key
GITHUB_TOKEN=optional_for_private_repos
```

### Run Locally
```bash
# Clone this repo
git clone https://github.com/manassingh9220/codebase-assistant
cd codebase-assistant

# Start PostgreSQL with pgvector
docker-compose up -d db

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📈 Performance Targets

| Metric | Target |
|---|---|
| Indexing speed | < 2 min for 10K lines |
| Query latency | < 500ms end-to-end |
| Retrieval accuracy | > 85% (RAGAS) |
| Faithfulness | > 90% |
| Answer relevance | > 85% |

---

## 🔑 Get API Keys

| Service | Link | Free Tier |
|---|---|---|
| Anthropic (Claude) | console.anthropic.com | $5 free credits |
| Voyage AI | dash.voyageai.com | 50M free tokens |

---

## 👤 Author

**Manas Singh** — Software Engineer at Avathon
- GitHub: [github.com/manassingh9220](https://github.com/manassingh9220)
- LinkedIn: [linkedin.com/in/manassingh21](https://linkedin.com/in/manassingh21)

---

> Built to demonstrate RAG, hybrid search, and vector databases using a real engineering problem.
> Every concept used here is production-grade and interview-ready.