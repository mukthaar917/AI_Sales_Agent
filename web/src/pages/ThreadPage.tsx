import { useEffect, useMemo, useState } from 'react'
import DOMPurify from 'dompurify'
import {
  createDraftReply,
  detectSalesOpportunity,
  getEmailThread,
  getReplySuggestions,
  summarizeThread,
} from '../api/email'
import type {
  EmailMessage,
  EmailThreadDetail,
  EmailThreadSummaryResponse,
  ReplySuggestionsResponse,
  SalesOpportunityResponse,
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

  const [summary, setSummary] =
    useState<EmailThreadSummaryResponse | null>(null)

  const [replySuggestions, setReplySuggestions] =
    useState<ReplySuggestionsResponse | null>(null)

  const [salesOpportunity, setSalesOpportunity] =
    useState<SalesOpportunityResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [summarizing, setSummarizing] =
    useState(false)

  const [generatingReplies, setGeneratingReplies] =
    useState(false)

  const [detectingSales, setDetectingSales] =
    useState(false)

  const [creatingDraftIndex, setCreatingDraftIndex] =
    useState<number | null>(null)

  const [error, setError] =
    useState<string | null>(null)

  const [summaryError, setSummaryError] =
    useState<string | null>(null)

  const [replyError, setReplyError] =
    useState<string | null>(null)

  const [salesError, setSalesError] =
    useState<string | null>(null)

  const [draftError, setDraftError] =
    useState<string | null>(null)

  const [draftSuccess, setDraftSuccess] =
    useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadThread(): Promise<void> {
      try {
        setLoading(true)
        setError(null)

        setSummary(null)
        setSummaryError(null)

        setReplySuggestions(null)
        setReplyError(null)

        setSalesOpportunity(null)
        setSalesError(null)

        setCreatingDraftIndex(null)
        setDraftError(null)
        setDraftSuccess(null)

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

  async function handleSummarize(): Promise<void> {
    try {
      setSummarizing(true)
      setSummaryError(null)

      const response = await summarizeThread(
        threadId,
      )

      setSummary(response)
    } catch {
      setSummaryError(
        'Unable to summarize this email thread right now.',
      )
    } finally {
      setSummarizing(false)
    }
  }

  async function handleGenerateReplies(): Promise<void> {
    try {
      setGeneratingReplies(true)
      setReplyError(null)
      setDraftError(null)
      setDraftSuccess(null)

      const response = await getReplySuggestions(
        threadId,
      )

      setReplySuggestions(response)
    } catch {
      setReplyError(
        'Unable to generate reply suggestions right now.',
      )
    } finally {
      setGeneratingReplies(false)
    }
  }

  async function handleDetectSalesOpportunity(): Promise<void> {
    try {
      setDetectingSales(true)
      setSalesError(null)

      const response = await detectSalesOpportunity(
        threadId,
      )

      setSalesOpportunity(response)
    } catch {
      setSalesError(
        'Unable to detect sales opportunity right now.',
      )
    } finally {
      setDetectingSales(false)
    }
  }

  async function handleCreateDraft(
    subject: string,
    body: string,
    suggestionIndex: number,
  ): Promise<void> {
    try {
      setCreatingDraftIndex(suggestionIndex)
      setDraftError(null)
      setDraftSuccess(null)

      const response = await createDraftReply(
        threadId,
        {
          subject,
          body,
        },
      )

      setDraftSuccess(
        `Gmail draft created successfully. Draft ID: ${response.draft_id}`,
      )
    } catch {
      setDraftError(
        'Unable to create the Gmail draft right now.',
      )
    } finally {
      setCreatingDraftIndex(null)
    }
  }

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

        <div className="thread-heading-row">
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

          <div className="thread-action-buttons">
            <button
              type="button"
              className="primary-button"
              onClick={() => void handleSummarize()}
              disabled={
                loading ||
                summarizing ||
                !thread ||
                thread.messages.length === 0
              }
            >
              {summarizing
                ? 'Summarizing…'
                : summary
                  ? 'Regenerate Summary'
                  : 'Summarize Thread'}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                void handleGenerateReplies()
              }
              disabled={
                loading ||
                generatingReplies ||
                !thread ||
                thread.messages.length === 0
              }
            >
              {generatingReplies
                ? 'Generating Replies…'
                : replySuggestions
                  ? 'Regenerate Replies'
                  : 'Generate Reply Suggestions'}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                void handleDetectSalesOpportunity()
              }
              disabled={
                loading ||
                detectingSales ||
                !thread ||
                thread.messages.length === 0
              }
            >
              {detectingSales
                ? 'Analyzing Sales…'
                : salesOpportunity
                  ? 'Recheck Sales Opportunity'
                  : 'Detect Sales Opportunity'}
            </button>
          </div>
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

      {summaryError && (
        <div
          className="error-message"
          role="alert"
        >
          {summaryError}
        </div>
      )}

      {replyError && (
        <div
          className="error-message"
          role="alert"
        >
          {replyError}
        </div>
      )}

      {salesError && (
        <div
          className="error-message"
          role="alert"
        >
          {salesError}
        </div>
      )}

      {draftError && (
        <div
          className="error-message"
          role="alert"
        >
          {draftError}
        </div>
      )}

      {draftSuccess && (
        <div
          className="success-message"
          role="status"
        >
          {draftSuccess}
        </div>
      )}

      {salesOpportunity && (
        <section
          className="sales-opportunity-card"
          aria-label="Sales opportunity result"
        >
          <p className="eyebrow">
            Sales Opportunity
          </p>

          <h2>
            {salesOpportunity.classification ===
            'sales_opportunity'
              ? 'Sales Opportunity Detected'
              : salesOpportunity.classification ===
                  'non_sales'
                ? 'Not a Sales Opportunity'
                : 'Unclear Opportunity'}
          </h2>

          <p>
            <strong>
              Confidence:
            </strong>{' '}
            {Math.round(
              salesOpportunity.confidence * 100,
            )}
            %
          </p>

          <p>
            <strong>
              Reason:
            </strong>{' '}
            {salesOpportunity.reason}
          </p>
        </section>
      )}

      {summary && (
        <section
          className="summary-card"
          aria-label="Thread summary"
        >
          <div className="summary-card-header">
            <div>
              <p className="eyebrow">
                AI Summary
              </p>

              <h2>
                Conversation overview
              </h2>
            </div>

            <span className="summary-count">
              {summary.message_count}{' '}
              {summary.message_count === 1
                ? 'message'
                : 'messages'}
            </span>
          </div>

          <p className="summary-text">
            {summary.summary}
          </p>
        </section>
      )}

      {replySuggestions &&
        replySuggestions.suggestions.length > 0 && (
          <section
            className="reply-suggestions"
            aria-label="Reply suggestions"
          >
            <div className="reply-suggestions-header">
              <div>
                <p className="eyebrow">
                  AI Reply Suggestions
                </p>

                <h2>
                  Suggested replies
                </h2>
              </div>

              <span className="summary-count">
                {replySuggestions.suggestions.length}{' '}
                {replySuggestions.suggestions.length === 1
                  ? 'suggestion'
                  : 'suggestions'}
              </span>
            </div>

            <div className="reply-suggestion-list">
              {replySuggestions.suggestions.map(
                (suggestion, index) => (
                  <article
                    key={`${suggestion.subject}-${index}`}
                    className="reply-suggestion-card"
                  >
                    <div className="reply-suggestion-number">
                      Suggestion {index + 1}
                    </div>

                    <h3>
                      {suggestion.subject}
                    </h3>

                    <p>
                      {suggestion.body}
                    </p>

                    <div className="reply-suggestion-actions">
                      <button
                        type="button"
                        className="primary-button"
                        onClick={() =>
                          void handleCreateDraft(
                            suggestion.subject,
                            suggestion.body,
                            index,
                          )
                        }
                        disabled={
                          creatingDraftIndex !== null
                        }
                      >
                        {creatingDraftIndex === index
                          ? 'Creating Draft…'
                          : 'Create Gmail Draft'}
                      </button>
                    </div>
                  </article>
                ),
              )}
            </div>
          </section>
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