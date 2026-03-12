export interface DocumentTags {
  type?: string
  company?: string
  year?: string
  amount?: string
  invoice_number?: string
  status?: string
  notes?: string
}

export interface SearchResult {
  filename: string
  path: string
  relative_path?: string
  snippet: string
  // Extracted fields (from document text, not tags)
  amount?: string
  company?: string
  date?: string
  // Nested tags object from the API
  tags: DocumentTags
}

// The /search API returns a plain array
export type SearchResponse = SearchResult[]

export interface Stats {
  doc_count: number
  last_indexed: string | null
}

export interface TagValues {
  type: Record<string, number>
  company: Record<string, number>
  year: Record<string, number>
}

export interface ReindexStatus {
  running: boolean
  logs: string[]
  count: number
  skipped: number
  error: string | null
}

export interface StatsBreakdown {
  type: Record<string, number>
  company: Record<string, number>
  year: Record<string, number>
}

export type SortKey = 'relevance' | 'date_desc' | 'date_asc' | 'company' | 'year'
export type SearchMode = 'and' | 'or'

export interface SearchFilters {
  q: string
  company: string
  date: string
  amount: string
  mode: SearchMode
  tag_type: string
  tag_year: string
  tag_untagged: boolean
  sort: SortKey
}
