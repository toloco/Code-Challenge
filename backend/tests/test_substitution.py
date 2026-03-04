"""Tests for LLM-based ingredient substitution."""

import pytest
from unittest.mock import patch, AsyncMock

from src.models import Recipe, Ingredient, RecipeStep, SubstitutionResult
from src.agents import find_and_substitute


@pytest.fixture
def recipe_with_roma_tomatoes() -> Recipe:
    """Recipe with 'Roma tomatoes' for fuzzy matching tests."""
    return Recipe(
        title="Tomato Salad",
        servings=4,
        ingredients=[
            Ingredient(
                name="Roma tomatoes", quantity=4, unit="medium", category="produce"
            ),
            Ingredient(name="olive oil", quantity=2, unit="tbsp", category="pantry"),
            Ingredient(
                name="garlic cloves",
                quantity=2,
                unit="cloves",
                preparation="minced",
                category="produce",
            ),
            Ingredient(
                name="fresh basil", quantity=1, unit="bunch", category="produce"
            ),
            Ingredient(
                name="parmesan cheese",
                quantity=50,
                unit="g",
                preparation="shaved",
                category="dairy",
            ),
        ],
        steps=[
            RecipeStep(step_number=1, instruction="Slice tomatoes"),
            RecipeStep(step_number=2, instruction="Arrange and drizzle with oil"),
        ],
    )


class TestSubstitutionResult:
    """Test SubstitutionResult model."""

    def test_create_with_match(self):
        """Can create result with matched ingredient."""
        result = SubstitutionResult(
            matched_ingredient="Roma tomatoes",
            substitute_name="cherry tomatoes",
            substitute_quantity=2.0,
            substitute_unit="cups",
            confidence=0.9,
            cooking_tip="Cherry tomatoes are sweeter, reduce cooking time slightly.",
        )
        assert result.matched_ingredient == "Roma tomatoes"
        assert result.substitute_name == "cherry tomatoes"
        assert result.confidence == 0.9

    def test_create_without_match(self):
        """Can create result without match (suggestion only)."""
        result = SubstitutionResult(
            matched_ingredient=None,
            substitute_name="butter",
            suggestion="No butter in recipe. Did you mean olive oil?",
        )
        assert result.matched_ingredient is None
        assert result.suggestion is not None

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        result = SubstitutionResult(
            substitute_name="test",
            confidence=0.5,
        )
        assert 0 <= result.confidence <= 1


