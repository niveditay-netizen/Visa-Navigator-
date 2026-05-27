import warnings
warnings.filterwarnings("ignore")

import chromadb
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, Settings

Settings.llm = None
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.embed_model = embed_model

chroma_client = chromadb.PersistentClient(path="data/chroma_db")
chroma_collection = chroma_client.get_collection("uscis_docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)


def retrieve(query: str, top_k: int = 8) -> list[dict]:
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    results = []
    for node in nodes:
        meta = node.metadata
        # Derive a clean title from filename if explicit title is missing
        title = meta.get("title") or meta.get("file_name", "USCIS Document")
        if title == title.lower() and title.endswith(".txt"):
            title = title.replace(".txt", "").replace("-", " ").title()
        results.append({
            "text": node.get_text(),
            "score": node.get_score(),
            "source": meta.get("source", "USCIS"),
            "title": title,
            "url": meta.get("url", ""),
        })
    return results
