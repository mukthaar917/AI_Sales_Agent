import { apiClient } from './client'

export interface KnowledgeDocument {
  id: string
  organization_id: string
  uploaded_by: string
  filename: string
  original_filename: string
  mime_type: string
  file_size: number
  status: string
  title: string | null
  checksum: string
  created_at: string
  updated_at: string
}

export interface KnowledgeDocumentListResponse {
  items: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
}

export interface RAGSource {
  document_id: string
  chunk_id: string
  filename: string
  page: number | null
  score: number
}

export interface RAGAnswerResponse {
  answer: string
  insufficient_knowledge: boolean
  sources: RAGSource[]
}

export async function getKnowledgeDocuments() {
  const response =
    await apiClient.get<KnowledgeDocumentListResponse>(
      '/v1/knowledge/documents',
      {
        params: {
          page: 1,
          page_size: 100,
        },
      },
    )

  return response.data
}

export async function uploadKnowledgeDocument(
  file: File,
  title?: string,
) {
  const formData = new FormData()

  formData.append('file', file)

  if (title?.trim()) {
    formData.append('title', title.trim())
  }

  const response =
    await apiClient.post<KnowledgeDocument>(
      '/v1/knowledge/documents',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      },
    )

  return response.data
}

export async function askKnowledge(
  question: string,
): Promise<RAGAnswerResponse> {
  const response =
    await apiClient.post<RAGAnswerResponse>(
      '/v1/knowledge/answer',
      {
        question,
        limit: 3,
      },
    )

  return response.data
}

export async function deleteKnowledgeDocument(
  id: string,
): Promise<void> {
  await apiClient.delete(
    `/v1/knowledge/documents/${id}`,
  )
}