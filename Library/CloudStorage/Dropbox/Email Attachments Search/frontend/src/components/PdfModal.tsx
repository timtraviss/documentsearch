import { useEffect, useRef, useState } from 'react'
import {
  ActionIcon,
  Autocomplete,
  Box,
  Button,
  Divider,
  Drawer,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import {
  IconChevronLeft,
  IconChevronRight,
  IconDeviceFloppy,
  IconDownload,
  IconTag,
} from '@tabler/icons-react'
import * as pdfjsLib from 'pdfjs-dist'
import { getTags, saveTags, pdfUrl } from '../api'
import type { DocumentTags, SearchResult } from '../types'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString()

const DOC_TYPES = [
  { value: '', label: '— select —' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'receipt', label: 'Receipt' },
  { value: 'contract', label: 'Contract' },
  { value: 'quote', label: 'Quote' },
  { value: 'statement', label: 'Statement' },
  { value: 'other', label: 'Other' },
]

const YEAR_OPTIONS = [
  { value: '', label: '— select —' },
  ...Array.from({ length: 31 }, (_, i) => {
    const y = String(2030 - i)
    return { value: y, label: y }
  }),
]

function formatAmount(raw: string): string {
  if (!raw) return ''
  const num = parseFloat(raw.replace(/[^0-9.]/g, ''))
  if (isNaN(num)) return raw
  return `$${num.toFixed(2)}`
}

interface Props {
  doc: SearchResult | null
  companies: string[]
  onClose: () => void
  onTagsSaved: (path: string, tags: DocumentTags) => void
}

export default function PdfModal({ doc, companies, onClose, onTagsSaved }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pdfDocRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null)
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState(1)
  const [pdfError, setPdfError] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [tagDrawerOpen, setTagDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const form = useForm<DocumentTags>({
    initialValues: { type: '', company: '', year: '', amount: '', invoice_number: '', notes: '' },
  })

  // Load PDF when doc changes
  useEffect(() => {
    if (!doc) return
    setPdfError(null)
    setPdfLoading(true)
    setPage(1)
    pdfDocRef.current = null

    pdfjsLib
      .getDocument(pdfUrl(doc.path))
      .promise.then((pdf) => {
        pdfDocRef.current = pdf
        setNumPages(pdf.numPages)
        setPdfLoading(false)
        renderPage(1, pdf)
      })
      .catch((err) => {
        setPdfLoading(false)
        const msg: string = err?.message ?? String(err)
        const isPermission = msg.includes('403') || msg.toLowerCase().includes('permission')
        setPdfError(
          isPermission
            ? 'macOS permission denied. Grant Full Disk Access in System Settings → Privacy & Security → Full Disk Access, then relaunch the app.'
            : `PDF error: ${msg}`
        )
      })

    // Load tags
    getTags(doc.path)
      .then((t) => {
        form.setValues({
          type: t.type ?? doc.tags?.type ?? '',
          company: t.company ?? doc.tags?.company ?? doc.company ?? '',
          year: t.year ?? doc.tags?.year ?? '',
          amount: t.amount ?? doc.amount ?? '',
          invoice_number: t.invoice_number ?? '',
          notes: t.notes ?? '',
        })
      })
      .catch(() => {
        // Fall back to search result tags
        form.setValues({
          type: doc.tags?.type ?? '',
          company: doc.tags?.company ?? doc.company ?? '',
          year: doc.tags?.year ?? '',
          amount: doc.tags?.amount ?? doc.amount ?? '',
          invoice_number: '',
          notes: '',
        })
      })
  }, [doc?.path])

  async function renderPage(pageNum: number, pdf?: pdfjsLib.PDFDocumentProxy) {
    const pdfDoc = pdf ?? pdfDocRef.current
    if (!pdfDoc || !canvasRef.current) return
    const p = await pdfDoc.getPage(pageNum)
    const viewport = p.getViewport({ scale: 1.5 })
    const canvas = canvasRef.current
    canvas.width = viewport.width
    canvas.height = viewport.height
    await p.render({ canvasContext: canvas.getContext('2d')!, viewport, canvas }).promise
    setPage(pageNum)
  }

  const handlePageChange = (delta: number) => {
    const next = page + delta
    if (next < 1 || next > numPages) return
    renderPage(next)
  }

  const handleSave = async () => {
    if (!doc) return
    setSaving(true)
    try {
      const values = {
        ...form.values,
        amount: formatAmount(form.values.amount ?? ''),
      }
      await saveTags(doc.path, values)
      form.setFieldValue('amount', values.amount ?? '')
      onTagsSaved(doc.path, values)
      notifications.show({ color: 'teal', message: '✓ Labels saved' })
      setTagDrawerOpen(false)
    } catch (e: unknown) {
      notifications.show({ color: 'red', message: 'Failed to save labels' })
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = () => {
    if (!doc) return
    const a = document.createElement('a')
    a.href = pdfUrl(doc.path)
    a.download = doc.filename
    a.click()
  }

  if (!doc) return null

  return (
    <>
      <Modal
        opened={!!doc}
        onClose={onClose}
        size="90vw"
        padding={0}
        withCloseButton={false}
        styles={{
          content: { maxWidth: 1100, height: '88vh', display: 'flex', flexDirection: 'column' },
          body: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 },
        }}
      >
        {/* Header */}
        <Group
          justify="space-between"
          px="lg"
          py="sm"
          style={{ borderBottom: '1px solid var(--border)', flexShrink: 0 }}
        >
          <Title order={4} style={{ fontFamily: '"DM Serif Display", serif', fontWeight: 400 }} lineClamp={1}>
            {doc.filename}
          </Title>
          <Group gap="xs">
            <Button
              size="xs"
              variant="light"
              color="teal"
              leftSection={<IconTag size={13} />}
              onClick={() => setTagDrawerOpen(true)}
            >
              Edit labels
            </Button>
            <ActionIcon variant="default" size="md" title="Download" onClick={handleDownload}>
              <IconDownload size={14} />
            </ActionIcon>
            <ActionIcon variant="default" size="md" title="Close" onClick={onClose}>
              ×
            </ActionIcon>
          </Group>
        </Group>

        {/* PDF canvas area */}
        <Box
          style={{
            flex: 1,
            overflow: 'auto',
            background: '#e8e4dc',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '1rem',
            gap: '0.75rem',
          }}
        >
          {pdfLoading && <Loader mt="xl" />}

          {pdfError && (
            <Box
              p="lg"
              style={{
                background: '#fff8f6',
                border: '1px solid #fca5a5',
                borderRadius: 6,
                maxWidth: 480,
                color: '#991b1b',
                fontSize: 14,
                lineHeight: 1.6,
              }}
            >
              {pdfError}
            </Box>
          )}

          {/* Page controls — only shown once loaded */}
          {!pdfLoading && !pdfError && numPages > 1 && (
            <Group gap="sm">
              <ActionIcon
                variant="filled"
                color="teal"
                disabled={page <= 1}
                onClick={() => handlePageChange(-1)}
              >
                <IconChevronLeft size={16} />
              </ActionIcon>
              <Text size="sm" style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}>
                Page {page} of {numPages}
              </Text>
              <ActionIcon
                variant="filled"
                color="teal"
                disabled={page >= numPages}
                onClick={() => handlePageChange(1)}
              >
                <IconChevronRight size={16} />
              </ActionIcon>
            </Group>
          )}

          {/* Canvas is always mounted so the ref is valid when renderPage fires */}
          <canvas
            ref={canvasRef}
            style={{
              display: pdfLoading || !!pdfError ? 'none' : 'block',
              maxWidth: '100%',
              boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
              borderRadius: 2,
            }}
          />
        </Box>
      </Modal>

      {/* Tag editor drawer — slides in over the modal */}
      <Drawer
        opened={tagDrawerOpen}
        onClose={() => setTagDrawerOpen(false)}
        title="Edit labels"
        position="right"
        size="sm"
        styles={{
          title: { fontFamily: '"DM Serif Display", serif', fontSize: 20, fontWeight: 400 },
          body: { paddingTop: '1rem' },
        }}
      >
        <Stack gap="md">
          {/* Auto-detected values from document */}
          {(doc.company || doc.amount || doc.date) && (
            <Box
              p="sm"
              style={{
                background: '#EDF8F8',
                border: '1px solid #b2dede',
                borderRadius: 6,
                fontSize: 12,
                color: 'var(--ink-muted)',
                lineHeight: 1.7,
              }}
            >
              <Text size="xs" fw={600} mb={4} c="teal">Auto-detected from document</Text>
              {doc.company && <div>Company: <strong>{doc.company}</strong></div>}
              {doc.amount && <div>Amount: <strong>{doc.amount}</strong></div>}
              {doc.date && <div>Date: <strong>{doc.date}</strong></div>}
            </Box>
          )}

          <Select
            label="Document type"
            data={DOC_TYPES}
            {...form.getInputProps('type')}
          />

          <Autocomplete
            label="Company"
            placeholder="e.g. Spark NZ"
            data={companies}
            {...form.getInputProps('company')}
          />

          <Select
            label="Year"
            data={YEAR_OPTIONS}
            {...form.getInputProps('year')}
          />

          <TextInput
            label="Amount"
            placeholder="e.g. $123.45"
            {...form.getInputProps('amount')}
            onBlur={() =>
              form.setFieldValue('amount', formatAmount(form.values.amount ?? ''))
            }
          />

          <TextInput
            label="Invoice number"
            placeholder="e.g. INV-1234"
            {...form.getInputProps('invoice_number')}
          />

          <Divider />

          <Button
            fullWidth
            color="teal"
            leftSection={<IconDeviceFloppy size={15} />}
            loading={saving}
            onClick={handleSave}
          >
            Save labels
          </Button>
        </Stack>
      </Drawer>
    </>
  )
}
