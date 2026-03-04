# 🍳 Recipe Companion Challenge

Build a **cooking companion** frontend that helps users extract recipes from documents 
and guides them through the cooking process.

## The Challenge

You have a working Python backend that:
- Accepts recipe uploads (PDF or text)
- Extracts structured recipe data
- Provides conversational cooking assistance via CopilotKit
- Make it beautiful
- Discover what's been implemented


## Requirements

### Must Have ✅

1. **File Upload**
2. **Chat Interface**
   - Integrate with CopilotKit
   - Display agent responses
   - Handle multi-turn conversations
3. **Recipe Display**
   - Show extracted recipe (title, time, servings, difficulty)
   - List ingredients
   - Show cooking steps
   - Update recipe according to the chat requests
4. **Responsive Design**
   - Works on desktop and mobile
   - Readable, usable layout
5. **Easy to Run**
   - Should be easy to build and run for us


### Nice to Have ✨
6. **Rich UI Components**
   - Animated transitions
   - Progress indicators
   - Delightful micro-interactions
   - Voice input (stretch)
7. **Error Handling**
    - Upload failures
    - Agent errors
    - Network issues


## Getting Started

### Start the Backend

See [backend/README.md](backend/README.md) for setup instructions (API key, environment, running).

You have two options docker or running the python application.

```bash
cd backend
# Install dependencies
uv sync

# Start the server
uv run uvicorn src.main:app --reload --port 8000
```

Or with Docker:

```bash
docker-compose up backend
```


## API Reference
Full specs http://localhost:8000/docs

The backend exposes:
- `POST /upload` - Upload recipe documents
- `POST /copilotkit` - CopilotKit endpoint
- `GET /health` - Health check

### State Model

The agent maintains this state (accessible via `useCoAgent`), you can find a full 
definition at backend/src/models.py.


```typescript
interface RecipeContext {
  document_text: string | null    // Original uploaded text
  recipe: Recipe | null           // Parsed recipe data
  current_step: number            // Current cooking step index
  scaled_servings: number | null  // Servings after scaling
  checked_ingredients: string[]   // Ingredients marked as ready
  cooking_started: boolean        // Whether cooking has begun
}
...
```

## Tips

- **Read the CopilotKit docs** - They have great examples
- **Start with the basics** - Upload → Chat → Display, then iterate
- **The agent modifies state via tools** - Your UI should react to state changes from `useCoAgent`
- **Use `threadId` from upload response** - This identifies the session for state persistence
- **Comment your decisions** - Quick notes on "why" help us understand
- **Don't over-engineer** - Simple and working beats complex and broken
- **Have fun with it** - Recipes are fun, your app should be too!

## Questions?

If you have questions about the requirements, reach out at tolo.palmer@indegene.com . We're happy to clarify—we want you to succeed!

---

Good luck, and happy cooking!
