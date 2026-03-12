import { useEffect, useRef, useState } from 'react'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Group,
  Stack,
  Text,
} from '@mantine/core'
import { IconDownload, IconEye, IconTag } from '@tabler/icons-react'
import * as pdfjsLib from 'pdfjs-dist'
import type { SearchResult } from '../types'
import { pdfUrl } from '../api'

// Set up PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString()

const TYPE_COLORS: Record<string, string> = {
  invoice: 'teal',
  receipt: 'green',
  contract: 'blue',
  quote: 'orange',
  statement: 'grape',
  other: 'gray',
}

function highlightSnippet(text: string, q: string): React.ReactNode {
  if (!q.trim()) return text
  const words = q.trim().split(/\s+/).filter(Boolean)
  const pattern = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
  const parts = text.split(pattern)
  return parts.map((part, i) =>
    pattern.test(part) ? (
      <mark key={i} style={{ background: '#FFF3A3', color: 'inherit', borderRadius: 2, padding: '0 1px' }}>
        {part}
      </mark>
    ) : (
      part
    )
  )
}

interface Props {
  doc: SearchResult
  query: string
  selected: boolean
  onToggleSelect: (path: string) => void
  onView: (doc: SearchResult) => void
}

export default function ResultCard({ doc, query, selected, onToggleSelect, onView }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [thumbFailed, setThumbFailed] = useState(false)

  const company = doc.tags?.company || doc.company || ''
  const amount = doc.tags?.amount || doc.amount || ''
  const tagType = doc.tags?.type || ''
  const tagYear = doc.tags?.year || ''
  const typeColor = TYPE_COLORS[tagType] ?? 'gray'

  // Render PDF thumbnail
  useEffect(() => {
    if (!canvasRef.current || thumbFailed) return
    let cancelled = false

    const url = pdfUrl(doc.path)
    pdfjsLib
      .getDocument({ url, disableAutoFetch: true, disableStream: true })
      .promise.then((pdf) => pdf.getPage(1))
      .then((page) => {
        if (cancelled || !canvasRef.current) return
        const viewport = page.getViewport({ scale: 0.5 })
        const canvas = canvasRef.current
        canvas.width = viewport.width
        canvas.height = viewport.height
        const ctx = canvas.getContext('2d')!
        return page.render({ canvasContext: ctx, viewport, canvas }).promise
      })
      .catch(() => {
        if (!cancelled) setThumbFailed(true)
      })

    return () => { cancelled = true }
  }, [doc.path, thumbFailed])

  const handleDownload = () => {
    const a = document.createElement('a')
    a.href = pdfUrl(doc.path)
    a.download = doc.filename
    a.click()
  }

  return (
    <Card
      radius="sm"
      withBorder
      style={{
        background: selected ? '#EDF8F8' : 'var(--card-bg)',
        borderColor: selected ? 'var(--accent)' : 'var(--border)',
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      <Group gap="sm" align="flex-start" wrap="nowrap">
        {/* Checkbox */}
        <Checkbox
          checked={selected}
          onChange={() => onToggleSelect(doc.path)}
          mt={4}
          styles={{ input: { cursor: 'pointer' } }}
        />

        {/* Thumbnail */}
        <Box
          style={{
            width: 64,
            minWidth: 64,
            height: 80,
            background: '#f0ede6',
            border: '1px solid var(--border)',
            borderRadius: 3,
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {thumbFailed ? (
            <Text size="xs" c="dimmed" ta="center" px={4}>PDF</Text>
          ) : (
            <canvas
              ref={canvasRef}
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
            />
          )}
        </Box>

        {/* Content */}
        <Stack gap={4} flex={1} style={{ minWidth: 0 }}>
          {/* Company + amount row */}
          <Group gap="xs" justify="space-between" wrap="nowrap">
            <Text
              fw={600}
              size="md"
              style={{ color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
            >
              {company || <Text component="span" c="dimmed" fw={400}>Unknown vendor</Text>}
            </Text>
            {amount && (
              <Text
                fw={700}
                size="md"
                ff="monospace"
                style={{ color: 'var(--accent)', flexShrink: 0 }}
              >
                {amount}
              </Text>
            )}
          </Group>

          {/* Badges */}
          {(tagType || tagYear) && (
            <Group gap={4}>
              {tagType && (
                <Badge size="xs" color={typeColor} variant="light">
                  {tagType}
                </Badge>
              )}
              {tagYear && (
                <Badge size="xs" color="gray" variant="outline">
                  {tagYear}
                </Badge>
              )}
            </Group>
          )}

          {/* Filename */}
          <Text
            size="xs"
            ff="monospace"
            c="dimmed"
            style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {doc.filename}
          </Text>

          {/* Snippet */}
          {doc.snippet && (
            <Text size="xs" c="dimmed" lineClamp={2} style={{ lineHeight: 1.5 }}>
              {highlightSnippet(doc.snippet.replace(/\n/g, ' '), query)}
            </Text>
          )}
        </Stack>
      </Group>

      {/* Actions */}
      <Group gap="xs" mt="sm" justify="flex-end">
        <Button
          size="xs"
          variant="light"
          color="teal"
          leftSection={<IconEye size={13} />}
          onClick={() => onView(doc)}
          style={{ flex: 2 }}
        >
          View
        </Button>
        <ActionIcon
          size="md"
          variant="default"
          title="Download"
          onClick={handleDownload}
        >
          <IconDownload size={14} />
        </ActionIcon>
        <ActionIcon
          size="md"
          variant="default"
          title="Edit tags"
          onClick={() => onView(doc)}
        >
          <IconTag size={14} />
        </ActionIcon>
      </Group>
    </Card>
  )
}
