import { type ChangeEvent, type FormEvent, useState } from 'react'

type UploadPanelProps = {
  onUploadSuccess: (data: any) => void
}

function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [threadId, setThreadId] = useState<string | null>(null)
  const [recipe, setRecipe] = useState<any>(null)
  const [rawResponse, setRawResponse] = useState<any>(null)

  function isRetryableStatus(status: number) {
    return status === 422 || status === 429 || status === 503
  }

  function delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setError(null)
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError('Please choose a .pdf or .txt file first.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      let data: any = null
      let uploadSucceeded = false
      let lastStatus: number | null = null

      for (let attempt = 1; attempt <= 2; attempt += 1) {
        const formData = new FormData()
        formData.append('file', selectedFile)

        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        })

        lastStatus = response.status

        if (response.ok) {
          data = await response.json()
          uploadSucceeded = true
          break
        }

        if (attempt === 1 && isRetryableStatus(response.status)) {
          await delay(2000)
          continue
        }

        throw new Error(`Upload failed with status ${response.status}`)
      }

      if (!uploadSucceeded || !data) {
        throw new Error(
          lastStatus ? `Upload failed with status ${lastStatus}` : 'Upload failed. Please try again.',
        )
      }

      setThreadId(data.threadId ?? null)
      setRecipe(data)
      setRawResponse(data)
      onUploadSuccess(data)
      console.log('Upload response:', data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <h2>Upload Recipe</h2>
      <p>Select a PDF or text recipe file to get started.</p>

      <form className="upload-form" onSubmit={handleUpload}>
        <input
          type="file"
          accept=".pdf,.txt"
          onChange={handleFileChange}
          className="file-input"
        />

        <p className="upload-meta">
          Selected: <strong>{selectedFile?.name ?? 'No file selected'}</strong>
        </p>

        <button type="submit" className="touch-button" disabled={loading || !selectedFile}>
          {loading ? 'Extracting recipe...' : 'Upload Recipe'}
        </button>
      </form>

      {error ? <p className="status-error">{error}</p> : null}
      {threadId ? <p className="status-ok">Thread created: {threadId}</p> : null}
      {recipe ? <p className="status-meta">Recipe response stored for next step.</p> : null}
      {rawResponse ? <p className="status-meta">Full response stored for later integration.</p> : null}
    </section>
  )
}

export default UploadPanel
