import os
import re
import chromadb
from fastembed import TextEmbedding

WORDS_PER_CHUNK = 200
OVERLAP_WORDS = 30


def parse_frontmatter(filepath: str) -> dict:
    meta = {}
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read(2000)
        match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            for line in match.group(1).splitlines():
                if ": " in line:
                    key, val = line.split(": ", 1)
                    meta[key.strip()] = val.strip()
    except Exception:
        pass
    return meta


def read_body(filepath: str) -> str:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"^---\n.*?\n---\n?", content, re.DOTALL)
    return content[match.end():] if match else content


def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + WORDS_PER_CHUNK])
        if chunk.strip():
            chunks.append(chunk)
        i += WORDS_PER_CHUNK - OVERLAP_WORDS
    return chunks


def ingest():
    print("Loading embedding model...")
    embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")

    print("Loading and chunking documents...")
    docs_dir = "data/uscis_docs"
    all_texts, all_metas = [], []

    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        filepath = os.path.join(docs_dir, fname)
        meta = parse_frontmatter(filepath)
        title = meta.get("title") or fname.replace(".txt", "").replace("-", " ").title()
        chunks = chunk_text(read_body(filepath))
        print(f"  {fname}: {len(chunks)} chunks")
        for chunk in chunks:
            all_texts.append(chunk)
            all_metas.append({
                "title": title,
                "source": meta.get("source", "USCIS"),
                "url": meta.get("url", ""),
                "file_name": fname,
            })

    print(f"\nTotal: {len(all_texts)} chunks")

    print("Embedding chunks (this takes a minute)...")
    embeddings = [e.tolist() for e in embed_model.embed(all_texts)]

    print("Setting up ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="data/chroma_db")
    try:
        chroma_client.delete_collection("uscis_docs")
        print("  Deleted existing collection")
    except Exception:
        pass
    collection = chroma_client.create_collection(
        name="uscis_docs",
        metadata={"hnsw:space": "cosine"},
    )

    print("Storing chunks...")
    ids = [str(i) for i in range(len(all_texts))]
    collection.add(ids=ids, embeddings=embeddings, documents=all_texts, metadatas=all_metas)

    print(f"\nDone. {len(all_texts)} chunks stored in ChromaDB at data/chroma_db/")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ingest()
