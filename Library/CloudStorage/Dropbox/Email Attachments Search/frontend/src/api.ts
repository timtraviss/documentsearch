import type { SearchFilters, SearchResponse, DocumentTags, Stats, TagValues, ReindexStatus, StatsBreakdown } from './types'

const PAGE_SIZE = 20

function buildSearchParams(filters: Partial<SearchFilters>, offset = 0, limit = PAGE_SIZE): URLSearchParams {
  const p = new URLSearchParams()
  if (filters.q) p.set('q', filters.q)
  if (filters.company) p.set('company', filters.company)
  if (filters.date) p.set('date', filters.date)
  if (filters.amount) p.set('amount', filters.amount)
  if (filters.mode) p.set('mode', filters.mode)
  if (filters.tag_type) p.set('tag_type', filters.tag_type)
  if (filters.tag_year) p.set('tag_year', filters.tag_year)
  if (filters.tag_untagged) p.set('tag_untagged', '1')
  if (filters.sort && filters.sort !== 'relevance') p.set('sort', filters.sort)
  p.set('limit', String(limit))
  p.set('offset', String(offset))
  return p
}

export async function search(filters: Partial<SearchFilters>, offset = 0): Promise<SearchResponse> {
  const params = buildSearchParams(filters, offset)
  const res = await fetch(`/search?${params}`)
  if (!res.ok) throw new Error(`Search failed: ${res.status}`)
  return res.json()
}

export { PAGE_SIZE }

export async function exportCsv(filters: Partial<SearchFilters>): Promise<void> {
  const params = buildSearchParams(filters, 0, 9999)
  window.location.href = `/export/csv?${params}`
}

export async function getStats(): Promise<Stats> {
  const res = await fetch('/stats')
  if (!res.ok) throw new Error('Stats failed')
  return res.json()
}

export async function getStatsBreakdown(): Promise<StatsBreakdown> {
  const res = await fetch('/stats/breakdown')
  if (!res.ok) throw new Error('Stats breakdown failed')
  return res.json()
}

export async function getCompanies(): Promise<string[]> {
  const res = await fetch('/companies')
  if (!res.ok) throw new Error('Companies failed')
  return res.json()
}

export async function getTagValues(): Promise<TagValues> {
  const res = await fetch('/tag_values')
  if (!res.ok) throw new Error('Tag values failed')
  return res.json()
}

export async function getTags(path: string): Promise<DocumentTags> {
  const res = await fetch(`/tags/${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error('Get tags failed')
  return res.json()
}

export async function saveTags(path: string, tag: DocumentTags): Promise<void> {
  const res = await fetch(`/tags/${encodeURIComponent(path)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tag),
  })
  if (!res.ok) throw new Error('Save tags failed')
}

export async function bulkTags(paths: string[], tag: DocumentTags): Promise<void> {
  const res = await fetch('/bulk_tags', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths, ...tag }),
  })
  if (!res.ok) throw new Error('Bulk tags failed')
}

export async function renameTag(field: string, oldValue: string, newValue: string): Promise<void> {
  const res = await fetch('/rename_tag', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field, old_value: oldValue, new_value: newValue }),
  })
  if (!res.ok) throw new Error('Rename tag failed')
}

export async function startReindex(incremental: boolean): Promise<void> {
  const res = await fetch('/reindex', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ incremental }),
  })
  if (!res.ok) throw new Error('Reindex failed')
}

export async function getReindexStatus(): Promise<ReindexStatus> {
  const res = await fetch('/reindex/status')
  if (!res.ok) throw new Error('Reindex status failed')
  return res.json()
}

export function pdfUrl(path: string): string {
  return `/pdf/${encodeURIComponent(path)}`
}
