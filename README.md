# Visa Navigator

A RAG (Retrieval-Augmented Generation) agent that answers US employment-based immigration questions using official USCIS documents. It cites every claim, abstains on out-of-scope questions, and never gives legal advice.

**Live demo**: https://visa-navigator-five.vercel.app/

---

## What it does

- Answers questions about H-1B, L-1, O-1, EB-1/2/3, I-140, I-485, EAD, and related forms
- Cites the specific USCIS document for every factual claim
- Declines to speculate on case outcomes, processing times, or out-of-scope topics
- Streams responses token-by-token for a fast feel

## Architecture

```
User → React frontend (Vercel)
          ↓ POST /api/chat
     FastAPI backend (Render)
          ↓
     ChromaDB (453 chunks, BAAI/bge-small-en-v1.5 embeddings)
          ↓ top-8 retrieved chunks
     Groq LLM (llama-3.3-70b-versatile) → streamed response
```

**Retrieval**: Query is embedded with fastembed → cosine similarity search over 453 chunks from 6 USCIS instruction PDFs → top-8 chunks injected into system prompt.

**Generation**: Groq's `llama-3.3-70b-versatile` with a strict 8-rule system prompt enforcing citation format, abstention triggers, and scope limits.

## Knowledge base

| Document | Coverage |
|---|---|
| Form I-129 Instructions | H-1B, L-1, O-1, and other nonimmigrant workers |
| Form I-140 Instructions | EB-1, EB-2, EB-3 immigrant worker petitions |
| Form I-485 Instructions | Adjustment of status (green card) |
| Form I-485 Supplement J | AC21 job portability |
| Form I-539 Instructions | Extension/change of nonimmigrant status |
| Form I-765 Instructions | Employment Authorization Document (EAD) |

## Eval results

Tested against 40 hand-written cases across three categories:

```
Overall:  31/40 (77.5%)
Factual   : 14/20   ██████████████░░░░░░
Abstain   : 12/12   ████████████  (perfect)
Citation  : 5/8     █████░░░
```

The abstain category scores 100% — the agent correctly refuses to answer out-of-scope questions (Canadian immigration, tourist visas, legal predictions, freelance work on H-1B, etc.).

Factual gaps are mostly due to content not explicitly stated in the instruction PDFs (e.g., specific H-1B period lengths live in the USCIS Policy Manual, not the I-129 instructions).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Tailwind CSS 4, Vite |
| Backend | FastAPI, Python 3.14 |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5, ONNX) |
| Vector store | ChromaDB 1.x (cosine similarity) |
| LLM | Groq API — llama-3.3-70b-versatile |
| Hosting | Vercel (frontend) + Render free tier (backend) |
| Logging | SQLite (conversation turns) |

## Running locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

**Re-ingest** (if you add new documents to `backend/data/uscis_docs/`):
```bash
cd backend && python ingest.py
```

**Run eval**:
```bash
cd eval && python run_eval.py
```

## Project structure

```
visa-navigator/
├── backend/
│   ├── main.py          # FastAPI app — streaming + sync endpoints
│   ├── retrieval.py     # ChromaDB query via fastembed
│   ├── ingest.py        # One-time ingestion script (run locally)
│   ├── db.py            # SQLite conversation logging
│   ├── data/
│   │   ├── chroma_db/   # Persisted vector store (committed to repo)
│   │   └── uscis_docs/  # Source .txt files with frontmatter metadata
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWidget.tsx   # Main chat UI
│   │   │   └── MessageBubble.tsx # Citation badge rendering
│   │   └── hooks/useChat.ts     # SSE streaming hook
│   └── package.json
└── eval/
    ├── cases.json       # 40 test cases (factual / abstain / citation)
    └── run_eval.py      # Eval runner with keyword scoring
```

## Notes

- The backend is on Render's free tier, which spins down after 15 min of inactivity. The first request after a cold start takes ~30s.
- The ChromaDB vector store is committed to the repo so no ingestion step is needed on the server.
- The system prompt enforces that the agent never uses knowledge outside the retrieved USCIS documents.
