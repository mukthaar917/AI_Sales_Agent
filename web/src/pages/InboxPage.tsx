import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { getEmailThreads, syncInbox } from '../api/email'
import type {
  EmailThreadListResponse,
  EmailThreadSummary,
} from '../types/email'

interface InboxPageProps {
  onOpenThread: (threadId: string) => void
}

function formatDate(value: string | null): string {
  if (!value) {
    return 'No date'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function InboxPage({
  onOpenThread,
}: InboxPageProps) {
  const [threads, setThreads] =
    useState<EmailThreadListResponse | null>(null)
  const [search, setSearch] = useState('')
  const [sender, setSender] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [syncMessage, setSyncMessage] =
    useState<string | null>(null)

  const query = useMemo(
    () => ({
      page,
      page_size: 20,
      search: search.trim() || undefined,
      sender: sender.trim() || undefined,
      unread: unreadOnly ? true : undefined,
    }),
    [page, search, sender, unreadOnly],
  )

  const loadThreads = useCallback(
    async (): Promise<void> => {
      try {
        setLoading(true)
        setError(null)

        const response = await getEmailThreads(query)

        setThreads(response)
      } catch {
        setError(
          'Unable to load the inbox. Check that the backend is running and you are authenticated.',
        )
      } finally {
        setLoading(false)
      }
    },
    [query],
  )

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadThreads()
    }, 300)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [loadThreads])

  async function handleSync(): Promise<void> {
    try {
      setSyncing(true)
      setError(null)
      setSyncMessage(null)

      const result = await syncInbox()

      setSyncMessage(
        `Fetched ${result.fetched}, created ${result.created}, updated ${result.updated}, skipped ${result.skipped}, failed ${result.failed}.`,
      )

      await loadThreads()
    } catch {
      setError('Unable to synchronize Gmail right now.')
    } finally {
      setSyncing(false)
    }
  }

  function renderThread(
    thread: EmailThreadSummary,
  ) {
    return (
      <button
        key={thread.id}
        type="button"
        className={`thread-row ${
          thread.unread ? 'thread-row-unread' : ''
        }`}
        onClick={() => onOpenThread(thread.id)}
      >
        <div className="thread-row-top">
          <strong>
            {thread.subject || '(No subject)'}
          </strong>
          <span>
            {formatDate(thread.last_message_at)}
          </span>
        </div>

        <div className="thread-participants">
          {thread.participant_emails.length > 0
            ? thread.participant_emails.join(', ')
            : 'No participants'}
        </div>

        <div className="thread-snippet">
          {thread.snippet || 'No preview available'}
        </div>

        <div className="thread-meta">
          <span>
            {thread.message_count}{' '}
            {thread.message_count === 1
              ? 'message'
              : 'messages'}
          </span>

          {thread.unread && (
            <span className="unread-badge">
              Unread
            </span>
          )}
        </div>
      </button>
    )
  }

  return (
    <main className="inbox-page">
      <header className="inbox-header">
        <div>
          <p className="eyebrow">
            AI Sales Agent
          </p>
          <h1>Inbox</h1>
          <p className="subtitle">
            Review synchronized Gmail conversations.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={() => void handleSync()}
          disabled={syncing}
        >
          {syncing ? 'Syncing…' : 'Sync Inbox'}
        </button>
      </header>

      <section className="filter-panel">
        <label>
          Search
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
            placeholder="Subject, snippet, or sender"
          />
        </label>

        <label>
          Sender
          <input
            type="email"
            value={sender}
            onChange={(event) => {
              setSender(event.target.value)
              setPage(1)
            }}
            placeholder="sender@example.com"
          />
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(event) => {
              setUnreadOnly(event.target.checked)
              setPage(1)
            }}
          />
          Unread only
        </label>
      </section>

      {syncMessage && (
        <div
          className="success-message"
          role="status"
        >
          {syncMessage}
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

      {loading ? (
        <div className="state-card">
          Loading inbox…
        </div>
      ) : threads && threads.items.length > 0 ? (
        <>
          <section
            className="thread-list"
            aria-label="Email threads"
          >
            {threads.items.map(renderThread)}
          </section>

          <footer className="pagination">
            <button
              type="button"
              onClick={() =>
                setPage((current) =>
                  Math.max(1, current - 1),
                )
              }
              disabled={page <= 1}
            >
              Previous
            </button>

            <span>
              Page {threads.page} of{' '}
              {Math.max(
                threads.total_pages,
                1,
              )}
            </span>

            <button
              type="button"
              onClick={() =>
                setPage(
                  (current) => current + 1,
                )
              }
              disabled={
                threads.total_pages === 0 ||
                page >= threads.total_pages
              }
            >
              Next
            </button>
          </footer>
        </>
      ) : (
        <div className="state-card">
          No synchronized email threads were found.
        </div>
      )}
    </main>
  )
}