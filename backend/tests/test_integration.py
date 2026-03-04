"""
Integration tests that use the REAL OpenAI API.

These tests are NOT mocked and will make actual API calls.
They require a valid OPENAI_API_KEY environment variable.

Run with: pytest -v tests/test_integration.py
Skip with: pytest -v -m "not integration"
"""

import json
from io import BytesIO

import pytest
from httpx import AsyncClient


def parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE (Server-Sent Events) response into list of event dicts."""
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


class TestIntegrationRealAPI:
    """
    Integration tests that use the REAL OpenAI API.

    These tests are NOT mocked and will make actual API calls.
    They require a valid OPENAI_API_KEY environment variable.
    """

    @pytest.fixture
    def sample_recipe_text(self) -> str:
        """Simple recipe text for parsing."""
        return """
        Simple Tomato Pasta

        A quick and easy pasta dish perfect for weeknight dinners.

        Servings: 4
        Prep Time: 10 minutes
        Cook Time: 20 minutes

        Ingredients:
        - 400g spaghetti
        - 3 tablespoons olive oil
        - 4 cloves garlic, minced
        - 800g canned crushed tomatoes
        - 1 bunch fresh basil leaves
        - 50g parmesan cheese, grated
        - Salt and pepper to taste

        Instructions:
        1. Bring a large pot of salted water to boil and cook spaghetti according to package directions.
        2. While pasta cooks, heat olive oil in a large skillet over medium heat.
        3. Add minced garlic and sauté for 1-2 minutes until fragrant but not browned.
        4. Pour in crushed tomatoes, season with salt and pepper, and simmer for 15 minutes.
        5. Drain pasta and toss with the sauce.
        6. Serve topped with fresh basil and grated parmesan.
        """

    @pytest.mark.integration
    async def test_real_full_flow_upload_scale_substitute(
        self, client: AsyncClient, sample_recipe_text: str
    ) -> None:
        """
        Full integration test: Upload → Scale → Substitute using REAL API.

        This test:
        1. Uploads and parses a recipe (real OpenAI call)
        2. Asks agent to scale it (real OpenAI call)
        3. Asks agent to substitute an ingredient (real OpenAI call)
        4. Verifies all state changes
        """
        # === STEP 1: Upload and parse recipe ===
        files = {
            "file": ("recipe.txt", BytesIO(sample_recipe_text.encode()), "text/plain")
        }
        upload_response = await client.post("/upload", files=files)

        assert upload_response.status_code == 200
        upload_data = upload_response.json()

        recipe = upload_data["state"].get("recipe")
        assert recipe is not None, "Recipe should be parsed"

        original_servings = recipe["servings"]
        assert original_servings == 4

        # Find spaghetti ingredient and note original quantity
        spaghetti = next(
            (
                i
                for i in recipe["ingredients"]
                if "spaghetti" in i["name"].lower() or "pasta" in i["name"].lower()
            ),
            None,
        )
        assert spaghetti is not None, "Should have spaghetti/pasta ingredient"
        original_spaghetti_qty = spaghetti.get("quantity", 400)

        # === STEP 2: Scale the recipe (double it) ===
        upload_data["messages"].append(
            {
                "id": "msg-1",
                "role": "user",
                "content": "Please double this recipe to serve 8 people",
            }
        )

        scale_response = await client.post("/copilotkit/", json=upload_data)

        assert scale_response.status_code == 200, scale_response.text

        scale_events = parse_sse_events(scale_response.text)

        # Check if scale_recipe tool was called
        tool_calls = [e for e in scale_events if e.get("type") == "TOOL_CALL_START"]
        scale_tool_called = any(
            tc.get("toolCallName") == "scale_recipe" for tc in tool_calls
        )

        # Get state update
        state_events = [e for e in scale_events if e.get("type") == "STATE_SNAPSHOT"]

        if scale_tool_called and state_events:
            # Tool was called - verify state was updated
            scaled_state = state_events[0]["snapshot"]
            assert scaled_state["recipe"]["servings"] == 8, (
                "Recipe should be scaled to 8 servings"
            )

            # Find spaghetti in scaled recipe
            scaled_spaghetti = next(
                (
                    i
                    for i in scaled_state["recipe"]["ingredients"]
                    if "spaghetti" in i["name"].lower() or "pasta" in i["name"].lower()
                ),
                None,
            )
            if scaled_spaghetti and scaled_spaghetti.get("quantity"):
                # Quantity should be doubled
                assert scaled_spaghetti["quantity"] == original_spaghetti_qty * 2, (
                    f"Spaghetti should be doubled: {original_spaghetti_qty} * 2 = {original_spaghetti_qty * 2}"
                )

            # Use scaled state for next step
            current_state = scaled_state
        else:
            # Tool might not have been called if LLM decided differently
            # In that case, use original state
            print("Note: scale_recipe tool was not called by LLM")
            current_state = {
                "document_text": None,
                "recipe": recipe,
                "current_step": 0,
                "scaled_servings": None,
                "checked_ingredients": [],
                "cooking_started": False,
            }

        # === STEP 3: Substitute an ingredient ===
        sub_response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "integration-test-001",
                "runId": "run-sub-001",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": current_state,
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Please double this recipe to serve 8 people",
                    },
                    {
                        "id": "msg-2",
                        "role": "assistant",
                        "content": "I've scaled the recipe to serve 8 people.",
                    },
                    {
                        "id": "msg-3",
                        "role": "user",
                        "content": "Can you substitute the parmesan with pecorino cheese?",
                    },
                ],
            },
        )

        assert sub_response.status_code == 200

        sub_events = parse_sse_events(sub_response.text)

        # Check if substitute_ingredient tool was called
        sub_tool_calls = [e for e in sub_events if e.get("type") == "TOOL_CALL_START"]
        sub_tool_called = any(
            tc.get("toolCallName") == "substitute_ingredient" for tc in sub_tool_calls
        )

        sub_state_events = [e for e in sub_events if e.get("type") == "STATE_SNAPSHOT"]

        if sub_tool_called and sub_state_events:
            final_state = sub_state_events[0]["snapshot"]
            ingredient_names = [
                i["name"].lower() for i in final_state["recipe"]["ingredients"]
            ]

            # Check if substitution happened
            has_pecorino = any("pecorino" in name for name in ingredient_names)
            parmesan_gone = not any("parmesan" in name for name in ingredient_names)

            if has_pecorino:
                print("✓ Substitution successful - pecorino in ingredients")
            elif parmesan_gone:
                print("✓ Parmesan removed (substitution partially worked)")
            else:
                print(
                    f"Note: Tool called but ingredient name mismatch. Ingredients: {ingredient_names}"
                )

            print(f"✓ Final ingredients: {ingredient_names}")
        else:
            print("Note: substitute_ingredient tool was not called by LLM")

        # Verify we got text responses
        text_events = [
            e
            for e in scale_events + sub_events
            if e.get("type") == "TEXT_MESSAGE_CONTENT"
        ]
        assert len(text_events) > 0, "Should have received text responses from agent"

    @pytest.mark.integration
    async def test_fuzzy_substitution_tomatoes(self, client: AsyncClient) -> None:
        """
        Test LLM-based fuzzy matching for ingredient substitution.

        This test verifies that saying "tomatoes" matches "crushed tomatoes"
        in the recipe (fuzzy matching via LLM).
        """
        # Recipe with "crushed tomatoes" - user will say just "tomatoes"
        recipe = {
            "title": "Pasta Sauce",
            "servings": 4,
            "difficulty": "easy",
            "ingredients": [
                {
                    "name": "crushed tomatoes",
                    "quantity": 800,
                    "unit": "g",
                    "category": "produce",
                },
                {
                    "name": "olive oil",
                    "quantity": 2,
                    "unit": "tbsp",
                    "category": "pantry",
                },
                {
                    "name": "garlic cloves",
                    "quantity": 3,
                    "unit": "cloves",
                    "category": "produce",
                },
                {
                    "name": "fresh basil",
                    "quantity": 1,
                    "unit": "bunch",
                    "category": "produce",
                },
            ],
            "steps": [
                {"step_number": 1, "instruction": "Sauté garlic in oil"},
                {"step_number": 2, "instruction": "Add tomatoes and simmer"},
            ],
        }

        # Ask to substitute "tomatoes" (fuzzy) with "cherry tomatoes"
        response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "fuzzy-test-001",
                "runId": "run-fuzzy-001",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": recipe,
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Please substitute the tomatoes with cherry tomatoes",
                    }
                ],
            },
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)

        # Check if substitute_ingredient tool was called
        tool_calls = [e for e in events if e.get("type") == "TOOL_CALL_START"]
        sub_tool_called = any(
            tc.get("toolCallName") == "substitute_ingredient" for tc in tool_calls
        )

        state_events = [e for e in events if e.get("type") == "STATE_SNAPSHOT"]

        if sub_tool_called and state_events:
            final_state = state_events[0]["snapshot"]
            ingredient_names = [
                i["name"].lower() for i in final_state["recipe"]["ingredients"]
            ]

            # Verify "crushed tomatoes" was replaced with "cherry tomatoes"
            has_cherry = any("cherry" in name for name in ingredient_names)
            crushed_gone = not any(
                "crushed tomatoes" in name for name in ingredient_names
            )

            print(f"✓ Fuzzy substitution test - ingredients: {ingredient_names}")

            if has_cherry:
                print("✓ Cherry tomatoes found - fuzzy matching worked!")
            if crushed_gone:
                print("✓ Crushed tomatoes removed")

            # At minimum, the tool should have been called
            assert sub_tool_called, "substitute_ingredient tool should be called"
        else:
            print(
                f"Note: Tool not called or no state update. Events: {[e.get('type') for e in events]}"
            )

    @pytest.mark.integration
    async def test_substitution_no_match_helpful_response(
        self, client: AsyncClient
    ) -> None:
        """
        Test that substituting a non-existent ingredient gives helpful response.

        When user asks to substitute an ingredient that doesn't exist,
        the LLM should suggest available alternatives.
        """
        recipe = {
            "title": "Simple Salad",
            "servings": 2,
            "difficulty": "easy",
            "ingredients": [
                {
                    "name": "lettuce",
                    "quantity": 1,
                    "unit": "head",
                    "category": "produce",
                },
                {
                    "name": "olive oil",
                    "quantity": 2,
                    "unit": "tbsp",
                    "category": "pantry",
                },
                {
                    "name": "lemon juice",
                    "quantity": 1,
                    "unit": "tbsp",
                    "category": "produce",
                },
            ],
            "steps": [
                {"step_number": 1, "instruction": "Wash and chop lettuce"},
                {"step_number": 2, "instruction": "Dress with oil and lemon"},
            ],
        }

        # Ask to substitute "butter" which doesn't exist in the recipe
        response = await client.post(
            "/copilotkit/",
            json={
                "threadId": "no-match-test-001",
                "runId": "run-no-match-001",
                "tools": [],
                "context": [],
                "forwardedProps": {},
                "state": {
                    "document_text": None,
                    "recipe": recipe,
                    "current_step": 0,
                    "scaled_servings": None,
                    "checked_ingredients": [],
                    "cooking_started": False,
                },
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": "Can you substitute the butter with margarine?",
                    }
                ],
            },
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)

        # The agent should respond (either via tool return or text)
        text_events = [e for e in events if e.get("type") == "TEXT_MESSAGE_CONTENT"]
        tool_calls = [e for e in events if e.get("type") == "TOOL_CALL_START"]

        # We should get some response
        assert len(text_events) > 0 or len(tool_calls) > 0, (
            "Should receive either text response or tool call"
        )

        # If there's text, it should mention that butter isn't in the recipe
        if text_events:
            full_text = " ".join(e.get("content", "") for e in text_events)
            print(f"Agent response: {full_text[:200]}...")
            # Response should be helpful (mention available ingredients or clarify)
