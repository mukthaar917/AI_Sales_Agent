import {
  type FormEvent,
  useEffect,
  useState,
} from 'react'

import {
  askKnowledge,
  deleteKnowledgeDocument,
  getKnowledgeDocuments,
  uploadKnowledgeDocument,
  type KnowledgeDocument,
  type RAGAnswerResponse,
} from '../api/knowledge'

export function KnowledgeBasePage() {
  const [documents, setDocuments] =
    useState<KnowledgeDocument[]>([])

  const [file, setFile] =
    useState<File | null>(null)

  const [title, setTitle] =
    useState('')

  const [question, setQuestion] =
    useState('')

  const [answer, setAnswer] =
    useState<RAGAnswerResponse | null>(null)

  const [error, setError] =
    useState('')

  const [loading, setLoading] =
    useState(false)

  async function loadDocuments() {
    try {
      const result =
        await getKnowledgeDocuments()

      setDocuments(result.items)
    } catch (err) {
      console.error(err)
      setError(
        'Unable to load knowledge documents.',
      )
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [])

  async function handleUpload(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!file) {
      setError('Please select a document.')
      return
    }

    try {
      setLoading(true)
      setError('')

      await uploadKnowledgeDocument(
        file,
        title,
      )

      setFile(null)
      setTitle('')

      await loadDocuments()
    } catch (err: any) {
      console.error(err)

      setError(
        err?.response?.data?.detail ||
          'Unable to upload document.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleQuestion(
    event: FormEvent,
  ) {
    event.preventDefault()

    if (!question.trim()) {
      return
    }

    try {
      setLoading(true)
      setError('')
      setAnswer(null)

      const result =
        await askKnowledge(
          question.trim(),
        )

      setAnswer(result)
    } catch (err: any) {
      console.error(err)

      setError(
        err?.response?.data?.detail ||
          'Unable to answer question.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(
    document: KnowledgeDocument,
  ) {
    if (
      !window.confirm(
        `Delete ${document.original_filename}?`,
      )
    ) {
      return
    }

    await deleteKnowledgeDocument(
      document.id,
    )

    await loadDocuments()
  }

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">
            AI SALES AGENT
          </p>

          <h1>Knowledge Base</h1>

          <p className="subtitle">
            Upload approved company
            information and ask AI questions
            from it.
          </p>
        </div>
      </header>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form
        className="customer-form"
        onSubmit={handleUpload}
      >
        <h2>Upload Knowledge</h2>

        <input
          placeholder="Document title"
          value={title}
          onChange={(e) =>
            setTitle(e.target.value)
          }
        />

        <input
          type="file"
          accept=".pdf,.txt,.md"
          onChange={(e) =>
            setFile(
              e.target.files?.[0] ||
                null,
            )
          }
        />

        <button
          className="primary-button"
          disabled={loading}
        >
          Upload Document
        </button>
      </form>

      <div className="customers-card">
        <h2>Documents</h2>

        {documents.length === 0 ? (
          <p>
            No knowledge documents uploaded.
          </p>
        ) : (
          <table className="customer-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Title</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {documents.map(
                (document) => (
                  <tr key={document.id}>
                    <td>
                      {
                        document.original_filename
                      }
                    </td>

                    <td>
                      {document.title || '-'}
                    </td>

                    <td>
                      {document.status}
                    </td>

                    <td>
                      <button
                        type="button"
                        onClick={() =>
                          handleDelete(
                            document,
                          )
                        }
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        )}
      </div>

      <form
        className="customer-form"
        onSubmit={handleQuestion}
      >
        <h2>Ask Knowledge Base</h2>

        <textarea
          placeholder="Ask a question about your company, products or services..."
          value={question}
          onChange={(e) =>
            setQuestion(e.target.value)
          }
        />

        <button
          className="primary-button"
          disabled={loading}
        >
          Ask AI
        </button>
      </form>

      {answer && (
        <div className="customers-card">
          <h2>AI Answer</h2>

          <p>{answer.answer}</p>

          {answer.insufficient_knowledge && (
            <p>
              <strong>
                Human review required.
              </strong>
            </p>
          )}

          {answer.sources.length > 0 && (
            <>
              <h3>Sources</h3>

              {answer.sources.map(
                (source) => (
                  <p key={source.chunk_id}>
                    {source.filename}
                    {source.page
                      ? ` — Page ${source.page}`
                      : ''}
                  </p>
                ),
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}