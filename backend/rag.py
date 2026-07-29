"""
Retrieval layer for TIMBA.

Design intent: TIMBA should never write stories from scratch. Every reply
is grounded in a piece of curated content from content/stories/. This
module builds a small vector index over that library and retrieves the
best-matching story for a child's message. The chat layer (main.py) then
asks the LLM to *narrate/adapt* the retrieved story, not invent a new one.

Swap-in path: this uses a local sentence-transformers embedding model so
it works with just a Sarvam LLM key and no separate embeddings provider.
If you later want higher-quality multilingual retrieval, swap
EMBEDDING_MODEL for "BAAI/bge-m3" (heavier, but stronger on Indic text).
"""

import os
import glob
from pathlib import Path

import chromadb
import frontmatter
from sentence_transformers import SentenceTransformer

CONTENT_DIR = Path(__file__).parent / "content" / "stories"
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
COLLECTION_NAME = "timba_stories"

# Multilingual, reasonably small, handles Tamil + English + code-mixed text.
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def get_collection():
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    return client.get_or_create_collection(COLLECTION_NAME)


def load_story_files():
    """Read every markdown file in content/stories/ with its frontmatter metadata."""
    stories = []
    for path in glob.glob(str(CONTENT_DIR / "*.md")):
        post = frontmatter.load(path)
        stories.append(
            {
                "id": Path(path).stem,
                "text": post.content.strip(),
                "metadata": {
                    "story_id": post.get("story_id", Path(path).stem),
                    "title": post.get("title", ""),
                    "language": post.get("language", "en"),
                    "values": ",".join(post.get("values", [])),
                    "age_min": post.get("age_min", 0),
                    "age_max": post.get("age_max", 99),
                    "tags": ",".join(post.get("tags", [])),
                },
            }
        )
    return stories


def build_index():
    """Run this once (and again whenever content/stories/ changes)."""
    stories = load_story_files()
    if not stories:
        raise RuntimeError(f"No story files found in {CONTENT_DIR}")

    embedder = get_embedder()
    collection = get_collection()

    # Wipe and rebuild - simplest correct approach for a content library this size.
    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)

    texts = [f"{s['metadata']['title']}\n{s['text']}" for s in stories]
    embeddings = embedder.encode(texts).tolist()

    collection.add(
        ids=[s["id"] for s in stories],
        embeddings=embeddings,
        documents=[s["text"] for s in stories],
        metadatas=[s["metadata"] for s in stories],
    )
    print(f"Indexed {len(stories)} story documents into '{COLLECTION_NAME}'.")


def retrieve(query: str, language: str = "en", child_age: int | None = None, top_k: int = 1):
    """
    Return the best-matching story chunk(s) for a child's message.

    Filters by language first (don't hand a Tamil story to an English-mode
    session or vice versa), then ranks by semantic similarity to the query.
    """
    embedder = get_embedder()
    collection = get_collection()
    query_embedding = embedder.encode([query]).tolist()

    where_filter = {"language": language}

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where_filter,
    )

    matches = []
    for doc, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        matches.append({"text": doc, "metadata": meta, "distance": distance})
    return matches


if __name__ == "__main__":
    build_index()
