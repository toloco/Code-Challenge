"""Pytest fixtures for backend tests."""

from collections.abc import Generator
from unittest.mock import patch, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models import Recipe, Ingredient, RecipeStep, RecipeContext
from src import agents



@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_recipe() -> Recipe:
    """Sample recipe for testing."""
    return Recipe(
        title="Pasta al Pomodoro",
        description="Simple Italian tomato pasta",
        servings=4,
        prep_time_minutes=10,
        cook_time_minutes=20,
        difficulty="easy",
        cuisine="Italian",
        dietary_tags=["vegetarian"],
        ingredients=[
            Ingredient(name="spaghetti", quantity=400, unit="g", category="pantry"),
            Ingredient(name="olive oil", quantity=3, unit="tbsp", category="pantry"),
            Ingredient(
                name="garlic",
                quantity=3,
                unit="cloves",
                preparation="minced",
                category="produce",
            ),
            Ingredient(
                name="tomatoes",
                quantity=800,
                unit="g",
                preparation="crushed",
                category="produce",
            ),
            Ingredient(name="basil", quantity=1, unit="bunch", category="produce"),
            Ingredient(
                name="parmesan",
                quantity=50,
                unit="g",
                preparation="grated",
                category="dairy",
            ),
        ],
        steps=[
            RecipeStep(
                step_number=1,
                instruction="Boil water and cook pasta",
                duration_minutes=10,
            ),
            RecipeStep(
                step_number=2,
                instruction="Sauté garlic in olive oil",
                duration_minutes=2,
            ),
            RecipeStep(
                step_number=3,
                instruction="Add tomatoes and simmer",
                duration_minutes=15,
            ),
            RecipeStep(
                step_number=4,
                instruction="Combine pasta with sauce, add basil and parmesan",
            ),
        ],
    )


@pytest.fixture
def sample_state(sample_recipe: Recipe) -> RecipeContext:
    """Sample recipe context for testing."""
    return RecipeContext(
        document_text="Original recipe text...",
        recipe=sample_recipe,
        current_step=0,
        scaled_servings=None,
        checked_ingredients=[],
        cooking_started=False,
    )


@pytest.fixture
def mock_parse_recipe() -> Generator[AsyncMock, None, None]:
    """Mock the parse_recipe_from_text function."""
    with patch("src.agents.parse_recipe_from_text") as mock:
        mock.return_value = None  # Default to None, tests can override
        yield mock
