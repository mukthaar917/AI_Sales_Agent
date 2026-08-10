import { apiClient } from './client'
import type {
  EmailMessage,
  EmailThreadDetail,
  EmailThreadListResponse,
  EmailThreadSummaryResponse,
  GmailSyncResponse,
  ReplySuggestionsResponse,
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
  const response = await apiClient.get<EmailThreadListResponse>(
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

export async function getEmailMessage(
  messageId: string,
): Promise<EmailMessage> {
  const response = await apiClient.get<EmailMessage>(
    `/email/messages/${messageId}`,
  )

  return response.data
}