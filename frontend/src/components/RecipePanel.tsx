import { useEffect, useState } from 'react'

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

type RecipePanelProps = {
  recipe: Recipe | null
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

function RecipePanel({ recipe }: RecipePanelProps) {
  const [checkedIngredients, setCheckedIngredients] = useState<string[]>([])

  useEffect(() => {
    setCheckedIngredients([])
  }, [recipe?.title])

  function toggleIngredient(name: string) {
    setCheckedIngredients((current) =>
      current.includes(name) ? current.filter((item) => item !== name) : [...current, name],
    )
  }

  if (!recipe) {
    return (
      <section className="panel panel-primary">
        <h2>Recipe Display</h2>
        <p className="empty-state">
          Upload a recipe to see title, ingredients, and step-by-step instructions here.
        </p>
      </section>
    )
  }

  const totalSteps = recipe.steps?.length ?? 0

  return (
    <section className="panel panel-primary">
      <h2>Recipe Display</h2>
      <h3 className="recipe-title">{recipe.title}</h3>

      <div className="recipe-meta" aria-label="Recipe details">
        {recipe.prep_time_minutes ? <span>Prep: {recipe.prep_time_minutes} min</span> : null}
        {recipe.cook_time_minutes ? <span>Cook: {recipe.cook_time_minutes} min</span> : null}
        {recipe.servings ? <span>Servings: {recipe.servings}</span> : null}
        {recipe.difficulty ? <span>Difficulty: {recipe.difficulty}</span> : null}
      </div>

      <section className="recipe-section" aria-label="Ingredients">
        <h4>Ingredients</h4>
        <ul className="ingredient-list">
          {recipe.ingredients?.map((ingredient) => (
            <li key={ingredient.name}>
              <label className="ingredient-item">
                <input
                  type="checkbox"
                  checked={checkedIngredients.includes(ingredient.name)}
                  onChange={() => toggleIngredient(ingredient.name)}
                />
                <span>{formatIngredient(ingredient)}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section className="recipe-section" aria-label="Cooking steps">
        <h4>Steps</h4>
        <ol className="step-list">
          {recipe.steps?.map((step, index) => (
            <li key={step.step_number} className="step-item">
              <p className="step-indicator">
                Step {index + 1} of {totalSteps}
              </p>
              <p>{step.instruction}</p>
            </li>
          ))}
        </ol>
      </section>
      <div className="step-summary">
        Step 1 of {totalSteps} (AI step tracking will be added in a later step)
      </div>
    </section>
  )
}

export default RecipePanel
