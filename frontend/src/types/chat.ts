export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  searchResults?: SearchResult[]
  isError?: boolean
  thinking?: string
  hasThinking?: boolean
}

export interface SearchResult {
  title: string
  url: string
  snippet: string
}

export interface StreamingResponse {
  type: 'status' | 'search_results' | 'token' | 'completed' | 'error'
  content: string | SearchResult[]
  search_results?: SearchResult[]
} 