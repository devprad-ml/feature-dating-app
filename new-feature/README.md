# Echoes

A second feature concept for the same dating app, but **not** a conversation starter.

## What it is

Each user writes a vivid personal memory (80-1500 characters). Anything real from their life: small, specific, honest. Claude analyzes the memory and extracts:

- **3-5 themes**: the implicit values it reveals (loyalty, self-doubt, wonder, restraint), not categories (family, work, travel)
- **An emotional register**: one of ten registers (tender, raw, fierce, bittersweet, contemplative…)
- **The lesson**: a single sentence stating the load-bearing life-truth the memory carries, even if the writer didn't say it outright
- **A one-line essence**: the memory's natural title

The user immediately sees their own analysis side-by-side with **one anonymous memory from someone else** that resonates with theirs, plus a one-line "why" written by Claude on the fly.

## Why this isn't a conversation starter

Hot Take Duel produces a debate, then unlocks chat. Echoes does the opposite: it produces **a matching mechanism**. The output isn't a chat window. It's the recognition that someone else carries an adjacent lesson. The conversation, if it happens, starts from the *inside* of two people, not from "hey."

The LLM here is a **values-archaeologist**, not a moderator. It looks at a memory and tells you what you didn't realize you were saying.

## Project layout

```
new-feature/
  backend/
    app/
      main.py            FastAPI entry
      config.py          env-driven settings
      database.py        SQLAlchemy session + init
      models.py          Memory only
      schemas.py         Pydantic request/response
      prompts.py         analyze + resonance-reason prompts
      llm.py             thin Anthropic client
      routers/
        memories.py      POST /memory  (analyze + find echo)
    seed.py              loads 6 hand-crafted seed memories
    requirements.txt
    .env.example
  frontend/
    src/
      App.jsx            one page: compose -> analyze -> result
      api.js
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

Seed the database with 6 hand-written memories so the very first submission has something to echo against:

```powershell
python seed.py --reset
```

Then run the API on **port 8001** (different from Hot Take Duel's 8000):

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

Both Echoes and Hot Take Duel can run at the same time on different ports.

## How to use it

1. Open http://localhost:5174
2. Pick a handle (anything; defaults to `you`)
3. Write a memory. **Be specific and small**. "The time my grandmother cried at my graduation" beats "growing up was hard." 80 character minimum, 1500 max
4. Submit
5. Wait ~3 seconds. Claude analyzes your memory, then finds the most resonant of the seed memories and writes a one-line "why"
6. You see your own analysis (themes, emotion, lesson, essence) and the echoing memory below, with **shared themes highlighted in honey** on both cards
7. Under the echo: **Yes, want to match** / **No thanks** buttons. Click one. The decision is one-shot.

## The two-tab demo (mutual matching)

To see the full mutual-match flow, open the app in **two browser windows** (one normal, one incognito so they're treated as different users). Each tab will end up showing the other's memory as the echo, and when **both** click "Yes, want to match," a green **Mutual Echo** banner appears.

Concrete walkthrough:

1. **Tab 1** (`alice`): write a memory with strong values like loyalty, restraint, or self-trust. Submit. URL becomes `?memory_id=…`.
2. **Tab 2** (`bob`): write a memory with **overlapping themes** (that's how the matching works). If alice wrote about loyalty, bob writes about something like trust or honesty. Submit.
3. Bob's echo will be alice's memory (highest theme overlap). Bob clicks **Yes, want to match**.
4. Alice's tab is polling every 2 seconds. As soon as bob's reaction lands, alice sees the partner has reacted and her UI shows a waiting state if she hasn't decided, or the **Mutual Echo** banner if she already said yes.
5. Tab refresh works at any time. The URL `?memory_id=…` lets either tab reload the current state.

If one tab clicks "No thanks," that tab gets a "you passed" message and the other tab gets "this one didn't unlock." Same neutral copy regardless of who said no first.

## API surface

Three endpoints:

```
POST /memory                       analyze + cache the echo + return state
Body: { "author_handle": "you", "text": "..." }

GET  /memory/{memory_id}           fetch current state (used by polling)

POST /memory/{from_id}/react       store a yes/no reaction
Body: { "to_memory_id": "...", "kind": "yes" | "no" }
```

All three return the same shape:

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

`echo` is `null` only if you're the very first memory in the system. Reactions are **one-shot**. Calling `/react` a second time for the same `(from, to)` pair returns 409.

## How the matching works

Two-step, on every submission:

1. **Theme overlap (deterministic, no LLM):** the new memory's themes are intersected with each existing memory's themes. Highest overlap wins, with the same emotional register as a tiebreaker. This picks *who* you're paired with.
2. **Resonance reason (one Claude call):** the chosen pair is sent to Claude with `SYSTEM_RESONANCE_REASON` and a one-line "why" comes back. This produces the *language* of the match.

Two LLM calls per submission total: one to analyze the new memory, one to write the resonance line.

## Production seams

Same pattern as Hot Take Duel. Auth wraps `author_handle`, SQLite swaps for Postgres via `DATABASE_URL`, theme-overlap matching gets replaced with embeddings (OpenAI/Voyage `text-embedding`) for sub-second semantic search at scale, and a moderation pass on submitted memory text is required before any of this hits real users.
