"""
Recipe Companion API - FastAPI Application

Main entry point with routes and CopilotKit integration.
"""

from __future__ import annotations

import logging
import uuid
from io import BytesIO
from typing import Any

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from pydantic_ai.ag_ui import StateDeps

from .models import RecipeContext
from .agents import recipe_agent, parse_recipe_from_text

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="Recipe Companion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# File Upload Endpoint
# =============================================================================
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Upload a recipe document (PDF or text), parse it, and return the parsed recipe.

    The frontend stores the recipe in CopilotKit state via useCoAgent.
    """
    content = await file.read()
    filename = file.filename or ""

    # Extract text based on file type
    if filename.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = content.decode("utf-8", errors="ignore")

    # Parse recipe using pydantic-ai
    recipe = await parse_recipe_from_text(text)
    # # Include parsed recipe if available
    # if not recipe:
    #     raise Exception()

    # Build response - frontend stores this in state
    response: dict[str, Any] = {
        "threadId": str(uuid.uuid4()),
        "runId": str(uuid.uuid4()),
        "state": RecipeContext(document_text=text, recipe=recipe),
        "tools": [],
        "context": [],
        "forwardedProps": {},
        "messages": [],
    }

    return response


# =============================================================================
# AG-UI Integration (pydantic-ai)
# =============================================================================

# Create AG-UI app from the recipe agent and mount it
ag_ui_app = recipe_agent.to_ag_ui(deps=StateDeps(RecipeContext()))
app.mount("/copilotkit", ag_ui_app)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "recipe-companion"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
