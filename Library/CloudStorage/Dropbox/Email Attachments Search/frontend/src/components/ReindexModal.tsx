import { useEffect, useRef, useState } from 'react'
import {
  Box,
  Button,
  Checkbox,
  Divider,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Text,
  Badge,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconRefresh } from '@tabler/icons-react'
import { startReindex, getReindexStatus, startRebuildEmbeddings, getRebuildEmbeddingsStatus } from '../api'

interface Props {
  opened: boolean
  onClose: () => void
  onComplete: () => void
}

export default function ReindexModal({ opened, onClose, onComplete }: Props) {
  const [incremental, setIncremental] = useState(true)
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [obsidian, setObsidian] = useState<{ wrote: number; skipped: number } | null>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const pollingRef = useRef(false)

  const [rebuildRunning, setRebuildRunning] = useState(false)
  const [rebuildLogs, setRebuildLogs] = useState<string[]>([])
  const [rebuildDone, setRebuildDone] = useState(false)
  const rebuildPollingRef = useRef(false)
  const rebuildLogRef = useRef<HTMLDivElement>(null)

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])
  useEffect(() => {
    if (rebuildLogRef.current) rebuildLogRef.current.scrollTop = rebuildLogRef.current.scrollHeight
  }, [rebuildLogs])

  // On open, check if a reindex is already running (e.g. page refresh mid-index)
  useEffect(() => {
    if (!opened) return
    setLogs([])
    setDone(false)
    setObsidian(null)
    getReindexStatus().then((s) => {
      if (s.running) {
        setRunning(true)
        setLogs(s.logs ?? [])
        poll()
      }
    }).catch(() => {})
  }, [opened])

  async function poll() {
    if (pollingRef.current) return
    pollingRef.current = true
    let lastLen = 0
    while (true) {
      await new Promise((r) => setTimeout(r, 1000))
      try {
        const s = await getReindexStatus()
        if (s.logs && s.logs.length > lastLen) {
          setLogs(s.logs)
          lastLen = s.logs.length
        }
        if (!s.running) {
          pollingRef.current = false
          setRunning(false)
          setDone(true)
          if (s.obsidian) setObsidian(s.obsidian)
          if (s.error) {
            setLogs((prev) => [...prev, `Error: ${s.error}`])
          } else {
            const indexed = (s.count ?? 0) - (s.skipped ?? 0)
            setLogs((prev) => [
              ...prev,
              `Done. ${indexed} indexed, ${s.skipped ?? 0} unchanged, ${s.count ?? 0} total.`,
            ])
          }
          onComplete()
          break
        }
      } catch {
        pollingRef.current = false
        setRunning(false)
        break
      }
    }
  }

  async function pollRebuild() {
    if (rebuildPollingRef.current) return
    rebuildPollingRef.current = true
    let lastLen = 0
    while (true) {
      await new Promise((r) => setTimeout(r, 1000))
      try {
        const s = await getRebuildEmbeddingsStatus()
        if (s.logs && s.logs.length > lastLen) {
          setRebuildLogs(s.logs)
          lastLen = s.logs.length
        }
        if (!s.running) {
          rebuildPollingRef.current = false
          setRebuildRunning(false)
          setRebuildDone(true)
          if (s.error) {
            setRebuildLogs((prev) => [...prev, `Error: ${s.error}`])
          }
          break
        }
      } catch {
        rebuildPollingRef.current = false
        setRebuildRunning(false)
        break
      }
    }
  }

  const handleRebuildEmbeddings = async () => {
    setRebuildLogs([])
    setRebuildDone(false)
    setRebuildRunning(true)
    try {
      await startRebuildEmbeddings()
      pollRebuild()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      notifications.show({ color: 'red', message: `Failed to rebuild embeddings: ${msg}` })
      setRebuildRunning(false)
    }
  }

  const handleStart = async () => {
    setLogs([])
    setDone(false)
    setObsidian(null)
    setRunning(true)
    try {
      await startReindex(incremental)
      poll()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      notifications.show({ color: 'red', message: `Failed to start reindex: ${msg}` })
      setRunning(false)
    }
  }

  const handleClose = () => {
    if (running) {
      // allow background indexing — just dismiss the modal
      notifications.show({
        color: 'teal',
        message: 'Indexing continues in the background',
      })
    }
    onClose()
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Re-index PDFs"
      size="lg"
      styles={{
        title: { fontFamily: '"DM Serif Display", serif', fontSize: 22, fontWeight: 400 },
      }}
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Scan your PDF folder and update the search index. Use{' '}
          <strong>Incremental</strong> to only process new or changed files — much faster
          when most files haven't changed.
        </Text>

        <Checkbox
          label="Incremental — skip unchanged files"
          checked={incremental}
          onChange={(e) => setIncremental(e.currentTarget.checked)}
          disabled={running}
        />

        <Group>
          <Button
            color="teal"
            leftSection={<IconRefresh size={15} />}
            loading={running}
            disabled={running}
            onClick={handleStart}
          >
            {running ? 'Indexing…' : 'Start re-index'}
          </Button>
          <Button variant="default" onClick={handleClose}>
            {done ? 'Close' : running ? 'Run in background' : 'Cancel'}
          </Button>
        </Group>

        {done && obsidian && (
          <Group gap="xs">
            <Text size="xs" c="dimmed" style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}>
              Obsidian:
            </Text>
            <Badge color="teal" variant="light" size="sm">{obsidian.wrote} written</Badge>
            <Badge color="gray" variant="light" size="sm">{obsidian.skipped} skipped</Badge>
          </Group>
        )}

        {logs.length > 0 && (
          <ScrollArea
            h={220}
            viewportRef={logRef}
            style={{
              background: '#0f1724',
              borderRadius: 6,
              padding: '0.75rem',
            }}
          >
            <Box
              component="pre"
              style={{
                fontFamily: 'var(--mantine-font-family-monospace)',
                fontSize: 12,
                color: '#e6eef8',
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {logs.join('\n')}
            </Box>
          </ScrollArea>
        )}

        <Divider my="xs" label="Semantic Search" labelPosition="left" />

        <Text size="sm" c="dimmed">
          Rebuild the AI embeddings index used by{' '}
          <strong>Ask AI</strong> mode. Run this after a full re-index when new
          documents have been added.
        </Text>

        <Group>
          <Button
            variant="light"
            color="teal"
            loading={rebuildRunning}
            disabled={rebuildRunning}
            onClick={handleRebuildEmbeddings}
          >
            {rebuildRunning ? 'Building embeddings…' : 'Rebuild embeddings'}
          </Button>
          {rebuildDone && (
            <Text size="sm" c="teal">✓ Done</Text>
          )}
        </Group>

        {rebuildLogs.length > 0 && (
          <ScrollArea
            h={160}
            viewportRef={rebuildLogRef}
            style={{ background: '#0f1724', borderRadius: 6, padding: '0.75rem' }}
          >
            <Box
              component="pre"
              style={{
                fontFamily: 'var(--mantine-font-family-monospace)',
                fontSize: 12,
                color: '#e6eef8',
                margin: 0,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {rebuildLogs.join('\n')}
            </Box>
          </ScrollArea>
        )}
      </Stack>
    </Modal>
  )
}
