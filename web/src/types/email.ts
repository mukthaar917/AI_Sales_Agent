export interface GmailSyncResponse {
  fetched: number
  created: number
  updated: number
  skipped: number
  failed: number
}

export interface EmailMessage {
  id: string
  thread_id: string
  provider_message_id: string
  provider_thread_id: string
  internet_message_id: string | null
  in_reply_to: string | null
  references_header: string | null
  sender_name: string | null
  sender_email: string | null
  recipient_emails: string[]
  cc_emails: string[]
  subject: string | null
  text_body: string | null
  html_body: string | null
  received_at: string | null
  sent_at: string | null
  direction: string
  unread: boolean
  has_attachments: boolean
  created_at: string
  updated_at: string
}

export interface EmailThreadSummary {
  id: string
  provider_thread_id: string
  subject: string | null
  snippet: string | null
  participant_emails: string[]
  last_message_at: string | null
  unread: boolean
  message_count: number
  created_at: string
  updated_at: string
}

export interface EmailThreadListResponse {
  items: EmailThreadSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface EmailThreadDetail {
  id: string
  provider_thread_id: string
  subject: string | null
  snippet: string | null
  participant_emails: string[]
  last_message_at: string | null
  unread: boolean
  created_at: string
  updated_at: string
  messages: EmailMessage[]
}

export interface ThreadListParams {
  page?: number
  page_size?: number
  search?: string
  sender?: string
  unread?: boolean
}

export interface EmailThreadSummaryResponse {
  thread_id: string
  summary: string
  message_count: number
}