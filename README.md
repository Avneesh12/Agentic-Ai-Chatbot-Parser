# 🤖 AI Chat API

A production-grade **Agentic AI Chat Backend** built with **FastAPI**, featuring intelligent multi-mode query routing, RAG-based document Q&A, real-time WebSocket streaming, JWT authentication (including Google OAuth), Redis caching, and MCP tool integrations.

---

## ✨ Features

- **Agentic Routing** — LLM autonomously decides between Tool call, RAG search, or direct LLM answer
- **RAG Pipeline** — Upload documents (PDF, DOCX, TXT), embed them into Qdrant vector DB, and query with semantic search via LangGraph
- **Real-time WebSocket Streaming** — Token-by-token streamed responses over WebSocket
- **Hallucination Guard** — Detects and filters hallucinated answers before sending to client
- **JWT Auth** — Register/Login with email+password or Google OAuth
- **Redis Caching** — Chat history, agent answers, and tool results cached with configurable TTLs
- **MCP Tools** — 10 built-in tools (health check, posts, users, products, carts, categories, etc.)
- **PostgreSQL + Alembic** — Async SQLAlchemy with full migration support
- **Docker Compose** — Redis and Qdrant services pre-configured

---

## 🏗️ Project Structure

```
app/
├── main.py                  # FastAPI app entry point, startup/shutdown events
│
├── agent/
│   ├── main_agent.py        # Core agent — parses LLM decision, routes to tool/RAG/LLM
│   ├── prompt.py            # System prompt with routing rules and tool definitions
│   └── grok_agent.py        # Groq-specific agent variant
│
├── core/
│   ├── config.py            # All settings loaded from .env
│   ├── security.py          # JWT creation, decoding, password hashing (bcrypt)
│   ├── cache.py             # Redis async cache helpers (get, set, delete pattern)
│   └── deps.py              # FastAPI dependency: get_current_user
│
├── db/
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── deps.py              # FastAPI dependency: get_db
│   └── init_db.py           # Creates all tables on startup
│
├── models/
│   ├── user.py              # User SQLAlchemy model (email, password, google_id, avatar)
│   └── chat.py              # Chat history model (user, question, answer, source)
│
├── schemas/
│   └── auth.py              # Pydantic schemas: Register, Login, Token, GoogleAuth
│
├── routes/
│   ├── auth.py              # /api/auth — register, login, google, logout, me
│   ├── chat.py              # /api/chat — REST chat endpoint
│   ├── upload.py            # /api/upload — file upload + RAG ingestion
│   └── document.py          # /api/documents — document management
│
├── websocket/
│   └── chat_ws.py           # WebSocket /ws/chat/ — streaming agent responses
│
├── rag/
│   ├── graph.py             # LangGraph graph: retrieve → decide → rag/llm
│   ├── nodes.py             # Graph nodes: retrieve, decide, rag, llm
│   ├── state.py             # GraphState TypedDict definition
│   ├── ingest.py            # File loader + chunker + Qdrant upserter
│   ├── embedding.py         # Sentence-transformer embedding
│   └── qdrant_store.py      # Qdrant client + collection initialisation
│
├── llm/
│   └── grok.py              # Groq LLM client wrapper
│
├── services/
│   ├── llm_service.py       # LLMService.generate_response() — calls LLM API
│   ├── memory.py            # Chat memory helpers
│   ├── document_parser.py   # Extracts text from PDF/DOCX/TXT
│   └── ocr_service.py       # OCR via pytesseract + pdf2image
│
├── mcp/
│   ├── server.py            # MCP server startup
│   ├── instance.py          # MCP server singleton
│   ├── config.py            # MCP configuration
│   └── tools/
│       ├── registry.py      # TOOLS dict — maps tool names to functions
│       ├── health.py        # health_check tool
│       └── external_api.py  # 9 external API tools (posts, users, products, etc.)
│
└── utils/
    └── logger.py            # Centralised logger

alembic/                     # Database migrations
Dockerfile                   # App container
docker-compose.yml           # Redis + Qdrant services
pyproject.toml               # Dependencies (uv)
```

---

## 🧠 How the Agent Works

Every WebSocket message goes through this pipeline:

