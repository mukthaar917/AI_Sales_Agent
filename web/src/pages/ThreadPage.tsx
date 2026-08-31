import { useEffect, useMemo, useState } from 'react'
import DOMPurify from 'dompurify'
import { getEmailThread } from '../api/email'
import type {
  EmailMessage,
  EmailThreadDetail,
} from '../types/email'

interface ThreadPageProps {
  threadId: string
  onBack: () => void
}

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return 'No date'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function getMessageDate(
  message: EmailMessage,
): string | null {
  return (
    message.received_at ??
    message.sent_at ??
    message.created_at
  )
}

function MessageCard({
  message,
}: {
  message: EmailMessage
}) {
  const sanitizedHtml = useMemo(
    () =>
      message.html_body
        ? DOMPurify.sanitize(message.html_body)
        : null,
    [message.html_body],
  )

  return (
    <article className="message-card">
      <header className="message-header">
        <div>
          <h2>
            {message.sender_name ||
              message.sender_email ||
              'Unknown sender'}
          </h2>

          <p>
            From:{' '}
            {message.sender_email || 'Unknown'}
          </p>

          <p>
            To:{' '}
            {message.recipient_emails.length > 0
              ? message.recipient_emails.join(', ')
              : 'No recipients'}
          </p>

          {message.cc_emails.length > 0 && (
            <p>
              CC: {message.cc_emails.join(', ')}
            </p>
          )}
        </div>

        <time>
          {formatDate(getMessageDate(message))}
        </time>
      </header>

      {message.subject && (
        <h3 className="message-subject">
          {message.subject}
        </h3>
      )}

      {message.has_attachments && (
        <div className="attachment-badge">
          Contains attachments
        </div>
      )}

      {sanitizedHtml ? (
        <div
          className="message-html"
          dangerouslySetInnerHTML={{
            __html: sanitizedHtml,
          }}
        />
      ) : (
        <pre className="message-text">
          {message.text_body ||
            'No message body available.'}
        </pre>
      )}
    </article>
  )
}

export function ThreadPage({
  threadId,
  onBack,
}: ThreadPageProps) {
  const [thread, setThread] =
    useState<EmailThreadDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadThread(): Promise<void> {
      try {
        setLoading(true)
        setError(null)

        const response =
          await getEmailThread(threadId)

        if (!cancelled) {
          setThread(response)
        }
      } catch {
        if (!cancelled) {
          setError(
            'Unable to load this email thread.',
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadThread()

    return () => {
      cancelled = true
    }
  }, [threadId])

  return (
    <main className="thread-page">
      <header className="thread-page-header">
        <button
          type="button"
          className="secondary-button"
          onClick={onBack}
        >
          ← Back to Inbox
        </button>

        <div>
          <p className="eyebrow">
            AI Sales Agent
          </p>
          <h1>
            {thread?.subject || 'Email Thread'}
          </h1>
          <p className="subtitle">
            {thread?.participant_emails.join(', ')}
          </p>
        </div>
      </header>

      {loading && (
        <div className="state-card">
          Loading thread…
        </div>
      )}

      {error && (
        <div
          className="error-message"
          role="alert"
        >
          {error}
        </div>
      )}

      {!loading &&
        !error &&
        thread &&
        thread.messages.length === 0 && (
          <div className="state-card">
            No messages were found in this thread.
          </div>
        )}

      {!loading &&
        !error &&
        thread &&
        thread.messages.length > 0 && (
          <section
            className="message-list"
            aria-label="Thread messages"
          >
            {thread.messages.map((message) => (
              <MessageCard
                key={message.id}
                message={message}
              />
            ))}
          </section>
        )}
    </main>
  )
}