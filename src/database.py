import os
import json
import hashlib
import math
import re
from functools import lru_cache

import chromadb


class LocalHashEmbeddingFunction:
    """Small deterministic embedding function that keeps ChromaDB fully local."""

    def __init__(self, dimensions=384):
        self.dimensions = dimensions

    def name(self):
        return "local_hash_embedding"

    def __call__(self, input):
        return [self._embed(document) for document in input]

    def embed_documents(self, input):
        return self(input)

    def embed_query(self, input):
        return self(input)

    def _embed(self, document):
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", document.lower())

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude:
            vector = [value / magnitude for value in vector]
        return vector

@lru_cache(maxsize=1)
def get_chroma_client(persist_directory="chroma_db"):
    """
    Get a persistent ChromaDB client pointing to the given directory.
    Uses absolute path relative to project root to avoid path mismatch issues.
    """
    # The database.py is in src/, project root is parent directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, persist_directory)
    # Ensure directory exists
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)

def get_collection(client, api_key=None):
    """
    Retrieve or create the collection using a deterministic local embedding function.
    This avoids first-run model downloads and keeps ChromaDB retrieval self-contained.
    """
    return client.get_or_create_collection(
        name="sports_facts_local",
        embedding_function=LocalHashEmbeddingFunction()
    )

def populate_database_if_empty(client, api_key, facts_json_path=None):
    """
    Idempotently populate the ChromaDB collection from sports_facts.json.
    Skips if the collection contains any documents.
    """
    collection = get_collection(client, api_key)
    
    # Check current size
    count = collection.count()
    if count > 0:
        return False, f"Collection already contains {count} facts. Skipping database population."
        
    # Resolve default path if not provided
    if not facts_json_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        facts_json_path = os.path.join(base_dir, "data", "sports_facts.json")
        
    if not os.path.exists(facts_json_path):
        raise FileNotFoundError(f"Offline facts JSON not found at: {facts_json_path}")
        
    with open(facts_json_path, "r", encoding="utf-8") as f:
        facts = json.load(f)
        
    documents = []
    metadatas = []
    ids = []
    
    for i, item in enumerate(facts):
        # Clean white spaces and validate fields
        fact_text = item.get("fact", "").strip()
        sport_name = item.get("sport", "").strip()
        if fact_text and sport_name:
            documents.append(fact_text)
            metadatas.append({"sport": sport_name})
            ids.append(f"fact_{sport_name.lower()}_{i}")
            
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return True, f"Successfully loaded {len(documents)} facts into ChromaDB."
    return False, "No facts loaded (empty JSON file)."

@lru_cache(maxsize=32)
def _get_facts_by_sport_cached(sport, query_text, n_results):
    """
    Retrieve sport-filtered facts from ChromaDB and rank them by query overlap.
    The corpus is small and already labeled, so metadata retrieval is faster than
    running a vector query on every quiz request while still using ChromaDB as
    the knowledge source.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    results = collection.get(
        where={"sport": sport}
    )

    documents = results.get("documents", [])
    if not documents:
        return []

    query_terms = set(re.findall(r"[a-z0-9]+", query_text.lower()))

    def relevance_score(document):
        document_terms = set(re.findall(r"[a-z0-9]+", document.lower()))
        return len(query_terms & document_terms)

    ranked_documents = sorted(documents, key=relevance_score, reverse=True)
    return ranked_documents[:n_results]


def query_facts_by_sport(client, api_key, sport, query_text="key events achievements facts", n_results=5):
    """
    Retrieve relevant documents filtered by sport metadata from ChromaDB.
    """
    return _get_facts_by_sport_cached(sport, query_text, n_results)
