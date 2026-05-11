# Echoes

A dating-app feature that matches people on the lessons their memories reveal, not on bios or photos.

## What it is

Each user writes one vivid personal memory (80 to 1500 characters). Anything real from their life: small, specific, honest. Claude analyzes the memory and extracts:

- **3-5 themes**: the implicit values it reveals (loyalty, self-doubt, wonder, restraint), not categories (family, work, travel)
- **An emotion**: one of ten emotional registers (tender, raw, fierce, bittersweet, contemplative, hopeful, melancholic, playful, defensive, vulnerable)
- **The lesson**: a single sentence stating the load-bearing life-truth the memory carries, even if the writer didn't say it outright
- **A one-line essence**: the memory's natural title

The user immediately sees their own analysis side-by-side with **one anonymous memory from someone else** that resonates with theirs, plus a one-line "why" written by Claude on the fly. Shared themes are visually highlighted on both cards.

Under the echo are two buttons: **Yes, want to match** / **No thanks**. Decisions are one-shot. If both users say yes, a mutual-match banner reveals the partner's handle and signals that the conversation can now begin from a place of having already seen each other's interior.

## Why this isn't a conversation starter

Most dating-app features are openers in disguise. Echoes is deliberately not. The output is not a chat window. It's the recognition that someone else carries an adjacent piece of life. The conversation, if it happens, starts from inside two people, not from "hey."

The product thesis: **people who have learned similar lessons from different lives are more compatible than people with overlapping interests.**

The LLM here is a **values-archaeologist**, not a moderator or a content generator. It reads what you wrote and tells you what you didn't realize you were saying.

## Project layout

```
new-feature/
  backend/
    app/
      main.py            FastAPI entry
      config.py          env-driven settings
      database.py        SQLAlchemy session + init
      models.py          Memory, Reaction
      schemas.py         Pydantic request/response
      prompts.py         analyze + resonance-reason prompts
      llm.py             thin Anthropic client with fallback
      routers/
        memories.py      POST /memory, GET /memory/{id}, POST /memory/{id}/react
    seed.py              loads 6 hand-crafted seed memories
    requirements.txt
    .env.example
  frontend/
    src/
      App.jsx            one page: compose + analyze + result + react
      api.js             three thin fetch wrappers
      styles.css         warm sepia palette, serif typeface
```

## Setup

### 1. Backend

```powershell
cd c:\feature-dating-app\new-feature\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env, paste ANTHROPIC_API_KEY=sk-ant-...
```

Seed the database with 6 hand-crafted memories so the very first submission has something to echo against:

```powershell
python seed.py --reset
```

Run the API:

```powershell
uvicorn app.main:app --reload --port 8001
```

### 2. Frontend

```powershell
cd c:\feature-dating-app\new-feature\frontend
npm install
npm run dev
```

Vite serves on **http://localhost:5174** and proxies `/api` to `:8001`.

## How to use it

1. Open http://localhost:5174
2. Pick a handle (anything; defaults to `you`)
3. Write a memory. **Be specific and small.** "The time my grandmother cried at my graduation" beats "growing up was hard." 80 character minimum, 1500 maximum.
4. Submit. Wait ~3 seconds while Claude analyzes.
5. The result screen shows your memory's analysis (themes, emotion, lesson, essence) on top, and the most resonant existing memory below, with a one-line "why" written by Claude. **Shared themes are highlighted in honey** on both cards.
6. Under the echo: **Yes, want to match** / **No thanks** buttons. Click one. The decision is one-shot.

### Picking a memory that lands a satisfying echo

Each seed memory has its own theme cluster. Write a memory whose values overlap with one of these and Claude will pair you with it:

