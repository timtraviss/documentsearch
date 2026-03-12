import { useState } from 'react'
import {
  Box,
  Button,
  Checkbox,
  Collapse,
  Group,
  Menu,
  Select,
  SimpleGrid,
  TextInput,
} from '@mantine/core'
import {
  IconAdjustments,
  IconChartBar,
  IconRefresh,
  IconSearch,
  IconTag,
  IconTools,
  IconX,
} from '@tabler/icons-react'
import type { SearchFilters } from '../types'

const DOC_TYPES = [
  { value: '', label: 'All types' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'receipt', label: 'Receipt' },
  { value: 'contract', label: 'Contract' },
  { value: 'quote', label: 'Quote' },
  { value: 'statement', label: 'Statement' },
  { value: 'other', label: 'Other' },
]

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'date_desc', label: 'Date: Newest first' },
  { value: 'date_asc', label: 'Date: Oldest first' },
  { value: 'company', label: 'Company A–Z' },
  { value: 'year', label: 'Year: Newest first' },
]

interface Props {
  filters: SearchFilters
  tagYears: string[]
  resultCount: number | null
  isIndexing: boolean
  onSearch: (filters: SearchFilters) => void
  onClear: () => void
  onExportCsv: () => void
  onOpenReindex: () => void
  onOpenTagMgmt: () => void
  onOpenStats: () => void
}

export default function SearchBar({
  filters,
  tagYears,
  resultCount,
  isIndexing,
  onSearch,
  onClear,
  onExportCsv,
  onOpenReindex,
  onOpenTagMgmt,
  onOpenStats,
}: Props) {
  const [showFilters, setShowFilters] = useState(false)
  const [local, setLocal] = useState<SearchFilters>(filters)

  const set = (key: keyof SearchFilters, value: string | boolean) =>
    setLocal((f) => ({ ...f, [key]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(local)
  }

  const handleClear = () => {
    const reset: SearchFilters = {
      q: '', company: '', date: '', amount: '',
      mode: 'and', tag_type: '', tag_year: '',
      tag_untagged: false, sort: 'relevance',
    }
    setLocal(reset)
    onClear()
  }

  const yearOptions = [
    { value: '', label: 'All years' },
    ...tagYears.map((y) => ({ value: y, label: y })),
  ]

  return (
    <Box component="form" onSubmit={handleSubmit}>
      {/* Main search row */}
      <Group gap="xs" wrap="nowrap">
        <TextInput
          flex={1}
          placeholder="Search by keyword, vendor, amount, date…"
          value={local.q}
          onChange={(e) => set('q', e.currentTarget.value)}
          size="md"
          styles={{
            input: {
              fontFamily: 'var(--mantine-font-family)',
              background: 'var(--card-bg)',
              borderColor: 'var(--border)',
            },
          }}
        />
        <Button type="submit" size="md" color="teal">
          <IconSearch size={16} />
        </Button>
        <Button size="md" variant="default" onClick={handleClear} title="Clear">
          <IconX size={16} />
        </Button>
        <Button
          size="md"
          variant={showFilters ? 'filled' : 'default'}
          color={showFilters ? 'teal' : undefined}
          onClick={() => setShowFilters((s) => !s)}
          leftSection={<IconAdjustments size={15} />}
        >
          Filters
        </Button>

        {/* Tools menu */}
        <Menu shadow="md" width={180} position="bottom-end">
          <Menu.Target>
            <Button
              size="md"
              variant="default"
              leftSection={<IconTools size={15} />}
              rightSection={
                isIndexing ? (
                  <Box
                    component="span"
                    style={{
                      fontSize: 11,
                      color: '#6366f1',
                      background: '#ede9fe',
                      borderRadius: 8,
                      padding: '1px 6px',
                    }}
                  >
                    indexing…
                  </Box>
                ) : undefined
              }
            >
              Tools
            </Button>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item leftSection={<IconRefresh size={14} />} onClick={onOpenReindex}>
              Re-index PDFs
            </Menu.Item>
            <Menu.Item leftSection={<IconTag size={14} />} onClick={onOpenTagMgmt}>
              Manage tags
            </Menu.Item>
            <Menu.Item leftSection={<IconChartBar size={14} />} onClick={onOpenStats}>
              Stats dashboard
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>

      {/* Advanced filters */}
      <Collapse in={showFilters}>
        <Box
          mt="sm"
          p="md"
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}
        >
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
            <TextInput
              label="Company / Vendor"
              placeholder="e.g. Acme Corp"
              value={local.company}
              onChange={(e) => set('company', e.currentTarget.value)}
              size="sm"
            />
            <TextInput
              label="Year or Date"
              placeholder="e.g. 2025 or 2025-03"
              value={local.date}
              onChange={(e) => set('date', e.currentTarget.value)}
              size="sm"
            />
            <TextInput
              label="Amount (min–max)"
              placeholder="e.g. 1000-5000"
              value={local.amount}
              onChange={(e) => set('amount', e.currentTarget.value)}
              size="sm"
            />
            <Select
              label="Document type"
              data={DOC_TYPES}
              value={local.tag_type}
              onChange={(v) => set('tag_type', v ?? '')}
              size="sm"
            />
            <Select
              label="Tag year"
              data={yearOptions}
              value={local.tag_year}
              onChange={(v) => set('tag_year', v ?? '')}
              size="sm"
            />
            <Box>
              <Box mb={6} style={{ fontSize: 14, fontWeight: 500, color: 'var(--ink-muted)' }}>
                Options
              </Box>
              <Group gap="lg">
                <Checkbox
                  label="Match any (OR)"
                  checked={local.mode === 'or'}
                  onChange={(e) => set('mode', e.currentTarget.checked ? 'or' : 'and')}
                  size="sm"
                />
                <Checkbox
                  label="Untagged only"
                  checked={local.tag_untagged}
                  onChange={(e) => set('tag_untagged', e.currentTarget.checked)}
                  size="sm"
                />
              </Group>
            </Box>
          </SimpleGrid>
        </Box>
      </Collapse>

      {/* Results header */}
      {resultCount !== null && (
        <Group justify="space-between" mt="sm">
          <Box style={{ fontSize: 13, color: 'var(--ink-muted)' }}>
            {resultCount} {resultCount === 1 ? 'result' : 'results'} found
          </Box>
          <Group gap="xs">
            <Select
              size="xs"
              data={SORT_OPTIONS}
              value={local.sort}
              onChange={(v) => {
                const next = { ...local, sort: (v ?? 'relevance') as SearchFilters['sort'] }
                setLocal(next)
                onSearch(next)
              }}
              styles={{ input: { borderColor: 'var(--border)' } }}
            />
            <Button size="xs" variant="default" onClick={onExportCsv}>
              ↓ Export CSV
            </Button>
          </Group>
        </Group>
      )}
    </Box>
  )
}
