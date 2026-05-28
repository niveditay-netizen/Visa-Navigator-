import os
import json
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Ensure working directory is the backend folder so relative paths work on Render
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from retrieval import retrieve
from db import log_turn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # retrieval module is already initialized at import time; just yield
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT_TEMPLATE = """You are a US immigration information assistant grounded in official USCIS documents.

RULES — follow these strictly:
1. Answer ONLY using information from the CONTEXT below. Never use outside knowledge.
2. Cite your source for every factual claim using the format [Source: document title].
3. If the context does not contain the answer, say: "This isn't covered in the USCIS guidance I have access to. I'd recommend consulting an immigration attorney or checking uscis.gov directly."
4. If the question asks for legal advice, case strategy, or predictions about case outcomes, say: "That requires legal judgment specific to your situation. An immigration attorney would be the right resource here."
5. If the question is about current processing times, say: "Processing times change frequently. Check the USCIS processing times page at egov.uscis.gov/processing-times for current estimates."
6. If the question is about a visa type not in the context (e.g., family-based, asylum, student visas), say: "My current knowledge base covers employment-based immigration only. For [topic], I'd recommend checking uscis.gov directly."
7. Be clear, concise, and use plain language.
8. End every response with: "Note: This is informational only based on published USCIS guidance, not legal advice."

CONTEXT:
{context}
"""


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Document {i}: {chunk['title']}]\n"
            f"Source: {chunk['url']}\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    history = body.get("history", [])
    session_id = body.get("session_id", str(uuid.uuid4()))

    chunks = retrieve(user_message, top_k=5)
    context = build_context(chunks)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    log_turn(session_id, "user", user_message)

    def generate():
        full_response = ""
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.1,
            max_tokens=1024,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_response += delta
            yield f"data: {json.dumps({'content': delta})}\n\n"

        log_turn(session_id, "assistant", full_response)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/chat/sync")
async def chat_sync(request: Request):
    """Non-streaming endpoint used by the eval script."""
    body = await request.json()
    user_message = body.get("message", "")
    history = body.get("history", [])
    session_id = body.get("session_id", str(uuid.uuid4()))

    chunks = retrieve(user_message, top_k=5)
    context = build_context(chunks)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
        stream=False,
    )
    answer = response.choices[0].message.content or ""
    log_turn(session_id, "user", user_message)
    log_turn(session_id, "assistant", answer)
    return {"response": answer}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
