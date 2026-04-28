import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copilotkit-agui-adapter',
      configureServer(server) {
        server.middlewares.use('/copilotkit', async (req, res, next) => {
          if (req.method !== 'POST') {
            return next()
          }

          let body = ''
          req.on('data', (chunk) => {
            body += chunk
          })

          req.on('end', async () => {
            try {
              const parsed = body ? JSON.parse(body) : {}

              // CopilotKit first sends a lightweight "info" probe to discover agents.
              // The backend AG-UI endpoint does not support that shape
              // Below is the a hard coded response sent, and the if stops it reaching the backend. This avoids the startup 422.
              if (parsed?.method === 'info') {
                res.statusCode = 200
                res.setHeader('Content-Type', 'application/json')
                res.end(
                  JSON.stringify({
                    agents: {
                      recipe_agent: {
                        id: 'recipe_agent',
                        name: 'recipe_agent',
                      },
                    },
                  }),
                )
                return
              }

              // CopilotKit single-endpoint mode wraps the real AG-UI payload inside
              // { method: "agent/run", body: { ... } }.
              //
              // The backend expects the inner body directly:
              // { threadId, runId, state, messages, tools, context, forwardedProps }
              //
              // So we pull the nested `body` out here.
              const bodyPayload =
                parsed && typeof parsed === 'object' && parsed.body && typeof parsed.body === 'object'
                  ? (parsed.body as Record<string, unknown>)
                  : (parsed as Record<string, unknown>)

              // Normalise the data by building a flat AG-UI request the backend can validate. We also provide
              // safe fallbacks for local dev/mock sessions so the adapter does not
              // forward an incomplete payload that would trigger another 422.
              const payload =
                parsed?.method === 'agent/run'
                  ? {
                    threadId:
                      (bodyPayload.threadId as string | undefined) ??
                      (parsed.threadId as string | undefined) ??
                      'dev-thread-local',
                    runId:
                      (bodyPayload.runId as string | undefined) ??
                      (parsed.runId as string | undefined) ??
                      `dev-run-${Date.now()}`,
                    state:
                      (bodyPayload.state as Record<string, unknown> | undefined) ??
                      (parsed.state as Record<string, unknown> | undefined) ??
                      {},
                    messages:
                      (bodyPayload.messages as unknown[] | undefined) ??
                      (parsed.messages as unknown[] | undefined) ??
                      [],
                    tools:
                      (bodyPayload.tools as unknown[] | undefined) ??
                      (parsed.tools as unknown[] | undefined) ??
                      [],
                    context:
                      (bodyPayload.context as unknown[] | undefined) ??
                      (parsed.context as unknown[] | undefined) ??
                      [],
                    forwardedProps:
                      (bodyPayload.forwardedProps as Record<string, unknown> | undefined) ??
                      (parsed.forwardedProps as Record<string, unknown> | undefined) ??
                      {},
                  }
                  : bodyPayload

              // Forward the normalised payload to the real backend endpoint.
              const upstream = await fetch('http://localhost:8000/copilotkit/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  Accept: req.headers.accept ?? '*/*',
                },
                body: JSON.stringify(payload),
              })

              res.statusCode = upstream.status
              const contentType = upstream.headers.get('content-type')
              if (contentType) {
                res.setHeader('Content-Type', contentType)
              }

              const text = await upstream.text()
              res.end(text)
            } catch (error) {
              res.statusCode = 502
              res.setHeader('Content-Type', 'application/json')
              res.end(
                JSON.stringify({
                  error: 'CopilotKit adapter failed',
                  detail: error instanceof Error ? error.message : String(error),
                }),
              )
            }
          })
        })
      },
    },
  ],
})
