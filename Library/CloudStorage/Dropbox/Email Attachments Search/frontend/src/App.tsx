import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AppShell,
  Box,
  Button,
  Center,
  Container,
  Divider,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { motion, AnimatePresence } from 'framer-motion'
import SearchBar from './components/SearchBar'
import ResultCard from './components/ResultCard'
import WelcomeState from './components/WelcomeState'
import PdfModal from './components/PdfModal'
import ReindexModal from './components/ReindexModal'
import TagMgmt from './components/TagMgmt'
import StatsPanel from './components/StatsPanel'
import BulkToolbar from './components/BulkToolbar'
import {
  exportCsv,
  getCompanies,
  getStats,
  getTagValues,
  search,
  PAGE_SIZE,
} from './api'
import type { DocumentTags, SearchFilters, SearchResult, Stats } from './types'

const DEFAULT_FILTERS: SearchFilters = {
  q: '', company: '', date: '', amount: '',
  mode: 'and', tag_type: '', tag_year: '',
  tag_untagged: false, sort: 'relevance',
}

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [companies, setCompanies] = useState<string[]>([])
  const [tagYears, setTagYears] = useState<string[]>([])

  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS)
  const [results, setResults] = useState<SearchResult[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [isIndexing, setIsIndexing] = useState(false)
  const [showWelcome, setShowWelcome] = useState(true)

  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())
  const [viewingDoc, setViewingDoc] = useState<SearchResult | null>(null)
  const [reindexOpen, setReindexOpen] = useState(false)
  const [tagMgmtOpen, setTagMgmtOpen] = useState(false)
  const [statsOpen, setStatsOpen] = useState(false)
  const activeFiltersRef = useRef<SearchFilters>(DEFAULT_FILTERS)
  const resultCountRef = useRef(0)

  useEffect(() => {
    getStats().then(setStats).catch(() => {})
    getCompanies().then(setCompanies).catch(() => {})
    getTagValues()
      .then((tv) => setTagYears(Object.keys(tv.year).sort().reverse()))
      .catch(() => {})
  }, [])

  const runSearch = useCallback(async (f: SearchFilters, append = false) => {
    activeFiltersRef.current = f
    setFilters(f)
    setIsSearching(true)
    if (!append) {
      resultCountRef.current = 0
      setResults([])
      setTotal(null)
      setHasMore(false)
      setSelectedPaths(new Set())
      setShowWelcome(false)
    }
    try {
      const data = await search(f, append ? resultCountRef.current : 0)
      resultCountRef.current = (append ? resultCountRef.current : 0) + data.length
      setResults((prev) => (append ? [...prev, ...data] : data))
      setTotal((prev) => append ? (prev ?? 0) + data.length : data.length)
      setHasMore(data.length === PAGE_SIZE)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      notifications.show({ color: 'red', message: `Search failed: ${msg}` })
    } finally {
      setIsSearching(false)
    }
  }, [])

  const handleSearch = (f: SearchFilters) => runSearch(f, false)

  const handleQuickSearch = (q: string) => runSearch({ ...DEFAULT_FILTERS, q }, false)

  const handleClear = () => {
    setFilters(DEFAULT_FILTERS)
    setResults([])
    setTotal(null)
    setHasMore(false)
    setSelectedPaths(new Set())
    setShowWelcome(true)
    resultCountRef.current = 0
  }

  const toggleSelect = (path: string) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const handleView = (doc: SearchResult) => setViewingDoc(doc)

  const handleTagsSaved = (path: string, tags: DocumentTags) => {
    // Update the result in the list so badges/company reflect the save immediately
    setResults((prev) =>
      prev.map((r) => (r.path === path ? { ...r, tags: { ...r.tags, ...tags } } : r))
    )
    // Refresh company list for autocomplete
    getCompanies().then(setCompanies).catch(() => {})
  }

  return (
    <AppShell style={{ background: 'var(--page-bg)', minHeight: '100vh' }}>
      <AppShell.Main>
        <Container size="xl" py="xl">
          <Stack gap="xl">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <Group justify="space-between" align="flex-start">
                <Box>
                  <Title order={1} style={{ color: 'var(--ink)', lineHeight: 1.1 }}>
                    Document Search
                  </Title>
                  <Text c="dimmed" size="sm" mt={4}>
                    Find documents from your email attachments
                  </Text>
                </Box>
                {stats && (
                  <Box ta="right" style={{ fontSize: 12, color: 'var(--ink-muted)', lineHeight: 1.8 }}>
                    <div>{stats.doc_count} documents</div>
                    {stats.last_indexed && <div>Indexed {stats.last_indexed}</div>}
                  </Box>
                )}
              </Group>
            </motion.div>

            <Divider color="var(--border)" />

            {/* Search bar */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
            >
              <SearchBar
                filters={filters}
                tagYears={tagYears}
                resultCount={total}
                isIndexing={isIndexing}
                onSearch={handleSearch}
                onClear={handleClear}
                onExportCsv={() => exportCsv(filters)}
                onOpenReindex={() => setReindexOpen(true)}
                onOpenTagMgmt={() => setTagMgmtOpen(true)}
                onOpenStats={() => setStatsOpen(true)}
              />
            </motion.div>

            {/* Welcome state */}
            <AnimatePresence>
              {showWelcome && (
                <motion.div
                  key="welcome"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  <WelcomeState
                    stats={stats}
                    companies={companies}
                    onSearch={handleQuickSearch}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Loading */}
            {isSearching && results.length === 0 && (
              <Center py="xl">
                <Text c="dimmed" size="sm">Searching…</Text>
              </Center>
            )}

            {/* No results */}
            {!isSearching && !showWelcome && results.length === 0 && (
              <Center py="xl">
                <Text c="dimmed">No results found. Try different keywords or filters.</Text>
              </Center>
            )}

            {/* Results grid */}
            <AnimatePresence>
              {results.length > 0 && (
                <motion.div
                  key="results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
                    {results.map((doc, i) => (
                      <motion.div
                        key={doc.path}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }}
                      >
                        <ResultCard
                          doc={doc}
                          query={filters.q}
                          selected={selectedPaths.has(doc.path)}
                          onToggleSelect={toggleSelect}
                          onView={handleView}
                        />
                      </motion.div>
                    ))}
                  </SimpleGrid>

                  {hasMore && (
                    <Center mt="lg">
                      <Button
                        variant="default"
                        loading={isSearching}
                        onClick={() => runSearch(activeFiltersRef.current, true)}
                      >
                        Load more
                      </Button>
                    </Center>
                  )}

                  <BulkToolbar
                    selectedPaths={selectedPaths}
                    companies={companies}
                    onApplied={() => {
                      setSelectedPaths(new Set())
                      runSearch(activeFiltersRef.current, false)
                    }}
                    onDeselect={() => setSelectedPaths(new Set())}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </Stack>
        </Container>
      </AppShell.Main>

      <PdfModal
        doc={viewingDoc}
        companies={companies}
        onClose={() => setViewingDoc(null)}
        onTagsSaved={handleTagsSaved}
      />

      <ReindexModal
        opened={reindexOpen}
        onClose={() => { setReindexOpen(false); setIsIndexing(false) }}
        onComplete={() => {
          setIsIndexing(false)
          getStats().then(setStats).catch(() => {})
          getCompanies().then(setCompanies).catch(() => {})
          getTagValues().then((tv) => setTagYears(Object.keys(tv.year).sort().reverse())).catch(() => {})
        }}
      />

      <TagMgmt
        opened={tagMgmtOpen}
        onClose={() => setTagMgmtOpen(false)}
        onRenamed={() => {
          getCompanies().then(setCompanies).catch(() => {})
          getTagValues().then((tv) => setTagYears(Object.keys(tv.year).sort().reverse())).catch(() => {})
        }}
      />

      <StatsPanel
        opened={statsOpen}
        onClose={() => setStatsOpen(false)}
      />
    </AppShell>
  )
}
