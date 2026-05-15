import { useEffect, useState } from 'react'
import { Box, Loader, Modal, ScrollArea, Text } from '@mantine/core'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchManual } from '../api'

interface Props {
  opened: boolean
  onClose: () => void
}

export default function UserManualModal({ opened, onClose }: Props) {
  const [content, setContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!opened || content) return
    fetchManual().then((r) => {
      if (r.error) setError(r.error)
      else setContent(r.content ?? '')
    })
  }, [opened])

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="User Manual"
      size="xl"
      styles={{
        title: { fontFamily: '"DM Serif Display", serif', fontSize: 22, fontWeight: 400 },
      }}
    >
      <ScrollArea h={560}>
        {!content && !error && (
          <Box style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <Loader color="teal" size="sm" />
          </Box>
        )}
        {error && (
          <Text size="sm" c="red">{error}</Text>
        )}
        {content && (
          <Box className="ask-markdown" pr="md">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </Box>
        )}
      </ScrollArea>
    </Modal>
  )
}
