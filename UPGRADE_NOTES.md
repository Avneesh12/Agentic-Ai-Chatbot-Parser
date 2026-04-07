# Upgrade Notes — Real-World Agentic Chatbot

## What changed and why

### 1. Multi-file Upload API (`app/routes/upload.py`)

**Before:** Single file, no auth, no user isolation, bare `UploadFile = File(...)`.

**After:**
- Accepts **1–20 files per request** via `List[UploadFile]`
- **User-scoped storage** — files saved to `uploads/<user_id>/` so filenames never collide across users
- **Per-file validation** — type check (pdf/docx/txt/csv/xlsx/md) + 20 MB size guard per file
- **Unique filename** on disk (`stem_<8hex>.<ext>`) to prevent overwrites
- **Per-file status report** in response — client knows exactly which files succeeded/failed
- Passes `user_id` and `original_filename` into `ingest_file()` for metadata tracking

```http
POST /api/upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data

files=@report.pdf
files=@policy.docx
files=@data.csv
```

---

### 2. RAG Ingestion (`app/rag/ingest.py`)

**Before:** Fixed 500-char chunks, no overlap, no metadata, only PDF/DOCX/TXT.

**After:**
- **Sliding window chunking** with configurable `CHUNK_SIZE=512` and `CHUNK_OVERLAP=64`
  — sentences at chunk boundaries are never silently dropped
- **New file types**: CSV and XLSX now load properly via pandas, MD via plain text
- **Rich Qdrant payload** per point:
  ```json
  {
    "text": "...",
    "user_id": 42,
    "filename": "policy.pdf",
    "file_type": "pdf",
    "chunk_index": 3,
    "total_chunks": 18
  }
  ```

---

### 3. Per-User RAG Retrieval (`app/rag/nodes.py`, `app/rag/state.py`)

**Before:** All users shared the same Qdrant query — one user could get answers from another user's documents.

**After:**
- `retrieve()` builds a Qdrant `Filter` on `user_id` when present
- `source_files` returned in state so answers can cite which document was used
- Top-k raised from 3 → 5 for richer context
- `RAGState` extended with `user_id: Optional[int]` and `source_files: List[str]`
- WebSocket handler passes `int(user_id)` into every `rag_graph.astream()` call

---

### 4. Real-World MCP Tools (`app/mcp/tools/real_world.py`)

**Before:** All tools called `dummyjson.com`, `randomuser.me`, `fakestoreapi.com`, `jsonplaceholder.typicode.com` — fake data with zero business value.

**After — 10 production-grade tools:**

| Tool | API used | Key needed? |
|---|---|---|
| `get_weather` | wttr.in | ❌ Free |
| `get_exchange_rate` | Frankfurter (ECB) | ❌ Free |
| `search_wikipedia` | Wikipedia REST | ❌ Free |
| `get_news_headlines` | NewsAPI.org | ✅ `NEWS_API_KEY` |
| `get_time` | worldtimeapi.io | ❌ Free |
| `ip_lookup` | ip-api.com | ❌ Free |
| `get_github_repo` | GitHub API | ❌ 60 req/hr |
| `get_crypto_price` | CoinGecko | ❌ Free |
| `calculate_expression` | local eval (no API) | ❌ None |
| `unit_convert` | local logic (no API) | ❌ None |

All tools are registered with `@mcp.tool()` so they are exposed over the MCP protocol AND available to the agent router.

---

### 5. Agent System Prompt (`app/agent/prompt.py`)

**Before:** Hardcoded triggers for dummy tools; no real-world context.

**After:**
- Updated triggers for all 10 real tools
- Clear decision hierarchy: TOOL → RAG → LLM
- Strict JSON-only output rules
- Examples for every tool and every mode
- Wikipedia routed via tool (not hallucination), crypto/weather/forex all properly handled

---

### 6. MCP Server (`app/mcp/server.py`)

**Before:** Tool imports incomplete; `mcp` instance created but tools not guaranteed registered.

**After:**
- Explicit `import app.mcp.tools.real_world` ensures all `@mcp.tool()` decorators fire at startup
- Log line shows exactly how many tools were registered

---

## .env additions required

```env
NEWS_API_KEY=your_key_from_newsapi_org   # optional, only for news headlines
```

All other new tools are fully free with no API key.

---

## File map

```
app/
  routes/
    upload.py          ← multi-file, user-scoped, per-file status
  rag/
    ingest.py          ← sliding-window chunks, CSV/XLSX/MD support, metadata
    nodes.py           ← user_id filter on Qdrant, source_files in answer
    state.py           ← user_id + source_files added to RAGState
  mcp/
    server.py          ← proper tool registration at startup
    tools/
      real_world.py    ← 10 production tools (weather, fx, wiki, news, …)
      registry.py      ← updated TOOLS dict pointing to real_world.py
      external_api.py  ← deprecated (emptied)
  agent/
    prompt.py          ← updated system prompt for real tools
  websocket/
    chat_ws.py         ← passes user_id into every rag_graph.astream() call
```
