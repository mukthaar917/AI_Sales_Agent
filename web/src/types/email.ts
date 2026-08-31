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

export interface ReplySuggestion {
  subject: string
  body: string
}

export interface ReplySuggestionsResponse {
  thread_id: string
  suggestions: ReplySuggestion[]
}

export interface DraftReplyRequest {
  subject: string
  body: string
}

export interface DraftReplyResponse {
  thread_id: string
  draft_id: string
  message_id: string | null
  status: string
}

export interface SalesOpportunityResponse {
  thread_id: string
  classification:
    | 'sales_opportunity'
    | 'non_sales'
    | 'unknown'
  confidence: number
  reason: string
}

export interface QuotationExtractionResponse {
  thread_id: string
  product: string | null
  quantity: number | null
  pricing_requested: boolean
  availability_requested: boolean
  delivery_requested: boolean
  payment_terms_requested: boolean
  confidence: number
}

export interface QuotationPreviewResponse {
  thread_id: string

  customer_id: string
  customer_name: string
  customer_email: string | null

  product_id: string
  product_name: string

  quantity: string
  unit: string
  unit_price: string
  currency: string
  tax_rate: string

  subtotal: string
  tax_amount: string
  total_amount: string
}

export interface CreateQuotationFromThreadResponse {
  thread_id: string
  quotation_id: string
  quotation_number: string
  status: string
}

export type QuotationStatus =
  | 'draft'
  | 'reviewed'
  | 'approved'
  | 'sent'
  | 'accepted'
  | 'rejected'
  | 'expired'
  | 'cancelled'

export interface QuotationStatusUpdateRequest {
  status: QuotationStatus
}

export interface QuotationStatusUpdateResponse {
  id: string
  quotation_number: string
  status: QuotationStatus
}

export interface QuotationDraftRequest {
  quotation_id: string
}

export interface QuotationDraftResponse {
  thread_id: string
  quotation_id: string
  quotation_number: string

  draft_id: string
  message_id: string | null

  recipient: string
  attachment_filename: string

  status: string
}