function RecipePanel() {
  return (
    <section className="panel panel-primary">
      <h2>Recipe Display</h2>
      <p>Recipe title, ingredients, and cooking steps will appear here.</p>
      <div className="placeholder-list" aria-label="Recipe placeholders">
        <p>- Recipe metadata placeholder</p>
        <p>- Ingredients list placeholder</p>
        <p>- Step-by-step instructions placeholder</p>
      </div>
    </section>
  )
}

export default RecipePanel
