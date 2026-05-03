type Ingredient = {
  name: string
  quantity: number | null
  unit: string | null
  preparation: string | null
}

type RecipeStep = {
  step_number: number
  instruction: string
}

export type Recipe = {
  title: string
  prep_time_minutes: number | null
  cook_time_minutes: number | null
  servings: number | null
  difficulty: string | null
  ingredients: Ingredient[]
  steps: RecipeStep[]
}

export type RecipeContext = {
  document_text: string | null
  recipe: Recipe | null
  current_step: number
  scaled_servings: number | null
  checked_ingredients: string[]
  cooking_started: boolean
}

type RecipePanelProps = {
  sharedState: RecipeContext | null
  setSharedState?: (
    next: RecipeContext | ((current: RecipeContext | undefined) => RecipeContext),
  ) => void
}

function formatIngredient(ingredient: Ingredient) {
  const parts = [
    ingredient.quantity ?? '',
    ingredient.unit ?? '',
    ingredient.name ?? '',
    ingredient.preparation ?? '',
  ].filter(Boolean)

  return parts.join(' ')
}

function clampStepIndex(stepIndex: number, totalSteps: number) {
  if (!Number.isFinite(stepIndex) || stepIndex < 0) return 0
  if (totalSteps <= 0) return 0
  return Math.min(stepIndex, totalSteps - 1)
}

function RecipePanel({ sharedState, setSharedState }: RecipePanelProps) {
  const recipe = sharedState?.recipe ?? null

  if (!sharedState || !recipe) {
    return (
      <section className="panel panel-primary">
        <h2>Recipe Display</h2>
        <p className="empty-state">
          Upload a recipe to see title, ingredients, and step-by-step instructions here.
        </p>
      </section>
    )
  }

  const baseContext = sharedState
  const totalSteps = recipe.steps?.length ?? 0
  const currentStepIndex = clampStepIndex(baseContext.current_step ?? 0, totalSteps)
  const displayServings = baseContext.scaled_servings ?? recipe.servings
  const checkedIngredients = baseContext.checked_ingredients ?? []

  function toggleIngredient(name: string) {
    if (!setSharedState) return

    setSharedState((current) => {
      if (!current) return baseContext

      const currentChecked = current.checked_ingredients ?? []
      const nextChecked = currentChecked.includes(name)
        ? currentChecked.filter((item) => item !== name)
        : [...currentChecked, name]

      return {
        ...current,
        checked_ingredients: nextChecked,
      }
    })
  }

  return (
    <section className="panel panel-primary">
      <h2>Recipe Display</h2>
      <h3 className="recipe-title">{recipe.title}</h3>

      <div className="recipe-meta" aria-label="Recipe details">
        {recipe.prep_time_minutes ? <span>Prep: {recipe.prep_time_minutes} min</span> : null}
        {recipe.cook_time_minutes ? <span>Cook: {recipe.cook_time_minutes} min</span> : null}
        {displayServings ? (
          <span>{sharedState.scaled_servings ? 'Scaled servings' : 'Servings'}: {displayServings}</span>
        ) : null}
        {recipe.difficulty ? <span>Difficulty: {recipe.difficulty}</span> : null}
        <span>{sharedState.cooking_started ? 'Cooking started' : 'Not started yet'}</span>
      </div>

      <section className="recipe-section" aria-label="Ingredients">
        <h4>Ingredients</h4>
        <ul className="ingredient-list">
          {recipe.ingredients?.map((ingredient) => (
            <li key={ingredient.name}>
              <label
                className={`ingredient-item${
                  checkedIngredients.includes(ingredient.name) ? ' is-checked' : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={checkedIngredients.includes(ingredient.name)}
                  onChange={() => toggleIngredient(ingredient.name)}
                />
                <span className="ingredient-text">{formatIngredient(ingredient)}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section className="recipe-section" aria-label="Cooking steps">
        <h4>Steps</h4>
        <ol className="step-list">
          {recipe.steps?.map((step, index) => (
            <li
              key={step.step_number}
              className={`step-item${index === currentStepIndex ? ' is-current' : ''}`}
              aria-current={index === currentStepIndex ? 'step' : undefined}
            >
              <p className="step-indicator">
                Step {index + 1} of {totalSteps}
                {index === currentStepIndex ? <span className="current-step-badge">Current</span> : null}
              </p>
              <p>{step.instruction}</p>
            </li>
          ))}
        </ol>
      </section>
      <div className="step-summary">
        Step {totalSteps ? currentStepIndex + 1 : 0} of {totalSteps}
      </div>
    </section>
  )
}

export default RecipePanel