| Seed | Themes | What to write to match it |
|---|---|---|
| **rivka** | honesty, patience, the cost of waiting | a small confession you delayed; a moment of being given grace |
| **isaac** | risk, agency, self-trust | a decision you made without a plan, against advice |
| **mira** | pride, regret, love through teaching | something you couldn't bring yourself to do until it was too late |
| **dev** | presence, wordless kindness, shared grief | sitting with a stranger or someone in pain without saying anything |
| **saoirse** | self-knowledge, boundaries, being unheard | telling someone close who you are and not being believed |
| **tomas** | pragmatism, sibling memory, the cost of solving | a childhood project where solving the problem broke something else |

### About the reaction buttons

The Yes / No buttons store a one-shot reaction in the database. Mutual match (the green banner) only triggers when **both** users in a paired memory click Yes. Because seed memories have no real user behind them, clicking Yes on a seed leaves you in the polling "waiting on them" state. That's expected behavior, and it shows the UI states correctly. To trigger an actual mutual match, two real users have to write memories that pair with each other and both click Yes.

## API surface

Three endpoints, all returning the same shape:

```
POST /memory                       analyze + cache the echo + return state
Body: { "author_handle": "you", "text": "..." }

GET  /memory/{memory_id}           fetch current state (used by 2s polling)

POST /memory/{from_id}/react       store a yes/no reaction
Body: { "to_memory_id": "...", "kind": "yes" | "no" }
```

Response shape:

```
{
  "you": { ...analyzed memory... },
  "echo": {
    "memory": { ...the other person's analyzed memory... },
    "resonance_reason": "you both write about loyalty as something earned slowly",
    "overlap_themes": ["loyalty", "patience"],
    "my_reaction": "yes" | "no" | null,
    "their_reaction": "yes" | "no" | null,
    "mutual": true | false
  }
}
```

`echo` is `null` only if you're the very first memory in the system (which never happens after seeding). Reactions are **one-shot**: calling `/react` a second time for the same `(from, to)` pair returns 409.

## How the matching works

Two-step, on every submission:

1. **Theme overlap (deterministic, no LLM).** The new memory's themes are intersected with each existing memory's themes. Highest overlap wins, with the same emotional register as a tiebreaker. This picks *who* you're paired with.
2. **Resonance reason (one Claude call).** The chosen pair is sent to Claude with `SYSTEM_RESONANCE_REASON` and a one-line "why" comes back. This produces the *language* of the match.

Two LLM calls per submission total: one to analyze the new memory, one to write the resonance line.

The matching/language split is intentional. The *who* is a deterministic, free SQL operation, so A/B testing is possible and cost stays predictable. The *language* is the LLM's job, where it adds the most value. At scale you swap step 1 for vector embeddings; the split itself stays.

## Defensive design choices to know

| Decision | Why |
|---|---|
| Echo info **cached** on the Memory row | Polling and refresh stay free; mutual-match target is stable across time |
| `resonance_reason` falls back to a templated sentence | LLM outage doesn't break the UI |
| Reaction has **unique `(from, to)`** constraint | One-shot decisions enforced at the DB level |
| Polling **auto-stops** at final states | Browsers don't burn CPU forever |
| Same neutral copy regardless of who said no | Rejection asymmetry: the rejected user never gets attribution |
| Seed memories ship with hand-written analyses | Re-seeding doesn't cost Claude calls |
| Lazy LLM client init | Missing API key doesn't crash startup, just the endpoints that need it |

## Production seams

| Today | Production |
|---|---|
| `author_handle` as a free text field | Wrap with auth (JWT/session) |
| SQLite file | Postgres via `DATABASE_URL` change |
| Theme-overlap matching | Vector embeddings (cosine similarity) for sub-second semantic search |
| 2-second polling | WebSocket push for real-time sync |
| Open CORS | Lock to the real frontend origin |
| Vite proxy | Serve built React bundle from FastAPI/static CDN |
| No moderation on submitted memory | Claude moderation pass + report flow |
| No rate limits | Per-user limits on `/memory` (each call costs 2 Claude requests) |
| No chat after mutual match | Real messaging UI keyed off `mutual=True` |
