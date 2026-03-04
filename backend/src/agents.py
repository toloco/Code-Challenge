"""
Recipe Companion Agent using pydantic-ai with AG-UI integration.

Uses pydantic-ai for both recipe parsing (structured output) and the main
chat agent (with tool calling via decorators and state management).
"""

from __future__ import annotations

import logging
import os
from textwrap import dedent

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.ag_ui import StateDeps
from ag_ui.core import EventType, StateSnapshotEvent

from .models import Recipe, RecipeContext, SubstitutionResult

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4o")


# =============================================================================
# Recipe Parsing (separate agent for structured output)
# =============================================================================

PARSE_RECIPE_PROMPT = dedent("""
    You are a recipe parsing expert. Extract structured recipe data from the provided text.

    Guidelines:
    - Extract the recipe title, description, servings count, and timing information
    - Parse each ingredient with its quantity, unit, name, and preparation notes
    - Number and structure each cooking step starting from 1
    - Identify cuisine type and dietary tags if mentioned
    - Estimate difficulty based on technique complexity and time
    - If information is not explicitly stated, make reasonable inferences
    - For ambiguous quantities, use the most common interpretation

    Parse the following recipe text into a structured format.
""").strip()

_recipe_parser: Agent[None, Recipe] | None = None


def get_recipe_parser() -> Agent[None, Recipe]:
    """Get or create the recipe parser agent."""
    global _recipe_parser
    if _recipe_parser is None:
        _recipe_parser = Agent(
            model=GoogleModel(MODEL_NAME),
            system_prompt=PARSE_RECIPE_PROMPT,
            output_type=Recipe,
        )
    return _recipe_parser


async def parse_recipe_from_text(document_text: str) -> Recipe | None:
    """
    Parse raw recipe text into a structured Recipe object using pydantic-ai.

    Args:
        document_text: Raw text extracted from uploaded document

    Returns:
        Parsed Recipe object, or None if parsing fails
    """
    try:
        parser = get_recipe_parser()
        result = await parser.run(document_text)
        recipe = result.output
        recipe.source_text = document_text
        return recipe
    except Exception as e:
        logger.warning(f"Recipe parsing failed: {e}")
        return None


# =============================================================================
# Ingredient Substitution (LLM-based matching)
# =============================================================================

SUBSTITUTION_PROMPT = dedent("""
    You are an expert chef helping with ingredient substitutions.

    Given a recipe's ingredient list and a substitution request, you must:
    1. Find the ingredient in the recipe that BEST MATCHES what the user wants to replace
       - Use fuzzy matching: "tomatoes" should match "Roma tomatoes" or "cherry tomatoes"
       - Consider partial matches: "garlic" matches "garlic cloves"
       - Be flexible with descriptors: "parmesan" matches "parmesan cheese"
    2. If a match is found, suggest appropriate quantity/unit adjustments if needed
    3. If NO match is found, set matched_ingredient to null and provide a helpful suggestion
       about what ingredients ARE in the recipe that might be relevant
    4. Provide a brief cooking tip about using the substitute if relevant

    IMPORTANT:
    - If the user's ingredient clearly refers to something in the recipe (even with different wording),
      find and return that match
    - Only set matched_ingredient to null if there's truly no relevant ingredient
    - The confidence score should reflect how well the match fits (1.0 = exact, 0.5+ = good partial match)
""").strip()

_substitution_agent: Agent[None, SubstitutionResult] | None = None


def get_substitution_agent() -> Agent[None, SubstitutionResult]:
    """Get or create the substitution agent."""
    global _substitution_agent
    if _substitution_agent is None:
        _substitution_agent = Agent(
            model=GoogleModel(MODEL_NAME),
            system_prompt=SUBSTITUTION_PROMPT,
            output_type=SubstitutionResult,
        )
    return _substitution_agent


async def find_and_substitute(
    recipe: Recipe,
    original_ingredient: str,
    substitute_name: str,
) -> SubstitutionResult:
    """
    Use LLM to find the best matching ingredient and suggest substitution details.

    Args:
        recipe: The current recipe with ingredients
        original_ingredient: What the user wants to replace (may be fuzzy)
        substitute_name: What they want to use instead

    Returns:
        SubstitutionResult with matched ingredient and substitution details
    """
    # Format ingredients list for the prompt
    ingredients_text = "\n".join(
        f"- {ing.name}: {ing.quantity} {ing.unit or ''} {f'({ing.preparation})' if ing.preparation else ''}"
        for ing in recipe.ingredients
    )

    prompt = f"""
Recipe ingredients:
{ingredients_text}

User wants to replace: "{original_ingredient}"
With: "{substitute_name}"

Find the best matching ingredient and provide substitution details.
"""

    try:
        agent = get_substitution_agent()
        result = await agent.run(prompt)
        return result.output
    except Exception as e:
        logger.warning(f"LLM substitution matching failed: {e}")
        # Fallback: try exact match
        for ing in recipe.ingredients:
            if ing.name.lower() == original_ingredient.lower():
                return SubstitutionResult(
                    matched_ingredient=ing.name,
                    substitute_name=substitute_name,
                    substitute_quantity=ing.quantity,
                    substitute_unit=ing.unit,
                    confidence=1.0,
                )
        return SubstitutionResult(
            matched_ingredient=None,
            substitute_name=substitute_name,
            suggestion=f"Could not find '{original_ingredient}' in the recipe.",
        )


