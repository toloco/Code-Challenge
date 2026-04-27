function UploadPanel() {
  return (
    <section className="panel">
      <h2>Upload Recipe</h2>
      <p>Select a PDF or text recipe file to get started.</p>
      <button type="button" className="touch-button" disabled>
        Choose Recipe File
      </button>
    </section>
  )
}

export default UploadPanel
