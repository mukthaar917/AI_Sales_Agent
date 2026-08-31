import { useEffect, useMemo, useState } from 'react'
import DOMPurify from 'dompurify'
import {
  createDraftReply,
  createQuotationDraft,
  createQuotationFromThread,
  detectSalesOpportunity,
  downloadQuotationPdf,
  extractQuotationRequirements,
  getEmailThread,
  getReplySuggestions,
  previewQuotation,
  summarizeThread,
  updateQuotationStatus,
} from '../api/email'
import type {
  CreateQuotationFromThreadResponse,
  EmailMessage,
  EmailThreadDetail,
  EmailThreadSummaryResponse,
  QuotationDraftResponse,
  QuotationExtractionResponse,
  QuotationPreviewResponse,
  QuotationStatus,
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

function yesNo(value: boolean): string {
  return value ? 'Yes' : 'No'
}

function formatMoney(
  value: string,
  currency: string,
): string {
  const amount = Number(value)

  if (Number.isNaN(amount)) {
    return `${currency} ${value}`
  }

  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${currency} ${amount.toFixed(2)}`
  }
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

  const [quotationExtraction, setQuotationExtraction] =
    useState<QuotationExtractionResponse | null>(null)

  const [quotationPreview, setQuotationPreview] =
    useState<QuotationPreviewResponse | null>(null)

  const [createdQuotation, setCreatedQuotation] =
    useState<CreateQuotationFromThreadResponse | null>(
      null,
    )

  const [quotationDraft, setQuotationDraft] =
    useState<QuotationDraftResponse | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [summarizing, setSummarizing] =
    useState(false)

  const [generatingReplies, setGeneratingReplies] =
    useState(false)

  const [detectingSales, setDetectingSales] =
    useState(false)

  const [extractingQuotation, setExtractingQuotation] =
    useState(false)

  const [previewingQuotation, setPreviewingQuotation] =
    useState(false)

  const [creatingQuotation, setCreatingQuotation] =
    useState(false)

  const [updatingQuotationStatus, setUpdatingQuotationStatus] =
    useState(false)

  const [quotationStatusError, setQuotationStatusError] =
    useState<string | null>(null)

  const [downloadingPdf, setDownloadingPdf] =
    useState(false)

  const [creatingQuotationDraft, setCreatingQuotationDraft] =
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

  const [quotationError, setQuotationError] =
    useState<string | null>(null)

  const [previewError, setPreviewError] =
    useState<string | null>(null)

  const [createQuotationError, setCreateQuotationError] =
    useState<string | null>(null)

  const [quotationDraftError, setQuotationDraftError] =
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

        setQuotationExtraction(null)
        setQuotationError(null)

        setQuotationPreview(null)
        setPreviewError(null)

        setCreatedQuotation(null)
        setCreateQuotationError(null)
        setQuotationStatusError(null)

        setQuotationDraft(null)
        setQuotationDraftError(null)

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

      const response =
        await detectSalesOpportunity(threadId)

      setSalesOpportunity(response)
    } catch {
      setSalesError(
        'Unable to detect sales opportunity right now.',
      )
    } finally {
      setDetectingSales(false)
    }
  }

  async function handleExtractQuotation(): Promise<void> {
    try {
      setExtractingQuotation(true)
      setQuotationError(null)

      setQuotationPreview(null)
      setPreviewError(null)

      setCreatedQuotation(null)
      setCreateQuotationError(null)

      setQuotationDraft(null)
      setQuotationDraftError(null)

      const response =
        await extractQuotationRequirements(
          threadId,
        )

      setQuotationExtraction(response)
    } catch {
      setQuotationError(
        'Unable to extract quotation requirements right now.',
      )
    } finally {
      setExtractingQuotation(false)
    }
  }

  async function handlePreviewQuotation(): Promise<void> {
    try {
      setPreviewingQuotation(true)
      setPreviewError(null)

      setCreatedQuotation(null)
      setCreateQuotationError(null)

      setQuotationDraft(null)
      setQuotationDraftError(null)

      const response = await previewQuotation(
        threadId,
      )

      setQuotationPreview(response)
    } catch {
      setPreviewError(
        'Unable to prepare the quotation preview. Confirm the customer and product exist in the catalog.',
      )
    } finally {
      setPreviewingQuotation(false)
    }
  }

  async function handleCreateQuotation(): Promise<void> {
    if (!quotationPreview) {
      return
    }

    try {
      setCreatingQuotation(true)
      setCreateQuotationError(null)
      setQuotationDraft(null)
      setQuotationDraftError(null)

      const response =
        await createQuotationFromThread(threadId)

      setCreatedQuotation(response)
    } catch {
      setCreateQuotationError(
        'Unable to create the quotation right now.',
      )
    } finally {
      setCreatingQuotation(false)
    }
  }

  async function handleUpdateQuotationStatus(
    nextStatus: QuotationStatus,
  ): Promise<void> {
    if (!createdQuotation) {
      return
    }

    try {
      setUpdatingQuotationStatus(true)
      setQuotationStatusError(null)

      const response = await updateQuotationStatus(
        createdQuotation.quotation_id,
        {
          status: nextStatus,
        },
      )

      setCreatedQuotation((current) => {
        if (!current) {
          return current
        }

        return {
          ...current,
          status: response.status,
        }
      })
    } catch {
      setQuotationStatusError(
        'Unable to update the quotation status right now.',
      )
    } finally {
      setUpdatingQuotationStatus(false)
    }
  }

  async function handleDownloadPdf(): Promise<void> {
    if (!createdQuotation) {
      return
    }

    try {
      setDownloadingPdf(true)
      setCreateQuotationError(null)

      const pdf = await downloadQuotationPdf(
        createdQuotation.quotation_id,
      )

      const url = window.URL.createObjectURL(pdf)

      const anchor = document.createElement('a')

      anchor.href = url
      anchor.download =
        `${createdQuotation.quotation_number}.pdf`

      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()

      window.URL.revokeObjectURL(url)
    } catch {
      setCreateQuotationError(
        'Unable to download the quotation PDF.',
      )
    } finally {
      setDownloadingPdf(false)
    }
  }

  async function handleCreateQuotationDraft(): Promise<void> {
    if (!createdQuotation) {
      return
    }

    try {
      setCreatingQuotationDraft(true)
      setQuotationDraftError(null)

      const response = await createQuotationDraft(
        threadId,
        {
          quotation_id:
            createdQuotation.quotation_id,
        },
      )

      setQuotationDraft(response)
    } catch {
      setQuotationDraftError(
        'Unable to create the Gmail quotation draft right now.',
      )
    } finally {
      setCreatingQuotationDraft(false)
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
              onClick={() =>
                void handleSummarize()
              }
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

            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                void handleExtractQuotation()
              }
              disabled={
                loading ||
                extractingQuotation ||
                !thread ||
                thread.messages.length === 0
              }
            >
              {extractingQuotation
                ? 'Extracting Requirements…'
                : quotationExtraction
                  ? 'Re-extract Requirements'
                  : 'Extract Quotation Requirements'}
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

      {quotationError && (
        <div
          className="error-message"
          role="alert"
        >
          {quotationError}
        </div>
      )}

      {previewError && (
        <div
          className="error-message"
          role="alert"
        >
          {previewError}
        </div>
      )}

      {createQuotationError && (
        <div
          className="error-message"
          role="alert"
        >
          {createQuotationError}
        </div>
      )}

      {quotationStatusError && (
        <div
          className="error-message"
          role="alert"
        >
          {quotationStatusError}
        </div>
      )}

      {quotationDraftError && (
        <div
          className="error-message"
          role="alert"
        >
          {quotationDraftError}
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

      {quotationDraft && (
        <div
          className="success-message"
          role="status"
        >
          Gmail quotation draft created successfully.
          {' '}
          {quotationDraft.attachment_filename}
          {' '}
          is attached for
          {' '}
          {quotationDraft.recipient}.
          {' '}
          Review it in Gmail before sending.
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
            <strong>Confidence:</strong>{' '}
            {Math.round(
              salesOpportunity.confidence * 100,
            )}
            %
          </p>

          <p>
            <strong>Reason:</strong>{' '}
            {salesOpportunity.reason}
          </p>
        </section>
      )}

      {quotationExtraction && (
        <section
          className="quotation-extraction-card"
          aria-label="Quotation requirements"
        >
          <p className="eyebrow">
            Quotation Requirements
          </p>

          <h2>
            Extracted requirements
          </h2>

          <div className="quotation-requirements-grid">
            <p>
              <strong>Product:</strong>{' '}
              {quotationExtraction.product ||
                'Not detected'}
            </p>

            <p>
              <strong>Quantity:</strong>{' '}
              {quotationExtraction.quantity ??
                'Not detected'}
            </p>

            <p>
              <strong>
                Pricing requested:
              </strong>{' '}
              {yesNo(
                quotationExtraction.pricing_requested,
              )}
            </p>

            <p>
              <strong>
                Availability requested:
              </strong>{' '}
              {yesNo(
                quotationExtraction.availability_requested,
              )}
            </p>

            <p>
              <strong>
                Delivery requested:
              </strong>{' '}
              {yesNo(
                quotationExtraction.delivery_requested,
              )}
            </p>

            <p>
              <strong>
                Payment terms requested:
              </strong>{' '}
              {yesNo(
                quotationExtraction.payment_terms_requested,
              )}
            </p>

            <p>
              <strong>Confidence:</strong>{' '}
              {Math.round(
                quotationExtraction.confidence * 100,
              )}
              %
            </p>
          </div>

          <div className="quotation-workflow-actions">
            <button
              type="button"
              className="primary-button"
              onClick={() =>
                void handlePreviewQuotation()
              }
              disabled={previewingQuotation}
            >
              {previewingQuotation
                ? 'Preparing Preview…'
                : quotationPreview
                  ? 'Refresh Quotation Preview'
                  : 'Preview Quotation'}
            </button>
          </div>
        </section>
      )}

      {quotationPreview && (
        <section
          className="quotation-preview-card"
          aria-label="Quotation preview"
        >
          <p className="eyebrow">
            Quotation Preview
          </p>

          <h2>
            Review before creating
          </h2>

          <div className="quotation-requirements-grid">
            <p>
              <strong>Customer:</strong>{' '}
              {quotationPreview.customer_name}
            </p>

            <p>
              <strong>Email:</strong>{' '}
              {quotationPreview.customer_email ||
                'Not available'}
            </p>

            <p>
              <strong>Product:</strong>{' '}
              {quotationPreview.product_name}
            </p>

            <p>
              <strong>Quantity:</strong>{' '}
              {quotationPreview.quantity}
            </p>

            <p>
              <strong>Unit:</strong>{' '}
              {quotationPreview.unit}
            </p>

            <p>
              <strong>Unit price:</strong>{' '}
              {formatMoney(
                quotationPreview.unit_price,
                quotationPreview.currency,
              )}
            </p>

            <p>
              <strong>Tax rate:</strong>{' '}
              {quotationPreview.tax_rate}%
            </p>

            <p>
              <strong>Subtotal:</strong>{' '}
              {formatMoney(
                quotationPreview.subtotal,
                quotationPreview.currency,
              )}
            </p>

            <p>
              <strong>Tax:</strong>{' '}
              {formatMoney(
                quotationPreview.tax_amount,
                quotationPreview.currency,
              )}
            </p>

            <p>
              <strong>Total:</strong>{' '}
              {formatMoney(
                quotationPreview.total_amount,
                quotationPreview.currency,
              )}
            </p>
          </div>

          <p className="quotation-review-warning">
            Review the customer, product, quantity,
            pricing and tax before creating the quotation.
          </p>

          <div className="quotation-workflow-actions">
            <button
              type="button"
              className="primary-button"
              onClick={() =>
                void handleCreateQuotation()
              }
              disabled={
                creatingQuotation ||
                createdQuotation !== null
              }
            >
              {creatingQuotation
                ? 'Creating Quotation…'
                : createdQuotation
                  ? 'Quotation Created'
                  : 'Create Quotation'}
            </button>
          </div>
        </section>
      )}

      {createdQuotation && (
        <section
          className="quotation-created-card"
          aria-label="Created quotation"
        >
          <p className="eyebrow">
            Quotation Created
          </p>

          <h2>
            {createdQuotation.quotation_number}
          </h2>

          <p>
            <strong>Status:</strong>{' '}
            {createdQuotation.status}
          </p>

          <div className="quotation-workflow-actions">
            {createdQuotation.status === 'draft' && (
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleUpdateQuotationStatus('reviewed')
                }
                disabled={updatingQuotationStatus}
              >
                {updatingQuotationStatus
                  ? 'Updating Status…'
                  : 'Mark as Reviewed'}
              </button>
            )}

            {createdQuotation.status === 'reviewed' && (
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleUpdateQuotationStatus('approved')
                }
                disabled={updatingQuotationStatus}
              >
                {updatingQuotationStatus
                  ? 'Updating Status…'
                  : 'Approve Quotation'}
              </button>
            )}

            {createdQuotation.status === 'approved' && (
              <button
                type="button"
                className="primary-button"
                onClick={() =>
                  void handleUpdateQuotationStatus('sent')
                }
                disabled={updatingQuotationStatus}
              >
                {updatingQuotationStatus
                  ? 'Updating Status…'
                  : 'Mark as Sent'}
              </button>
            )}
          </div>

          <p>
            The quotation is saved as a draft.
            You can download the PDF or create a Gmail
            draft with the PDF attached.
          </p>

          <div className="quotation-workflow-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                void handleDownloadPdf()
              }
              disabled={downloadingPdf}
            >
              {downloadingPdf
                ? 'Downloading PDF…'
                : 'Download Quotation PDF'}
            </button>

            <button
              type="button"
              className="primary-button"
              onClick={() =>
                void handleCreateQuotationDraft()
              }
              disabled={
                creatingQuotationDraft ||
                quotationDraft !== null
              }
            >
              {creatingQuotationDraft
                ? 'Creating Gmail Draft…'
                : quotationDraft
                  ? 'Gmail Draft Created'
                  : 'Create Gmail Draft with PDF'}
            </button>
          </div>

          <p className="quotation-review-warning">
            Creating the Gmail draft does not send the
            email. Review it in Gmail and send manually.
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