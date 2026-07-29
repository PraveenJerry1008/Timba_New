# TIMBA — software MVP starter

A grounded-generation companion app: TIMBA never invents stories — it
retrieves the closest match from a curated story library (`backend/content/stories`)
and narrates/personalizes that specific content, in English or Tamil, via Sarvam AI.

## What's real vs. what's a stub

**Real, working architecture:**
- RAG retrieval (`rag.py`) — Chroma + multilingual embeddings, filtered by language
- FastAPI backend wiring retrieval → grounded system prompt → Sarvam chat completion
- React frontend calling that backend
- Sample bilingual story content with values metadata

**Written but NOT tested against the live Sarvam API** (this build environment has no
internet access) — `sarvam_client.py` was written from Sarvam's published docs/pricing
pages. Before you run this for real: check https://docs.sarvam.ai and confirm the
endpoint paths, request/response field names, and model name (`sarvam-m` in the code)
still match. API surfaces shift as vendors ship new models.

**Deliberately a stub, not production-ready:**
- `safety.py` is a keyword blocklist — a floor, not a real moderation layer. Before
  this touches a real child, add a proper classifier (e.g. Llama Guard) as a second pass.
- No auth, no database, no parent dashboard backend — those were mocked in an earlier
  demo; this build focuses on the core grounded-chat loop we discussed.
- Only 2 sample stories (courage, honesty) in 2 languages — enough to prove retrieval
  works, not enough content for a real product.

## Setup

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your SARVAM_API_KEY (sign up at https://dashboard.sarvam.ai)

python rag.py            # builds the vector index from content/stories/
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev              # opens on http://localhost:5173
```

Try asking TIMBA "tell me a story about being brave" — it should retrieve
`brave_elephant` from the library and narrate it, in whichever language you've
selected.

## Adding new content
Drop a new `.md` file into `backend/content/stories/` with frontmatter
(`story_id`, `title`, `language`, `values`, `age_min`, `age_max`, `tags`) — see
the existing files for the format. Re-run `python rag.py` to rebuild the index.
Write each story once per language (matching `story_id`, different `language`)
so retrieval stays consistent across English and Tamil.

## Next steps, in rough priority order
1. Swap the keyword safety filter for a real moderation pass.
2. Build out the story library — aim for broad coverage across the values you
   want to reinforce before opening this to real families.
3. Add parent auth + a real dashboard backend (session logs, values-touched summary).
4. Voice: wire `sarvam_client.text_to_speech` / `speech_to_text` into the frontend
   (mic capture + playback) — stubbed in the backend already, not wired to the UI yet.
5. Deploy: backend to any Python host (Railway, Render, Fly.io), frontend to
   Vercel/Netlify. Set `ALLOWED_ORIGINS` and `VITE_BACKEND_URL` accordingly.
6. Hardware phase: point a Raspberry Pi's mic/speaker at this same backend
   over Wi-Fi rather than attempting on-device inference — see the cost/architecture
   discussion for why that's the more realistic first hardware step.
