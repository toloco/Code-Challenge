import 'reflect-metadata'
import express from 'express'
import { CopilotRuntime } from '@copilotkit/runtime/v2'
import { createCopilotExpressHandler } from '@copilotkit/runtime/v2/express'
import { HttpAgent } from '@ag-ui/client'

const app = express()

const port = Number(process.env.PORT ?? 3001)
const upstreamBase = (process.env.PYTHON_BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const pythonAgUiUrl = `${upstreamBase}/copilotkit`

const runtime = new CopilotRuntime({
  agents: {
    recipe_agent: new HttpAgent({ url: pythonAgUiUrl }),
  },
})

app.get('/health', (_req, res) => {
  res.status(200).json({ ok: true, service: 'recipe-copilot-bff' })
})

app.use(
  createCopilotExpressHandler({
    runtime,
    basePath: '/copilotkit',
    mode: 'single-route',
    cors: true,
  }),
)

app.listen(port, () => {
  console.log(`CopilotRuntime (BFF) on http://localhost:${port}`)
  console.log(`Agents → Python AG-UI at ${pythonAgUiUrl}`)
})
