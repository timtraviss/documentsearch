import { useEffect, useRef, useState } from 'react'
import {
  Box,
  Button,
  Checkbox,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconRefresh } from '@tabler/icons-react'
import { startReindex, getReindexStatus } from '../api'

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
  const logRef = useRef<HTMLDivElement>(null)
  const pollingRef = useRef(false)

  // Auto-scroll log to bottom
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  // On open, check if a reindex is already running (e.g. page refresh mid-index)
  useEffect(() => {
    if (!opened) return
    setLogs([])
    setDone(false)
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

  const handleStart = async () => {
    setLogs([])
    setDone(false)
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
      </Stack>
    </Modal>
  )
}
