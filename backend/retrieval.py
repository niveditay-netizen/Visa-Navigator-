import warnings
warnings.filterwarnings("ignore")

import chromadb
from fastembed import TextEmbedding

embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
chroma_client = chromadb.PersistentClient(path="data/chroma_db")
chroma_collection = chroma_client.get_collection("uscis_docs")


def retrieve(query: str, top_k: int = 8) -> list[dict]:
    query_embedding = list(embed_model.embed([query]))[0].tolist()
    results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for text, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        title = meta.get("title") or meta.get("file_name", "USCIS Document")
        if title == title.lower() and title.endswith(".txt"):
            title = title.replace(".txt", "").replace("-", " ").title()
        output.append({
            "text": text,
            "score": 1.0 - distance,  # cosine distance → similarity
            "source": meta.get("source", "USCIS"),
            "title": title,
            "url": meta.get("url", ""),
        })
    return output
