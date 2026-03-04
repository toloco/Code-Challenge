"""
Domain Models for Recipe Companion

Pydantic models for structured recipe data and UI components.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Domain Models - Structured outputs for generative UI
# =============================================================================


class Ingredient(BaseModel):
    """A single ingredient with structured data for UI rendering."""

    name: str = Field(..., description="Name of the ingredient")
    quantity: float | None = Field(default=None, description="Numeric quantity")
    unit: str | None = Field(
        default=None, description="Unit of measurement (cup, tbsp, lb, etc.)"
    )
    preparation: str | None = Field(
        default=None, description="Preparation notes like 'diced' or 'minced'"
    )
    category: Literal["produce", "protein", "dairy", "pantry", "spice", "other"] = (
        Field(
            default="other", description="Ingredient category for grocery organization"
        )
    )
    substitutes: list[str] = Field(
        default_factory=list, description="Possible ingredient substitutions"
    )


class RecipeStep(BaseModel):
    """A cooking step with timing and actionable UI hints."""

    step_number: int = Field(..., description="Sequential step number starting from 1")
    instruction: str = Field(..., description="The step instruction text")
    duration_minutes: int | None = Field(
        default=None, description="Estimated time for this step in minutes"
    )
    timer_label: str | None = Field(
        default=None, description="Label for timer button if applicable"
    )
    requires_attention: bool = Field(
        default=False,
        description="Whether step needs constant attention (e.g., 'stir constantly')",
    )
    tips: list[str] = Field(
        default_factory=list, description="Helpful tips for this step"
    )


class Recipe(BaseModel):
    """Complete extracted recipe with all structured data."""

    title: str = Field(..., description="Recipe title/name")
    description: str | None = Field(
        default=None, description="Brief recipe description"
    )
    servings: int = Field(..., description="Number of servings this recipe makes")
    original_servings: int | None = Field(
        default=None,
        description="Original servings count before scaling (for reference)",
    )
    prep_time_minutes: int | None = Field(
        default=None, description="Preparation time in minutes"
    )
    cook_time_minutes: int | None = Field(
        default=None, description="Cooking time in minutes"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium", description="Recipe difficulty level"
    )
    cuisine: str | None = Field(
        default=None, description="Cuisine type (Italian, Mexican, etc.)"
    )
    dietary_tags: list[str] = Field(
        default_factory=list,
        description="Dietary tags like 'vegetarian', 'gluten-free', 'vegan'",
    )
    ingredients: list[Ingredient] = Field(..., description="List of recipe ingredients")
    steps: list[RecipeStep] = Field(..., description="Ordered list of cooking steps")
    source_text: str | None = Field(
        default=None, description="Original source text for reference"
    )

    def scale(self, target_servings: int) -> "Recipe":
        """
        Return a new Recipe scaled to target_servings.
        Preserves original_servings for reference.
        """
        if self.servings == 0 or self.servings == target_servings:
            return self

        scale_factor = target_servings / self.servings
        original = self.original_servings or self.servings

        scaled_ingredients = [
            Ingredient(
                name=ing.name,
                quantity=round(ing.quantity * scale_factor, 2)
                if ing.quantity
                else None,
                unit=ing.unit,
                preparation=ing.preparation,
                category=ing.category,
                substitutes=ing.substitutes,
            )
            for ing in self.ingredients
        ]

        return Recipe(
            **self.model_dump(exclude={"ingredients", "servings", "original_servings"}),
            ingredients=scaled_ingredients,
            servings=target_servings,
            original_servings=original,
        )

    def substitute_ingredient(
        self,
        original_name: str,
        substitute_name: str,
        substitute_quantity: float | None = None,
        substitute_unit: str | None = None,
    ) -> "Recipe":
        """
        Return a new Recipe with one ingredient substituted.
        Matches ingredient by name (case-insensitive).
        """
        new_ingredients = []
        for ing in self.ingredients:
            if ing.name.lower() == original_name.lower():
                new_ingredients.append(
                    Ingredient(
                        name=substitute_name,
                        quantity=substitute_quantity
                        if substitute_quantity is not None
                        else ing.quantity,
                        unit=substitute_unit
                        if substitute_unit is not None
                        else ing.unit,
                        preparation=ing.preparation,
                        category=ing.category,
                        substitutes=[],
                    )
                )
            else:
                new_ingredients.append(ing)

        return Recipe(
            **self.model_dump(exclude={"ingredients"}),
            ingredients=new_ingredients,
        )


# =============================================================================
# UI Component Models - What the frontend renders
# =============================================================================


class UIComponentType(str, Enum):
    """Types of UI components the agent can return."""

    RECIPE_CARD = "recipe_card"
    INGREDIENT_CHECKLIST = "ingredient_checklist"
    STEP_CARD = "step_card"
    TIMER_SUGGESTION = "timer_suggestion"
    QUICK_ACTIONS = "quick_actions"
    SHOPPING_LIST = "shopping_list"
    SCALING_RESULT = "scaling_result"
    SUBSTITUTION = "substitution"
    RECOVERY_HELP = "recovery_help"
    PAIRING_SUGGESTION = "pairing_suggestion"


class UIComponent(BaseModel):
    """A UI component for the frontend to render inline in chat."""

    type: UIComponentType
    data: dict[str, Any]


class TimerSuggestion(BaseModel):
    """Structured timer for frontend rendering."""

    type: Literal["timer_suggestion"] = "timer_suggestion"
    duration_seconds: int
    label: str
    step_number: int | None = None


class QuickAction(BaseModel):
    """A suggested quick action button."""

    label: str
    action_id: str
    icon: str | None = None  # Emoji or icon name


class AgentResponse(BaseModel):
    """Structured response from the agent with text and optional UI components."""

    message: str
    components: list[UIComponent] = Field(default_factory=list)
    quick_actions: list[QuickAction] = Field(default_factory=list)
    state_hint: Literal["upload", "overview", "cooking", "finished"] = "overview"


# =============================================================================
# Agent Context & State
# =============================================================================


class RecipeContext(BaseModel):
    """Shared state between frontend and agent via CopilotKit."""

    document_text: str | None = None
    recipe: Recipe | None = None
    current_step: int = 0
    scaled_servings: int | None = None
    checked_ingredients: list[str] = Field(default_factory=list)
    cooking_started: bool = False


class SubstitutionResult(BaseModel):
    """Result from LLM-based ingredient substitution."""

    matched_ingredient: str | None = Field(
        default=None,
        description="Name of the ingredient in the recipe that was matched",
    )
    substitute_name: str = Field(..., description="Name of the substitute ingredient")
    substitute_quantity: float | None = Field(
        default=None, description="Suggested quantity for the substitute"
    )
    substitute_unit: str | None = Field(
        default=None, description="Unit for the substitute quantity"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the ingredient match (0-1)",
    )
    suggestion: str | None = Field(
        default=None, description="Suggestion message if no match found"
    )
    cooking_tip: str | None = Field(
        default=None, description="Cooking tip for using the substitute"
    )
