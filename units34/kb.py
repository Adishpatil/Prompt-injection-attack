"""Unit 3 - RAG channel: a Chroma collection that can contain one poisoned chunk."""
import time

import chromadb
import ollama

from config import EMBED_MODEL

BENIGN_DOCS = {
    "hours": "Support hours are 9 AM to 6 PM, Monday to Friday.",
    "returns": "Items can be returned within 30 days with a receipt.",
    "shipping": "Standard shipping takes 3-5 business days within India.",
    "holidays": "Holiday policy: the office is closed on national holidays.",
}


def embed(texts):
    """Local embeddings via Ollama (run: ollama pull nomic-embed-text)."""
    return ollama.embed(model=EMBED_MODEL, input=texts)["embeddings"]


def build_kb(poison=None):
    """Fresh in-memory collection. `poison` is one extra attacker-controlled chunk."""
    client = chromadb.EphemeralClient()
    # cosine, not Chroma's default L2: L2 favours short chunks, so a long poisoned chunk
    # could silently fail to be retrieved and the attack would never reach the model
    col = client.create_collection(f"kb_{time.time_ns()}",
                                   configuration={"hnsw": {"space": "cosine"}})
    ids, texts = list(BENIGN_DOCS), list(BENIGN_DOCS.values())
    if poison:
        ids.append("poisoned")
        texts.append(poison)
    col.add(ids=ids, documents=texts, embeddings=embed(texts))
    return col


def retrieve(col, query, k=2):
    res = col.query(query_embeddings=embed([query]), n_results=k)
    return [{"id": i, "text": t} for i, t in zip(res["ids"][0], res["documents"][0])]
