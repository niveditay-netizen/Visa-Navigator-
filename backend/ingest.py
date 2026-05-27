import os
import re
import chromadb
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext


def parse_frontmatter(filepath: str) -> dict:
    """Extract title/source/url from the --- frontmatter block at the top of each doc."""
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


def ingest():
    print("Loading embedding model...")
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.embed_model = embed_model
    Settings.llm = None

    print("Loading documents...")

    def file_metadata(filepath: str) -> dict:
        meta = parse_frontmatter(filepath)
        return {
            "title": meta.get("title", os.path.basename(filepath)),
            "source": meta.get("source", "USCIS"),
            "url": meta.get("url", ""),
            "file_name": os.path.basename(filepath),
        }

    documents = SimpleDirectoryReader(
        input_dir="data/uscis_docs",
        recursive=True,
        file_metadata=file_metadata,
    ).load_data()
    print(f"  Loaded {len(documents)} documents")
    for doc in documents:
        print(f"    {doc.metadata.get('title', '?')[:70]}")

    print("Chunking...")
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"  Created {len(nodes)} chunks")

    print("Setting up ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="data/chroma_db")
    try:
        chroma_client.delete_collection("uscis_docs")
        print("  Deleted existing collection")
    except Exception:
        pass
    chroma_collection = chroma_client.create_collection("uscis_docs")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("Embedding and storing chunks (this takes a few minutes)...")
    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )

    print(f"\nDone. {len(nodes)} chunks stored in ChromaDB at data/chroma_db/")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ingest()
