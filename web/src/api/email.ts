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
  QuotationStatusUpdateRequest,
  QuotationStatusUpdateResponse,
  ReplySuggestionsResponse,
  SalesOpportunityResponse,
  ThreadListParams,
} from '../types/email'

export async function syncInbox(
  maxResults = 25,
): Promise<GmailSyncResponse> {
  const response = await apiClient.post<GmailSyncResponse>(
    '/v1/email/sync',
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
      '/v1/email/threads',
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
    `/v1/email/threads/${threadId}`,
  )

  return response.data
}

export async function summarizeThread(
  threadId: string,
): Promise<EmailThreadSummaryResponse> {
  const response =
    await apiClient.post<EmailThreadSummaryResponse>(
      `/v1/email/threads/${threadId}/summary`,
    )

  return response.data
}

export async function getReplySuggestions(
  threadId: string,
): Promise<ReplySuggestionsResponse> {
  const response =
    await apiClient.post<ReplySuggestionsResponse>(
      `/v1/email/threads/${threadId}/reply-suggestions`,
    )

  return response.data
}

export async function detectSalesOpportunity(
  threadId: string,
): Promise<SalesOpportunityResponse> {
  const response =
    await apiClient.post<SalesOpportunityResponse>(
      `/v1/email/threads/${threadId}/sales-opportunity`,
    )

  return response.data
}

export async function extractQuotationRequirements(
  threadId: string,
): Promise<QuotationExtractionResponse> {
  const response =
    await apiClient.post<QuotationExtractionResponse>(
      `/v1/email/threads/${threadId}/quotation-extraction`,
    )

  return response.data
}

export async function previewQuotation(
  threadId: string,
): Promise<QuotationPreviewResponse> {
  const response =
    await apiClient.post<QuotationPreviewResponse>(
      `/v1/email/threads/${threadId}/quotation-preview`,
    )

  return response.data
}

export async function createQuotationFromThread(
  threadId: string,
): Promise<CreateQuotationFromThreadResponse> {
  const response =
    await apiClient.post<CreateQuotationFromThreadResponse>(
      `/v1/email/threads/${threadId}/quotation`,
    )

  return response.data
}

export async function updateQuotationStatus(
  quotationId: string,
  payload: QuotationStatusUpdateRequest,
): Promise<QuotationStatusUpdateResponse> {
  const response =
    await apiClient.put<QuotationStatusUpdateResponse>(
      `/v1/quotations/${quotationId}`,
      payload,
    )

  return response.data
}

export async function createQuotationDraft(
  threadId: string,
  payload: QuotationDraftRequest,
): Promise<QuotationDraftResponse> {
  const response =
    await apiClient.post<QuotationDraftResponse>(
      `/v1/email/threads/${threadId}/quotation-draft`,
      payload,
    )

  return response.data
}

export async function downloadQuotationPdf(
  quotationId: string,
): Promise<Blob> {
  const response = await apiClient.get<Blob>(
    `/v1/quotations/${quotationId}/pdf`,
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
    `/v1/email/threads/${threadId}/draft-reply`,
    payload,
  )

  return response.data
}

export async function getEmailMessage(
  messageId: string,
): Promise<EmailMessage> {
  const response = await apiClient.get<EmailMessage>(
    `/v1/email/messages/${messageId}`,
  )

  return response.data
}