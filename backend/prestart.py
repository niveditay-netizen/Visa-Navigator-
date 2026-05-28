"""Run before uvicorn to surface startup errors clearly in Render logs."""
import sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Python: {sys.version}", flush=True)

print("Testing chromadb...", flush=True)
import chromadb
client = chromadb.PersistentClient(path="data/chroma_db")
col = client.get_collection("uscis_docs")
print(f"  chromadb OK — collection has {col.count()} chunks", flush=True)

print("Testing fastembed...", flush=True)
from fastembed import TextEmbedding
model = TextEmbedding("BAAI/bge-small-en-v1.5")
vec = list(model.embed(["test"]))
print(f"  fastembed OK — embedding dim={len(vec[0])}", flush=True)

print("All checks passed. Starting server...", flush=True)