# =============================================================================
# Recipe Companion Agent (pydantic-ai with AG-UI)
# =============================================================================
recipe_agent = Agent(
    model=GoogleModel(MODEL_NAME),
    deps_type=StateDeps[RecipeContext],
    name="recipe_agent",
)

CHAT_PROMPT = dedent("""
    You are a friendly, expert cooking companion. Your personality is warm,
    encouraging, and practical - like a patient friend who happens to be a great cook.

    CRITICAL - TOOL USAGE RULES:
    You MUST use tools to make ANY changes to the recipe. NEVER just describe changes.

    ALWAYS call a tool when the user:
    - Asks to change servings, scale, double, halve → call scale_recipe
    - Asks to substitute, replace, swap, or change an ingredient → call substitute_ingredient
    - Says "I don't have X" or "can I use Y instead" → call substitute_ingredient
    - Says "next step", "done", "what's next" → call update_cooking_progress

    TOOL USAGE IS MANDATORY:
    - If user asks to substitute tomatoes with cherry tomatoes → CALL substitute_ingredient
    - If user asks to double the recipe → CALL scale_recipe
    - Do NOT just give advice about substitutions - ACTUALLY MAKE THE CHANGE

    After calling a tool:
    - Confirm what was changed
    - Mention any cooking tips related to the change

    CAPABILITIES:
    - Scale recipes up or down, recalculating all quantities
    - Substitute ingredients based on dietary needs or availability
    - Provide step-by-step cooking guidance with timing
    - Help recover from cooking mistakes

    Be encouraging! Cooking should be fun, not stressful.
""").strip()


@recipe_agent.instructions
def recipe_instructions(ctx: RunContext[StateDeps[RecipeContext]]) -> str:
    """Dynamic system prompt with current recipe context."""
    base_prompt = CHAT_PROMPT
    state = ctx.deps.state

    if state.recipe:
        base_prompt += f"\n\nCURRENT RECIPE: {state.recipe.title}"
        base_prompt += f"\nServings: {state.recipe.servings}"
        if state.recipe.original_servings:
            base_prompt += f" (originally {state.recipe.original_servings})"
        base_prompt += f"\nIngredients: {len(state.recipe.ingredients)}"
        base_prompt += f"\nSteps: {len(state.recipe.steps)}"
        base_prompt += f"\nCurrent step: {state.current_step}"

    return base_prompt


# =============================================================================
# Tools
# =============================================================================


@recipe_agent.tool
def scale_recipe(
    ctx: RunContext[StateDeps[RecipeContext]], target_servings: int
) -> StateSnapshotEvent | str:
    """
    Scale the recipe to a different number of servings.

    Use when user asks to scale, double, halve, or change servings.

    Args:
        target_servings: The target number of servings to scale to
    """
    state = ctx.deps.state
    if state.recipe is None:
        return "No recipe is currently loaded. Please upload a recipe first."

    original_servings = state.recipe.servings
    state.recipe = state.recipe.scale(target_servings)
    state.scaled_servings = target_servings

    logger.info(f"Scaled recipe from {original_servings} to {target_servings} servings")

    return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state)


@recipe_agent.tool
async def substitute_ingredient(
    ctx: RunContext[StateDeps[RecipeContext]],
    original_ingredient: str,
    substitute_name: str,
) -> StateSnapshotEvent | str:
    """
    Replace an ingredient with a substitute using intelligent matching.

    Use when user doesn't have an ingredient or asks about alternatives.
    Uses LLM to find the best matching ingredient even with fuzzy names
    (e.g., "tomatoes" will match "Roma tomatoes").

    Args:
        original_ingredient: Name of the ingredient to replace (can be fuzzy)
        substitute_name: Name of the substitute ingredient
    """
    state = ctx.deps.state
    if state.recipe is None:
        return "No recipe is currently loaded. Please upload a recipe first."

    # Use LLM to find best match and get substitution details
    result = await find_and_substitute(
        state.recipe, original_ingredient, substitute_name
    )

    if result.matched_ingredient is None:
        # No match found - return helpful suggestion
        suggestion = (
            result.suggestion
            or f"Could not find '{original_ingredient}' in the recipe."
        )
        available = ", ".join(ing.name for ing in state.recipe.ingredients[:5])
        return f"{suggestion} Available ingredients include: {available}"

    # Apply the substitution using the matched ingredient name
    state.recipe = state.recipe.substitute_ingredient(
        result.matched_ingredient,
        result.substitute_name,
        result.substitute_quantity,
        result.substitute_unit,
    )

    logger.info(
        f"Substituted '{result.matched_ingredient}' with '{result.substitute_name}' "
        f"(user requested: '{original_ingredient}', confidence: {result.confidence})"
    )

    return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state)


@recipe_agent.tool
def update_cooking_progress(
    ctx: RunContext[StateDeps[RecipeContext]],
    current_step: int | None = None,
    cooking_started: bool | None = None,
) -> StateSnapshotEvent:
    """
    Update the current cooking step or cooking status.

    Use when user says 'next step', 'done with step X', or wants to track progress.

    Args:
        current_step: Step number to set (0-indexed)
        cooking_started: Whether cooking has started
    """
    state = ctx.deps.state

    if current_step is not None:
        if state.recipe and 0 <= current_step < len(state.recipe.steps):
            state.current_step = current_step
            logger.info(f"Updated current step to {current_step}")

    if cooking_started is not None:
        state.cooking_started = cooking_started
        logger.info(f"Updated cooking_started to {cooking_started}")

    return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state)
