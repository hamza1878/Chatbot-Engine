# Moviroo AI Chatbot

Multilingual RAG chatbot for transport support.  
Stack: **SentenceTransformer → FAISS → Mistral/Llama → FastAPI**

---

## Architecture

```
User question
     │
     ▼
FastAPI  POST /chat
     │
     ▼
SentenceTransformer (embed)
paraphrase-multilingual-mpnet-base-v2
     │  768-dim float32
     ▼
FAISS IndexFlatIP (search k=5)
     │
     ├─ score ≥ 0.82 ──► Direct answer (fast, no LLM)
     │
     ├─ score 0.55–0.82 ► Mistral/Llama enriched answer
     │
     └─ score < 0.55 ───► Fallback + auto-create ticket
```

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Ollama + Mistral

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral            # ~4 GB
ollama serve                   # keep running in background
```

> **No GPU?** Use `ollama pull llama3.2` (~2 GB) and set `OLLAMA_MODEL=llama3.2` in `.env`

### 3. Configure

```bash
cp .env.example .env
# Edit .env if needed (default SQLite, localhost Ollama)
```

### 4. Add your dataset

Copy your `dataset_1000.csv` to `data/dataset.csv`.

Required columns: `question`, `answer`, `category`, `language`

### 5. Run

```bash
python main.py
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

---

## Test the pipeline

```bash
python test_pipeline.py          # full test
python test_pipeline.py --csv-only  # skip DB
```

---

## API Reference

### POST /chat
```json
{
  "message": "My payment failed",
  "session_id": "optional-uuid"
}
```
Response:
```json
{
  "answer": "Check card funds, details, and expiry...",
  "confidence": 0.87,
  "category": "payment",
  "language": "en",
  "source": "direct_match",
  "suggest_ticket": false,
  "session_id": "..."
}
```

### POST /tickets
```json
{ "question": "I need help with my account", "language": "en" }
```

### PATCH /tickets/{ticket_id}/resolve
```json
{ "answer": "Go to Settings > Account to update your details." }
```
Resolving a ticket **automatically adds it to the FAISS index** (incremental learning).

### POST /feedback
```json
{ "ticket_id": "TKT-ABC123", "rating": 5, "helpful": true }
```

### GET /health
### GET /stats
### POST /admin/rebuild-index

---

## Supported Languages

| Language | Example |
|---|---|
| English | "My payment failed" |
| Français | "Mon paiement a échoué" |
| العربية | "فشل الدفع" |
| Franco-Arabic | "machkel fil paiement" |

---

## Project Structure

```
moviroo/
├── main.py                    # FastAPI app + lifespan
├── config.py                  # All settings via .env
├── requirements.txt
├── .env.example
├── test_pipeline.py           # Standalone test script
│
├── api/
│   ├── chat.py                # POST /chat
│   ├── tickets.py             # CRUD tickets
│   ├── feedback.py            # POST /feedback
│   └── health.py              # /health /stats /admin
│
├── core/
│   ├── rag_pipeline.py        # FAISS → routing → LLM
│   └── llm_service.py         # Ollama integration
│
├── models/
│   ├── embedding.py           # SentenceTransformer + Franco-Arabic augment
│   └── vector_store.py        # FAISS wrapper
│
├── pipelines/
│   └── training_pipeline.py   # CSV + tickets → FAISS rebuild
│
├── database/
│   ├── connection.py          # SQLAlchemy async engine
│   └── models.py              # Ticket, Feedback tables
│
└── data/
    └── dataset.csv            # Training data (1000+ rows)
```

---

## Confidence Thresholds

| Score | Action | `source` field |
|---|---|---|
| ≥ 0.82 | Direct answer, no LLM | `direct_match` |
| 0.55 – 0.82 | LLM generates enriched answer | `rag_llm` |
| < 0.55 | Fallback + auto-ticket created | `fallback` |

Adjust in `.env`: `HIGH_CONFIDENCE_THRESHOLD`, `LOW_CONFIDENCE_THRESHOLD`

---

## Production Notes

- Swap SQLite for PostgreSQL: `DATABASE_URL=postgresql+asyncpg://user:pass@host/db`
- Use `API_WORKERS=4` in `.env` for multi-worker production
- Schedule `POST /admin/rebuild-index` nightly to pick up new resolved tickets
- For GPU inference: replace `faiss-cpu` with `faiss-gpu` in requirements
