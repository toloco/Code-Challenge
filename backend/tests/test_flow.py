"""Tests for the Recipe Companion backend.

Tests cover:
- Upload endpoint
- Recipe model methods (scale, substitute)
- CopilotKit endpoints
"""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.models import Recipe, Ingredient, RecipeStep, RecipeContext


class TestUploadEndpoint:
    """Tests for POST /upload endpoint."""

    async def test_upload_returns_parsed_recipe(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """Verify upload returns parsed recipe when parsing succeeds."""
        content = b"Pasta al Pomodoro recipe text..."
        files = {"file": ("pasta.txt", BytesIO(content), "text/plain")}

        with patch(
            "src.main.parse_recipe_from_text", new_callable=AsyncMock
        ) as mock_parse:
            mock_parse.return_value = sample_recipe

            response = await client.post("/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["state"]["recipe"] is not None
        assert "Pasta al Pomodoro" in data["state"]["document_text"]
        assert data["state"]["recipe"]["title"] == "Pasta al Pomodoro"
        assert data["state"]["recipe"]["servings"] == 4
        assert len(data["state"]["recipe"]["ingredients"]) == 6
        assert data["threadId"] is not None


class TestCopilotKitEndpoints:
    """Tests for CopilotKit AG-UI endpoints.

    Request format based on CopilotKit curl:
    POST /copilotkit/ with body containing:
    - threadId, runId: identifiers
    - tools, context, forwardedProps: CopilotKit SDK fields
    - state: RecipeContext state object
    - messages: list of {id, role, content}
    """

    async def test_agent_run_streams_response(self, client: AsyncClient) -> None:
        """Test /copilotkit agent run returns streaming response."""
        with patch("src.agents.GoogleModel") as mock_openai:
            # Mock streaming response
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            async def mock_stream():
                class MockChoice:
                    class MockDelta:
                        content = "Hello!"
                        tool_calls = None

                    delta = MockDelta()

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_response = AsyncMock()
            mock_response.__aiter__ = mock_stream
            mock_client.chat.completions.create.return_value = mock_response

            response = await client.post(
                "/copilotkit/",
                json={
                    "threadId": "test-123",
                    "runId": "test-run-123",
                    "tools": [],
                    "context": [],
                    "forwardedProps": {},
                    "state": {
                        "document_text": None,
                        "recipe": None,
                        "current_step": 0,
                        "scaled_servings": None,
                        "checked_ingredients": [],
                        "cooking_started": False,
                    },
                    "messages": [{"id": "msg-1", "role": "user", "content": "Hello"}],
                },
            )

        # Should return streaming response
        assert response.status_code == 200

    async def test_agent_run_with_recipe_state(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """Test /copilotkit agent run with recipe in state."""
        with patch("src.agents.GoogleModel") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            async def mock_stream():
                class MockChoice:
                    class MockDelta:
                        content = "I see your recipe!"
                        tool_calls = None

                    delta = MockDelta()

                class MockChunk:
                    choices = [MockChoice()]

                yield MockChunk()

            mock_response = AsyncMock()
            mock_response.__aiter__ = mock_stream
            mock_client.chat.completions.create.return_value = mock_response

            response = await client.post(
                "/copilotkit/",
                json={
                    "threadId": "test-456",
                    "runId": "test-run-456",
                    "tools": [],
                    "context": [],
                    "forwardedProps": {},
                    "state": {
                        "document_text": None,
                        "recipe": sample_recipe.model_dump(),
                        "current_step": 0,
                        "scaled_servings": None,
                        "checked_ingredients": [],
                        "cooking_started": False,
                    },
                    "messages": [
                        {
                            "id": "msg-1",
                            "role": "user",
                            "content": "What recipe is this?",
                        }
                    ],
                },
            )

        assert response.status_code == 200


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE (Server-Sent Events) response into list of event dicts."""
    import json

    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            json_str = line[6:]  # Remove "data: " prefix
            try:
                events.append(json.loads(json_str))
            except json.JSONDecodeError:
                continue
        elif line and not line.startswith(":"):
            # Try parsing as plain JSON (fallback)
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


class TestToolCalling:
    """Tests for agent tool calling behavior.

    These tests use real API calls to verify:
    1. The agent calls tools when user requests changes
    2. Tools modify the recipe state correctly
    3. STATE_SNAPSHOT events are emitted with updated state

    Note: These tests make real OpenAI API calls because the pydantic-ai
    agent is created at module load time, making mocking difficult.
    """

    @pytest.mark.integration
    async def test_substitute_ingredient_tool_is_called(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """
        When user asks to substitute an ingredient, the agent should:
        1. Call the substitute_ingredient tool
        2. Emit a STATE_SNAPSHOT with the modified recipe
        """
        response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "test-tool-call",
                "runId": "run-tool-call",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": sample_recipe.model_dump(),
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Please substitute parmesan with pecorino",
                    }
                ],
            },
        )

        assert response.status_code == 200

        events = parse_sse_events(response.text)
        event_types = [e.get("type") for e in events]

        # Verify tool was called and state was updated
        assert "TOOL_CALL_START" in event_types, "Tool should be called"
        assert "STATE_SNAPSHOT" in event_types, "State should be updated"

        # Find the state snapshot event
        state_event = next(e for e in events if e.get("type") == "STATE_SNAPSHOT")
        snapshot = state_event["snapshot"]

        # Verify the substitution was made
        ingredient_names = [i["name"] for i in snapshot["recipe"]["ingredients"]]
        assert "parmesan" not in ingredient_names, "parmesan should be replaced"
        assert "pecorino" in ingredient_names, "pecorino should be added"

    @pytest.mark.integration
    async def test_scale_recipe_tool_is_called(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """
        When user asks to scale a recipe, the agent should:
        1. Call the scale_recipe tool
        2. Emit a STATE_SNAPSHOT with scaled quantities
        """
        response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "test-scale",
                "runId": "run-scale",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": sample_recipe.model_dump(),
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Double the recipe please",
                    }
                ],
            },
        )

        assert response.status_code == 200

        events = parse_sse_events(response.text)
        event_types = [e.get("type") for e in events]

        # Verify tool was called
        assert "TOOL_CALL_START" in event_types

        # Verify it was the scale_recipe tool
        tool_start = next(e for e in events if e.get("type") == "TOOL_CALL_START")
        assert tool_start["toolCallName"] == "scale_recipe"

        # Verify state snapshot event was emitted
        assert "STATE_SNAPSHOT" in event_types
        state_event = next(e for e in events if e.get("type") == "STATE_SNAPSHOT")
        snapshot = state_event["snapshot"]

        # The recipe should be scaled to 8 servings
        assert snapshot["recipe"]["servings"] == 8
        assert snapshot["scaled_servings"] == 8

        # Ingredient quantities should be doubled (original was 4 servings)
        spaghetti = next(
            i for i in snapshot["recipe"]["ingredients"] if i["name"] == "spaghetti"
        )
        assert spaghetti["quantity"] == 800  # Was 400g, now doubled


class TestRecipeScaling:
    """Tests for Recipe.scale() method."""

    def test_scale_doubles_servings(self, sample_recipe: Recipe) -> None:
        """Scaling to double servings doubles ingredient quantities."""
        scaled = sample_recipe.scale(8)

        assert scaled.servings == 8
        assert scaled.original_servings == 4

        # Check specific ingredients
        spaghetti = next(i for i in scaled.ingredients if i.name == "spaghetti")
        assert spaghetti.quantity == 800  # 400 * 2

        garlic = next(i for i in scaled.ingredients if i.name == "garlic")
        assert garlic.quantity == 6  # 3 * 2

    def test_scale_halves_servings(self, sample_recipe: Recipe) -> None:
        """Scaling to half servings halves ingredient quantities."""
        scaled = sample_recipe.scale(2)

        assert scaled.servings == 2
        assert scaled.original_servings == 4

        spaghetti = next(i for i in scaled.ingredients if i.name == "spaghetti")
        assert spaghetti.quantity == 200  # 400 / 2

    def test_scale_preserves_original(self, sample_recipe: Recipe) -> None:
        """Scaling preserves original_servings through multiple scales."""
        scaled_once = sample_recipe.scale(8)
        scaled_twice = scaled_once.scale(4)

        assert scaled_twice.servings == 4
        assert scaled_twice.original_servings == 4  # Original preserved

    def test_scale_to_same_servings_returns_self(self, sample_recipe: Recipe) -> None:
        """Scaling to same servings returns the same recipe."""
        scaled = sample_recipe.scale(4)

        assert scaled is sample_recipe  # Same object

    def test_scale_handles_none_quantity(self) -> None:
        """Scaling handles ingredients with None quantity."""
        recipe = Recipe(
            title="Test",
            servings=2,
            ingredients=[
                Ingredient(
                    name="salt", quantity=None, unit="to taste", category="spice"
                ),
                Ingredient(name="flour", quantity=100, unit="g", category="pantry"),
            ],
            steps=[RecipeStep(step_number=1, instruction="Mix")],
        )

        scaled = recipe.scale(4)

        salt = next(i for i in scaled.ingredients if i.name == "salt")
        assert salt.quantity is None  # Still None

        flour = next(i for i in scaled.ingredients if i.name == "flour")
        assert flour.quantity == 200


class TestRecipeSubstitution:
    """Tests for Recipe.substitute_ingredient() method."""

    def test_substitute_replaces_ingredient(self, sample_recipe: Recipe) -> None:
        """Substitution replaces ingredient by name."""
        modified = sample_recipe.substitute_ingredient(
            original_name="parmesan",
            substitute_name="pecorino romano",
        )

        names = [i.name for i in modified.ingredients]
        assert "parmesan" not in names
        assert "pecorino romano" in names

        # Quantity should be preserved
        pecorino = next(i for i in modified.ingredients if i.name == "pecorino romano")
        assert pecorino.quantity == 50
        assert pecorino.unit == "g"

    def test_substitute_with_new_quantity(self, sample_recipe: Recipe) -> None:
        """Substitution can change quantity and unit."""
        modified = sample_recipe.substitute_ingredient(
            original_name="olive oil",
            substitute_name="butter",
            substitute_quantity=4,
            substitute_unit="tbsp",
        )

        butter = next(i for i in modified.ingredients if i.name == "butter")
        assert butter.quantity == 4
        assert butter.unit == "tbsp"

    def test_substitute_case_insensitive(self, sample_recipe: Recipe) -> None:
        """Substitution is case-insensitive."""
        modified = sample_recipe.substitute_ingredient(
            original_name="GARLIC",
            substitute_name="shallots",
        )

        names = [i.name for i in modified.ingredients]
        assert "garlic" not in names
        assert "shallots" in names

    def test_substitute_nonexistent_does_nothing(self, sample_recipe: Recipe) -> None:
        """Substituting nonexistent ingredient returns unchanged recipe."""
        original_names = [i.name for i in sample_recipe.ingredients]

        modified = sample_recipe.substitute_ingredient(
            original_name="unicorn tears",
            substitute_name="water",
        )

        modified_names = [i.name for i in modified.ingredients]
        assert original_names == modified_names


class TestRecipeContext:
    """Tests for RecipeContext model."""

    def test_default_values(self) -> None:
        """RecipeContext has sensible defaults."""
        ctx = RecipeContext()

        assert ctx.document_text is None
        assert ctx.recipe is None
        assert ctx.current_step == 0
        assert ctx.scaled_servings is None
        assert ctx.checked_ingredients == []
        assert ctx.cooking_started is False

    def test_model_dump_serialization(self, sample_state: RecipeContext) -> None:
        """RecipeContext serializes properly for CopilotKit."""
        data = sample_state.model_dump()

        assert "document_text" in data
        assert "recipe" in data
        assert "current_step" in data
        assert data["recipe"]["title"] == "Pasta al Pomodoro"


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health endpoint returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "recipe-companion"


class TestFullRecipeFlow:
    """
    End-to-end flow tests for the Recipe Companion.

    These tests simulate a complete user journey using real API calls:
    1. Scale the recipe
    2. Substitute ingredients
    3. Verify state changes propagate correctly

    Note: These tests make real OpenAI API calls because the pydantic-ai
    agent is created at module load time, making mocking difficult.
    """

    @pytest.mark.integration
    async def test_full_flow_scale_then_substitute(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """
        Complete flow test: Scale → Substitute → Verify.

        This test simulates a real user session where they:
        1. Start with a parsed recipe (4 servings)
        2. Ask to double the recipe (8 servings)
        3. Ask to substitute parmesan with pecorino
        4. Verify all changes are reflected in the state
        """
        # === STEP 1: Scale the recipe (double it) ===
        scale_response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "flow-test-001",
                "runId": "run-scale-001",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": sample_recipe.model_dump(),
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Double the recipe please",
                    }
                ],
            },
        )

        assert scale_response.status_code == 200

        scale_events = parse_sse_events(scale_response.text)
        scale_event_types = [e.get("type") for e in scale_events]

        # Verify scale tool was called
        assert "TOOL_CALL_START" in scale_event_types
        scale_tool_calls = [
            e for e in scale_events if e.get("type") == "TOOL_CALL_START"
        ]
        assert scale_tool_calls[0]["toolCallName"] == "scale_recipe"

        # Verify state was updated
        assert "STATE_SNAPSHOT" in scale_event_types
        state_event = next(e for e in scale_events if e.get("type") == "STATE_SNAPSHOT")
        scaled_state = state_event["snapshot"]

        assert scaled_state["recipe"]["servings"] == 8
        assert scaled_state["scaled_servings"] == 8

        # Verify ingredients were doubled
        spaghetti = next(
            i for i in scaled_state["recipe"]["ingredients"] if i["name"] == "spaghetti"
        )
        assert spaghetti["quantity"] == 800  # Was 400, now 800

        garlic = next(
            i for i in scaled_state["recipe"]["ingredients"] if i["name"] == "garlic"
        )
        assert garlic["quantity"] == 6  # Was 3, now 6

        # === STEP 2: Substitute an ingredient ===
        sub_response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "flow-test-001",
                "runId": "run-sub-001",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": scaled_state,  # Use state from previous step
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Double the recipe please",
                    },
                    {
                        "id": "msg-2",
                        "role": "assistant",
                        "content": "I've doubled the recipe to serve 8 people.",
                    },
                    {
                        "id": "msg-3",
                        "role": "user",
                        "content": "Can you substitute parmesan with pecorino romano?",
                    },
                ],
            },
        )

        assert sub_response.status_code == 200

        sub_events = parse_sse_events(sub_response.text)
        sub_event_types = [e.get("type") for e in sub_events]

        # Verify substitute tool was called
        assert "TOOL_CALL_START" in sub_event_types
        sub_tool_calls = [e for e in sub_events if e.get("type") == "TOOL_CALL_START"]
        assert sub_tool_calls[0]["toolCallName"] == "substitute_ingredient"

        # Verify state was updated
        assert "STATE_SNAPSHOT" in sub_event_types
        final_state_event = next(
            e for e in sub_events if e.get("type") == "STATE_SNAPSHOT"
        )
        final_state = final_state_event["snapshot"]

        # Verify parmesan was replaced with pecorino
        ingredient_names = [i["name"] for i in final_state["recipe"]["ingredients"]]
        assert "parmesan" not in ingredient_names
        assert any("pecorino" in name.lower() for name in ingredient_names)

        # Recipe should still be at 8 servings
        assert final_state["recipe"]["servings"] == 8

    @pytest.mark.integration
    async def test_flow_scale_then_scale_again(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """
        Test multiple scaling operations in sequence.

        Verifies that:
        1. First scale (4 → 8 servings) works
        2. Second scale (8 → 2 servings) works
        3. Original servings is preserved throughout
        """
        # First scale: 4 → 8
        resp1 = await client.post(
            "/copilotkit/",
            json={
                "threadId": "scale-test",
                "runId": "run-scale-1",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": sample_recipe.model_dump(),
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Double it to 8 servings",
                    }
                ],
            },
        )

        assert resp1.status_code == 200
        events1 = parse_sse_events(resp1.text)

        state1_event = next(e for e in events1 if e.get("type") == "STATE_SNAPSHOT")
        state1 = state1_event["snapshot"]

        assert state1["recipe"]["servings"] == 8
        assert state1["recipe"]["original_servings"] == 4

        # Second scale: 8 → 2
        resp2 = await client.post(
            "/copilotkit/",
            json={
                "threadId": "scale-test",
                "runId": "run-scale-2",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": state1,
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Actually make it for 2 people",
                    }
                ],
            },
        )

        assert resp2.status_code == 200
        events2 = parse_sse_events(resp2.text)

        state2_event = next(e for e in events2 if e.get("type") == "STATE_SNAPSHOT")
        state2 = state2_event["snapshot"]

        assert state2["recipe"]["servings"] == 2
        assert state2["recipe"]["original_servings"] == 4  # Still preserved

        # Verify ingredients scaled correctly (original 400g / 2 = 200g)
        spaghetti = next(
            i for i in state2["recipe"]["ingredients"] if i["name"] == "spaghetti"
        )
        assert spaghetti["quantity"] == 200

    @pytest.mark.integration
    async def test_flow_multiple_substitutions(
        self, client: AsyncClient, sample_recipe: Recipe
    ) -> None:
        """
        Test multiple ingredient substitutions in sequence.

        Verifies that:
        1. First substitution works
        2. Second substitution works
        3. Both changes are reflected in final state
        """
        # First substitution: parmesan → pecorino
        resp1 = await client.post(
            "/copilotkit/",
            json={
                "threadId": "sub-test",
                "runId": "run-sub-1",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": sample_recipe.model_dump(),
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Replace parmesan with pecorino",
                    }
                ],
            },
        )

        assert resp1.status_code == 200
        events1 = parse_sse_events(resp1.text)

        state1_event = next(e for e in events1 if e.get("type") == "STATE_SNAPSHOT")
        state1 = state1_event["snapshot"]

        names1 = [i["name"] for i in state1["recipe"]["ingredients"]]
        assert "parmesan" not in names1
        assert "pecorino" in names1

        # Second substitution: olive oil → butter
        resp2 = await client.post(
            "/copilotkit/",
            json={
                "threadId": "sub-test",
                "runId": "run-sub-2",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": state1,
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "And replace olive oil with butter",
                    }
                ],
            },
        )

        assert resp2.status_code == 200
        events2 = parse_sse_events(resp2.text)

        state2_event = next(e for e in events2 if e.get("type") == "STATE_SNAPSHOT")
        state2 = state2_event["snapshot"]

        # Verify both substitutions are in final state
        names2 = [i["name"] for i in state2["recipe"]["ingredients"]]
        assert "parmesan" not in names2
        assert "pecorino" in names2
        assert "olive oil" not in names2
        assert "butter" in names2

    @pytest.mark.integration
    async def test_flow_no_recipe_loaded(self, client: AsyncClient) -> None:
        """
        Test that agent handles missing recipe gracefully.

        When user asks to modify a recipe but none is loaded,
        the agent should respond appropriately (may or may not call tools).
        """
        response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "no-recipe-test",
                "runId": "run-no-recipe",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": None,
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {"id": "msg-1", "role": "user", "content": "Double the recipe"}
                ],
            },
        )

        assert response.status_code == 200

        events = parse_sse_events(response.text)
        event_types = [e.get("type") for e in events]

        # Should complete the run (may or may not call tools)
        assert "RUN_STARTED" in event_types
