# Fitness & Sports Nutrition RAG Assistant

This project is a production-style backend for a fitness assistant powered by RAG:
- Offline indexing (`Vector + BM25`)
- Query understanding (`context compression + rewrite + decomposition`)
- Adaptive retrieval (`intent-based dynamic strategy`)
- Self-RAG post-processing (`evidence check + optional second pass + semantic rerank`)
- Final response generation (`structured answer + citation traceability`)

## 1) Environment Setup

```powershell
cd "F:\codex learning\backend"
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Update `.env`:
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (OpenAI-compatible endpoint; Qwen-compatible endpoints are supported)
- `EMBEDDING_MODEL`
- `CHAT_MODEL`
- `TRUST_ENV_PROXY=false` (recommended if your proxy causes SSL errors)

## 2) Build Offline Index

```powershell
.\.venv\Scripts\python.exe scripts/build_index.py --data-dir ./data/raw --recreate
```

Expected:
- `status=ok`
- `indexed_count > 0`
- `bm25_count > 0`

## 3) Start API Service

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Main endpoints:
- `GET /health`
- `GET /index/status`
- `POST /retrieve/debug`
- `POST /chat/preprocess`
- `POST /chat/query`

## 4) Frontend Demo UI

Start backend API first:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then start frontend static site:

```powershell
.\.venv\Scripts\python.exe scripts/run_frontend.py
```

Open:
- `http://127.0.0.1:5500`

The page calls `/chat/query` and shows:
- generated plan
- confidence
- citation cards

## 5) Manual API Testing

### 4.1 Preprocess
```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/chat/preprocess" `
  -ContentType "application/json" `
  -Body '{"session_id":"demo","query":"How can I lose fat while keeping muscle?","top_k_context_turns":6}'
```

### 4.2 Full Query (with generated answer + citations)
```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/chat/query" `
  -ContentType "application/json" `
  -Body '{"session_id":"demo","query":"How can I lose fat while keeping strength and avoid shoulder overuse?","top_k_context_turns":6,"top_k_retrieval":5,"max_sub_queries":3}'
```

Check response fields:
- `preprocess`
- `adaptive_plan`
- `hits`
- `generated_answer.summary`
- `generated_answer.answer_markdown`
- `generated_answer.citations`

## 6) Automated Validation (Recommended)

### 5.1 Single-command full validation
```powershell
.\.venv\Scripts\python.exe scripts/validate_all.py
```

Pass condition:
- top-level `passed = true`

### 5.2 Individual validations
```powershell
.\.venv\Scripts\python.exe scripts/validate_index.py
.\.venv\Scripts\python.exe scripts/validate_point2.py
.\.venv\Scripts\python.exe scripts/validate_point3.py
.\.venv\Scripts\python.exe scripts/validate_point4.py
.\.venv\Scripts\python.exe scripts/validate_point5.py
.\.venv\Scripts\python.exe scripts/api_smoke_test.py
```

## 7) Project Status

Implemented and validated:
1. Point 1: Offline indexing
2. Point 2: User query preprocessing
3. Point 3: Adaptive retrieval strategy
4. Point 4: Self-RAG post-processing
5. Point 5: Final answer generation with citations

## 8) Deploy to a Fixed URL (Render)

This repository already includes:
- `render.yaml`
- `Procfile`
- unified backend+frontend serving at one domain
- startup auto-bootstrap for index

Steps:
1. Push `backend` to a GitHub repository.
2. In Render: **New +** -> **Blueprint** -> connect that repo.
3. Set required env vars in Render:
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL`
   - `EMBEDDING_MODEL`
   - `CHAT_MODEL`
4. Click deploy.
5. Open the generated fixed URL (e.g. `https://fitrag-assistant.onrender.com`).

After deploy:
- Homepage serves frontend UI directly.
- API is available under the same domain (`/chat/query`, `/health`, etc.).