class TestLLMSubstitution:
    """Test LLM-based ingredient substitution."""

    @pytest.mark.asyncio
    async def test_fuzzy_match_tomatoes(self, recipe_with_roma_tomatoes):
        """'tomatoes' should match 'Roma tomatoes' in recipe."""
        # Mock the LLM agent to return expected result
        mock_result = SubstitutionResult(
            matched_ingredient="Roma tomatoes",
            substitute_name="cherry tomatoes",
            substitute_quantity=2.0,
            substitute_unit="cups",
            confidence=0.85,
            cooking_tip="Cherry tomatoes are sweeter and smaller.",
        )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = AsyncMock(output=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "tomatoes", "cherry tomatoes"
            )

            assert result.matched_ingredient == "Roma tomatoes"
            assert result.substitute_name == "cherry tomatoes"
            assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_fuzzy_match_garlic(self, recipe_with_roma_tomatoes):
        """'garlic' should match 'garlic cloves' in recipe."""
        mock_result = SubstitutionResult(
            matched_ingredient="garlic cloves",
            substitute_name="garlic powder",
            substitute_quantity=1.0,
            substitute_unit="tsp",
            confidence=0.9,
            cooking_tip="Use 1/4 tsp powder per clove.",
        )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = AsyncMock(output=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "garlic", "garlic powder"
            )

            assert result.matched_ingredient == "garlic cloves"
            assert result.substitute_name == "garlic powder"

    @pytest.mark.asyncio
    async def test_fuzzy_match_parmesan(self, recipe_with_roma_tomatoes):
        """'parmesan' should match 'parmesan cheese' in recipe."""
        mock_result = SubstitutionResult(
            matched_ingredient="parmesan cheese",
            substitute_name="pecorino romano",
            substitute_quantity=50.0,
            substitute_unit="g",
            confidence=0.95,
            cooking_tip="Pecorino is saltier, you may want to reduce salt.",
        )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = AsyncMock(output=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "parmesan", "pecorino romano"
            )

            assert result.matched_ingredient == "parmesan cheese"
            assert result.substitute_name == "pecorino romano"

    @pytest.mark.asyncio
    async def test_no_match_suggests_alternatives(self, recipe_with_roma_tomatoes):
        """Should suggest alternatives when ingredient not found."""
        mock_result = SubstitutionResult(
            matched_ingredient=None,
            substitute_name="margarine",
            confidence=0.0,
            suggestion="No butter in this recipe. Available fats: olive oil. You could substitute olive oil with margarine if desired.",
        )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = AsyncMock(output=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "butter", "margarine"
            )

            assert result.matched_ingredient is None
            assert result.suggestion is not None
            assert "olive oil" in result.suggestion.lower()

    @pytest.mark.asyncio
    async def test_quantity_adjustment(self, recipe_with_roma_tomatoes):
        """Should suggest appropriate quantity adjustments."""
        mock_result = SubstitutionResult(
            matched_ingredient="olive oil",
            substitute_name="coconut oil",
            substitute_quantity=2.0,  # Same as original
            substitute_unit="tbsp",
            confidence=0.95,
            cooking_tip="Coconut oil adds a slight sweetness.",
        )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = AsyncMock(output=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "olive oil", "coconut oil"
            )

            assert result.matched_ingredient == "olive oil"
            assert result.substitute_quantity == 2.0
            assert result.substitute_unit == "tbsp"

    @pytest.mark.asyncio
    async def test_llm_failure_fallback_exact_match(self, recipe_with_roma_tomatoes):
        """Should fallback to exact match if LLM fails."""
        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = Exception("LLM API error")
            mock_get_agent.return_value = mock_agent

            # Exact match should still work
            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "olive oil", "vegetable oil"
            )

            assert result.matched_ingredient == "olive oil"
            assert result.substitute_name == "vegetable oil"
            assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_llm_failure_no_match(self, recipe_with_roma_tomatoes):
        """Should return no match suggestion if LLM fails and no exact match."""
        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = Exception("LLM API error")
            mock_get_agent.return_value = mock_agent

            result = await find_and_substitute(
                recipe_with_roma_tomatoes, "tomatoes", "cherry tomatoes"
            )

            # Fuzzy match won't work without LLM, so should fail
            assert result.matched_ingredient is None
            assert "tomatoes" in result.suggestion


class TestSubstitutionPromptGeneration:
    """Test the prompt generation for LLM substitution."""

    @pytest.mark.asyncio
    async def test_ingredients_formatted_in_prompt(self, recipe_with_roma_tomatoes):
        """Verify ingredients are properly formatted in the prompt."""
        captured_prompt = None

        async def capture_prompt(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return AsyncMock(
                output=SubstitutionResult(
                    matched_ingredient="Roma tomatoes",
                    substitute_name="cherry tomatoes",
                )
            )

        with patch("src.agents.get_substitution_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run.side_effect = capture_prompt
            mock_get_agent.return_value = mock_agent

            await find_and_substitute(
                recipe_with_roma_tomatoes, "tomatoes", "cherry tomatoes"
            )

            assert captured_prompt is not None
            assert "Roma tomatoes" in captured_prompt
            assert "olive oil" in captured_prompt
            assert "garlic cloves" in captured_prompt
            assert 'replace: "tomatoes"' in captured_prompt
            assert 'With: "cherry tomatoes"' in captured_prompt
