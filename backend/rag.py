"""
Lightweight retrieval layer for TIMBA.

Design intent: TIMBA should never write stories from scratch. Every reply
is grounded in a piece of curated content from content/stories/.

An earlier version did this with local vector embeddings
(sentence-transformers + chromadb), which pulled in torch and needed
~800MB+ of runtime memory just to search a handful of stories - massive
overkill for a library this size, and it's what caused the production
OOM crash on /chat.

This version matches in two cheap steps instead:
1. Keyword/tag overlap scoring against each story's metadata - instant,
   no network call, handles the common case.
2. If nothing scores confidently, ask the Sarvam LLM itself to pick the
   best-fitting story_id from the shortlist - one small, cheap chat call.
   No local ML model is ever loaded into memory.

Revisit this if the story library grows into the hundreds of stories -
at that scale, real embedding search becomes worth the memory cost again.
"""

import glob
import re
from pathlib import Path

import frontmatter

import sarvam_client

CONTENT_DIR = Path(__file__).parent / "content" / "stories"

_stories_cache: list[dict] | None = None


def load_story_files() -> list[dict]:
    """Read every markdown file in content/stories/ with its frontmatter metadata.
    Cached after first call - these files don't change at runtime."""
    global _stories_cache
    if _stories_cache is not None:
        return _stories_cache

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
                    "values": post.get("values", []),
                    "age_min": post.get("age_min", 0),
                    "age_max": post.get("age_max", 99),
                    "tags": post.get("tags", []),
                },
            }
        )
    if not stories:
        raise RuntimeError(f"No story files found in {CONTENT_DIR}")
    _stories_cache = stories
    return stories


def _keywords(text: str) -> set[str]:
    # Matches Latin + Tamil unicode ranges so this works for both languages.
    return set(re.findall(r"[a-zA-Z\u0B80-\u0BFF]+", text.lower()))


def _keyword_score(query: str, story: dict) -> int:
    query_words = _keywords(query)
    story_words = _keywords(story["metadata"]["title"])
    for tag in story["metadata"]["tags"]:
        story_words |= _keywords(tag)
    for value in story["metadata"]["values"]:
        story_words |= _keywords(value)
    return len(query_words & story_words)


def _llm_pick(query: str, candidates: list[dict]) -> dict:
    """Ask Sarvam to choose the best-fitting story from a short list."""
    listing = "\n".join(
        f'{i+1}. id={c["metadata"]["story_id"]} title="{c["metadata"]["title"]}" '
        f'values={",".join(c["metadata"]["values"])} tags={",".join(c["metadata"]["tags"])}'
        for i, c in enumerate(candidates)
    )
    system_prompt = (
        "You are a router. Given a child's message and a numbered list of "
        "available stories, reply with ONLY the story_id of the single best "
        "match - no other text, no punctuation."
    )
    reply = sarvam_client.chat_completion(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": f'Child said: "{query}"\n\nStories:\n{listing}'}],
        max_tokens=20,
    )
    picked_id = reply.strip().split()[0] if reply.strip() else None
    for c in candidates:
        if c["metadata"]["story_id"] == picked_id:
            return c
    return candidates[0]  # safe fallback - never leave a child with no story


def retrieve(query: str, language: str = "en", child_age: int | None = None, top_k: int = 1):
    """
    Return the best-matching story for a child's message.
    Filters by language first, then matches by keyword overlap, falling
    back to an LLM pick only when keyword matching is inconclusive.
    """
    stories = load_story_files()
    candidates = [s for s in stories if s["metadata"]["language"] == language]
    if not candidates:
        return []

    scored = sorted(candidates, key=lambda s: _keyword_score(query, s), reverse=True)
    top_score = _keyword_score(query, scored[0])

    best = scored[0] if top_score > 0 else _llm_pick(query, candidates)

    return [{"text": best["text"], "metadata": best["metadata"], "distance": None}]
