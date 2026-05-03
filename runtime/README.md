# CopilotKit BFF (Node)

Small Express layer running **CopilotRuntime** in front of the Python AG-UI service, matching the stack described in `backend/README.md`.

## What it does

- Listens on `http://localhost:3001` (override with `PORT`)
- Serves CopilotKit **single-route** traffic under `/copilotkit`
- Registers `recipe_agent` as an **HttpAgent** pointing at the FastAPI mount: `{PYTHON_BACKEND_URL}/copilotkit`
- Exposes `GET /health` for smoke checks

## Run

```bash
cd runtime
npm install
npm run dev
```

Optional env vars:

- `PORT` (default `3001`)
- `PYTHON_BACKEND_URL` (default `http://localhost:8000`)

The Vite dev server proxies `/copilotkit` to this process (`VITE_BFF_URL` defaults to `http://localhost:3001`).
