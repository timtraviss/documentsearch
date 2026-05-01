import { useEffect, useRef, useState } from 'react'
import {
  Badge,
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
import { IconFolderSymlink } from '@tabler/icons-react'
import { startFilePdfs, getFilePdfsStatus } from '../api'

interface Props {
  opened: boolean
  onClose: () => void
  onComplete: () => void
}

export default function FilePdfsModal({ opened, onClose, onComplete }: Props) {
  const [dryRun, setDryRun] = useState(false)
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const [result, setResult] = useState<{ filed: number; skipped: number } | null>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const pollingRef = useRef(false)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  useEffect(() => {
    if (!opened) return
    setLogs([])
    setDone(false)
    setResult(null)
    getFilePdfsStatus().then((s) => {
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
        const s = await getFilePdfsStatus()
        if (s.logs && s.logs.length > lastLen) {
          setLogs(s.logs)
          lastLen = s.logs.length
        }
        if (!s.running) {
          pollingRef.current = false
          setRunning(false)
          setDone(true)
          setResult({ filed: s.filed ?? 0, skipped: s.skipped ?? 0 })
          if (!s.error) onComplete()
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
    setResult(null)
    setRunning(true)
    try {
      await startFilePdfs(dryRun)
      poll()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      notifications.show({ color: 'red', message: `Failed to start: ${msg}` })
      setRunning(false)
    }
  }

  const handleClose = () => {
    if (running) {
      notifications.show({ color: 'teal', message: 'Filing continues in the background' })
    }
    onClose()
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="File Loose PDFs"
      size="lg"
      styles={{
        title: { fontFamily: '"DM Serif Display", serif', fontSize: 22, fontWeight: 400 },
      }}
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Scan the root of your PDF folder for loose files and move them into the correct
          company subfolders. Files that aren't invoices or can't be identified are left in place.
        </Text>

        <Checkbox
          label="Dry run — show what would happen without moving anything"
          checked={dryRun}
          onChange={(e) => setDryRun(e.currentTarget.checked)}
          disabled={running}
        />

        <Group>
          <Button
            color="teal"
            leftSection={<IconFolderSymlink size={15} />}
            loading={running}
            disabled={running}
            onClick={handleStart}
          >
            {running ? 'Filing…' : 'File PDFs'}
          </Button>
          <Button variant="default" onClick={handleClose}>
            {done ? 'Close' : running ? 'Run in background' : 'Cancel'}
          </Button>
        </Group>

        {done && result && (
          <Group gap="xs">
            <Text size="xs" c="dimmed" style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}>
              Result:
            </Text>
            <Badge color="teal" variant="light" size="sm">{result.filed} filed</Badge>
            <Badge color="gray" variant="light" size="sm">{result.skipped} left in place</Badge>
          </Group>
        )}

        {logs.length > 0 && (
          <ScrollArea
            h={260}
            viewportRef={logRef}
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
              {logs.join('\n')}
            </Box>
          </ScrollArea>
        )}
      </Stack>
    </Modal>
  )
}
