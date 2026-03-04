# Backend

Recipe Companion API using FastAPI and pydantic-ai.

## Setup

### 1. Get a Free API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy your new API key

### 2. Configure Environment

Create a `.env` file in this directory:

```bash
cat > .env << EOF
GEMINI_API_KEY=your_key_here
LLM_MODEL=gemini-2.0-flash
EOF
```

## Development Commands

```bash
make help             # Show available commands
make format           # Format code with ruff
make lint             # Lint code with ruff
make test             # Run all tests
make test-unit        # Run unit tests only (fast, no API calls)
make test-integration # Run integration tests (real API calls)
```