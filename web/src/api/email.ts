import { apiClient } from './client'
import type {
  CreateQuotationFromThreadResponse,
  DraftReplyRequest,
  DraftReplyResponse,
  EmailMessage,
  EmailThreadDetail,
  EmailThreadListResponse,
  EmailThreadSummaryResponse,
  GmailSyncResponse,
  QuotationDraftRequest,
  QuotationDraftResponse,
  QuotationExtractionResponse,
  QuotationPreviewResponse,
  ReplySuggestionsResponse,
  SalesOpportunityResponse,
  ThreadListParams,
} from '../types/email'

export async function syncInbox(
  maxResults = 25,
): Promise<GmailSyncResponse> {
  const response = await apiClient.post<GmailSyncResponse>(
    '/email/sync',
    null,
    {
      params: {
        max_results: maxResults,
      },
    },
  )

  return response.data
}

export async function getEmailThreads(
  params: ThreadListParams = {},
): Promise<EmailThreadListResponse> {
  const response =
    await apiClient.get<EmailThreadListResponse>(
      '/email/threads',
      {
        params,
      },
    )

  return response.data
}

export async function getEmailThread(
  threadId: string,
): Promise<EmailThreadDetail> {
  const response = await apiClient.get<EmailThreadDetail>(
    `/email/threads/${threadId}`,
  )

  return response.data
}

export async function summarizeThread(
  threadId: string,
): Promise<EmailThreadSummaryResponse> {
  const response =
    await apiClient.post<EmailThreadSummaryResponse>(
      `/email/threads/${threadId}/summary`,
    )

  return response.data
}

export async function getReplySuggestions(
  threadId: string,
): Promise<ReplySuggestionsResponse> {
  const response =
    await apiClient.post<ReplySuggestionsResponse>(
      `/email/threads/${threadId}/reply-suggestions`,
    )

  return response.data
}

export async function detectSalesOpportunity(
  threadId: string,
): Promise<SalesOpportunityResponse> {
  const response =
    await apiClient.post<SalesOpportunityResponse>(
      `/email/threads/${threadId}/sales-opportunity`,
    )

  return response.data
}

export async function extractQuotationRequirements(
  threadId: string,
): Promise<QuotationExtractionResponse> {
  const response =
    await apiClient.post<QuotationExtractionResponse>(
      `/email/threads/${threadId}/quotation-extraction`,
    )

  return response.data
}

export async function previewQuotation(
  threadId: string,
): Promise<QuotationPreviewResponse> {
  const response =
    await apiClient.post<QuotationPreviewResponse>(
      `/email/threads/${threadId}/quotation-preview`,
    )

  return response.data
}

export async function createQuotationFromThread(
  threadId: string,
): Promise<CreateQuotationFromThreadResponse> {
  const response =
    await apiClient.post<CreateQuotationFromThreadResponse>(
      `/email/threads/${threadId}/quotation`,
    )

  return response.data
}

export async function createQuotationDraft(
  threadId: string,
  payload: QuotationDraftRequest,
): Promise<QuotationDraftResponse> {
  const response =
    await apiClient.post<QuotationDraftResponse>(
      `/email/threads/${threadId}/quotation-draft`,
      payload,
    )

  return response.data
}

export async function downloadQuotationPdf(
  quotationId: string,
): Promise<Blob> {
  const response = await apiClient.get<Blob>(
    `/quotations/${quotationId}/pdf`,
    {
      responseType: 'blob',
    },
  )

  return response.data
}

export async function createDraftReply(
  threadId: string,
  payload: DraftReplyRequest,
): Promise<DraftReplyResponse> {
  const response = await apiClient.post<DraftReplyResponse>(
    `/email/threads/${threadId}/draft-reply`,
    payload,
  )

  return response.data
}

export async function getEmailMessage(
  messageId: string,
): Promise<EmailMessage> {
  const response = await apiClient.get<EmailMessage>(
    `/email/messages/${messageId}`,
  )

  return response.data
}