```
User Message
     │
     ▼
 run_agent()  ←── LLM reads SYSTEM_PROMPT and returns JSON decision
     │
     ├── mode: "tool"  ──► Executes MCP tool, returns structured result
     │
     ├── mode: "rag"   ──► LangGraph pipeline:
     │                        retrieve (Qdrant) → decide → rag node (streams answer)
     │
     └── mode: "llm"   ──► Direct LLM response (greetings, math, casual chat)
     
     ▼
Hallucination Guard  ──► Filters suspicious answers
     │
     ▼
Redis Cache  ──► Caches answer for identical future queries
     │
     ▼
PostgreSQL  ──► Saves chat to DB, invalidates history cache
     │
     ▼
WebSocket  ──► Streams final answer to client token by token
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Language | Python 3.11 |
| LLM | Groq (LLaMA / Gemma via OpenRouter) |
| Agent Orchestration | LangGraph |
| Vector Database | Qdrant |
| Embeddings | sentence-transformers |
| Database | PostgreSQL + asyncpg |
| ORM | SQLAlchemy (async) + Alembic |
| Cache | Redis (async) |
| Auth | JWT (python-jose) + Google OAuth |
| Tool Protocol | MCP (Model Context Protocol) |
| OCR | pytesseract + pdf2image |
| Containerisation | Docker + Docker Compose |

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
# App
APP_NAME=AI Chat API
DEBUG=False

# LLM
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
MODEL=google/gemma-7b-it:free

# Hugging Face (for embeddings)
HF_API_KEY=your_hf_api_key

# Database
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aichat

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redis
REDIS_URL=redis://localhost:6379

# JWT
SECRET_KEY=your-super-secret-key-change-this

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
```

---

## 🚀 Getting Started

### 1. Start Infrastructure (Redis + Qdrant)

```bash
docker-compose up -d
```

### 2. Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register with email + password |
| POST | `/api/auth/login` | Login, returns JWT token |
| POST | `/api/auth/google` | Login/register via Google OAuth |
| POST | `/api/auth/logout` | Logout (client deletes token) |
| GET | `/api/auth/me` | Get current user profile |

### Chat & Upload
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | REST chat endpoint |
| POST | `/api/upload` | Upload PDF/DOCX/TXT for RAG indexing |
| WS | `/ws/chat/?token=<jwt>` | WebSocket streaming chat |

---

## 🔌 WebSocket Usage

Connect with a valid JWT token:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat/?token=YOUR_JWT");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "status")  console.log("Status:", data.message);
  if (data.type === "stream")  process.stdout.write(data.chunk);   // streaming token
  if (data.type === "done")    console.log("\nSource:", data.source);
};

ws.send("tell me about hostbooks");
```

### WebSocket Message Types

| Type | Description |
|---|---|
| `status` | `"processing"` — agent started |
| `stream` | Incremental answer chunk |
| `done` | Final message with `source`, `tool`, `tool_result` |

---

## 🧰 MCP Tools

The agent has access to 10 built-in tools:

| Tool | Trigger Example |
|---|---|
| `health_check` | "is the server up?" |
| `get_posts` | "show all posts" |
| `get_post` | "get post 3" |
| `get_users` | "list all users" |
| `get_products` | "show products" |
| `search_products` | "search for laptop" |
| `get_carts` | "show all carts" |
| `get_store_products` | "show store items" |
| `get_categories` | "what categories exist?" |
| `get_random_users` | "give me 5 random users" |

---

## 📄 Document Upload & RAG

1. Upload a file via `POST /api/upload` (PDF, DOCX, or TXT)
2. The file is chunked into 500-character segments
3. Each chunk is embedded using `sentence-transformers` (384-dim vectors)
4. Vectors are stored in Qdrant under the `documents` collection
5. On chat, the agent routes document-related queries to the RAG pipeline
6. LangGraph retrieves top-k chunks and generates a grounded answer

---

## 🔐 Authentication Flow

```
Register/Login  ──►  JWT Token (7-day expiry)
                           │
                    WebSocket connect
                    ?token=<JWT>
                           │
                    Token decoded → user_id
                           │
                    User fetched from DB
                           │
                    Connection accepted ✅
```

Google OAuth verifies the `id_token` against Google's tokeninfo endpoint, then creates or links the user account automatically.

---

## 🗄️ Redis Cache Keys & TTLs

| Cache Key | TTL | Purpose |
|---|---|---|
| `chat_history:<user_hash>` | 5 min | Last 5 messages per user |
| `agent_answer:<user>:<msg_hash>` | 1 hour | Cached agent responses |
| `tool_result:<tool>:<input_hash>` | 2 min | Tool execution results |
| `user:<id>` | 15 min | User profile data |

---

## 🐳 Docker

Build and run the full app:

```bash
# Start infrastructure
docker-compose up -d

# Build app image
docker build -t ai-chat-api .

# Run app
docker run --env-file .env -p 8000:8000 ai-chat-api
```

---

## 📋 Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Qdrant (via Docker)
- Tesseract OCR (`apt install tesseract-ocr` on Linux)

---

## 👤 Author

**Avneesh Kumar**  
Python Developer | FastAPI · LangGraph · RAG · WebSockets  
📧 avneeshkumar.work@gmail.com  
🔗 [github.com/Avneesh12](https://github.com/Avneesh12)  
🔗 [linkedin.com/in/avneesh-kumar-verma-1a33501b9](https://www.linkedin.com/in/avneesh-kumar-verma-1a33501b9/)