# Recipe Companion Challenge

Build a cooking companion. A user drops in a recipe (PDF or text), your app extracts it, shows it beautifully, and lets the user chat with an agent that can scale servings, swap ingredients, and walk them through the steps.

The backend is done. Your job is the frontend.

## Target device: a tablet in the kitchen

Design for a **tablet**, not a laptop. The cook props it on a worktop, glances at it with wet or messy hands, follows steps while cooking. This shapes most of your UX decisions:

- **Touch-first.** Big, forgiving tap targets. No hover states — assume there is no cursor.
- **Landscape is primary.** Portrait is fine as a secondary layout; mobile is nice-to-have, not the goal.
- **Readable at arm's length.** Generous type, strong contrast, plenty of whitespace. Dense desktop-style chrome is wrong here.
- **One-handed and glanceable.** The cook is holding a spatula. Long paragraphs, deep menus and tiny controls will hurt.

If you are prototyping in a browser, set the viewport to something like **1024×768** and design against that.

## What you get

A working Python backend with:

- `POST /upload` — parses a recipe file into structured data.
- `POST /copilotkit` — an AG-UI endpoint for the cooking agent (CopilotKit-compatible).
- Shared state the agent mutates via tools (`scale_recipe`, `substitute_ingredient`, `update_cooking_progress`).

Endpoints, payloads, state shape and setup: see [backend/README.md](backend/README.md).

## What to build

### Must have

- **File upload** — accept a recipe, show something useful while it parses.
- **Chat** — wired to CopilotKit, multi-turn, streaming.
- **Recipe view** — title, time, servings, difficulty, ingredients, steps. Updates live when the agent changes state.
- **Polish** — transitions, loading states, micro-interactions. Make it feel good to use.
- **Easy to run** — one README, one command, no hunting.

### Nice to have

- Graceful fallback on phone (the target is tablet, but don't actively break on smaller screens).
- Voice input — cooking with wet hands is the ideal use case.
- Real error handling — failed uploads, agent errors, network drops.

## How I'll judge it

- **Does it work?** Golden path and a couple of edge cases.
- **Is it well designed?** UI and UX decisions you can explain.
- **Is the code maintainable?** Sensible structure, not clever for its own sake.
- **Can you explain your choices?** I'll ask about tradeoffs. "I chose X over Y because…" goes a long way.
- **Did you make it yours?** Personal touches count.

Use AI assistants freely. I care about outcomes, not keystrokes. See [agents.md](agents.md).

## Get started

### 1. Get a Gemini API key

Use Gemini's free tier. Grab a key at https://aistudio.google.com/apikey (sign in, click **Create API key**, copy it).

Create `backend/.env`:

```env
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your_key_here
```

Values must not be quoted — `docker-compose` passes them literally.

### 2. Run the backend

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

Or with Docker:

```bash
docker-compose up backend
```

OpenAPI at http://localhost:8000/docs.

For state model, CopilotKit wiring and the agent's tools: [backend/README.md](backend/README.md).

### 3. Run the CopilotKit BFF (Node)

```bash
cd runtime
npm install
npm run dev
```

This runs **CopilotRuntime** on Express at `http://localhost:3001`, with `recipe_agent`
implemented as an `HttpAgent` pointing at the Python `/copilotkit` mount (see
[backend/README.md](backend/README.md)). The Vite dev server proxies `/copilotkit` to
that process.

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

## Tips

- Start with the walking skeleton: upload → chat → show recipe. Then iterate.
- The agent mutates state through tools — your UI reacts to state changes, don't parse chat messages.
- Use the `threadId` from `/upload` to keep the session consistent.
- Don't over-engineer. Working and simple beats clever and half-finished.
- Commit often. I'll read the git history.

## Questions

If anything is unclear, email me at tolo.palmer@indegene.com. I'd rather answer a question than have you guess.

Good luck.
