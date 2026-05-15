import { useEffect, useRef, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Group,
  Text,
  TextInput,
} from '@mantine/core'
import { IconRefresh, IconSend } from '@tabler/icons-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ask } from '../api'
import type { AskMessage, AskSource, SearchResult } from '../types'

interface Props {
  messages: AskMessage[]
  onMessagesChange: (messages: AskMessage[]) => void
  onOpenPdf: (doc: SearchResult) => void
}

function sourceToResult(s: AskSource): SearchResult {
  return {
    filename: s.filename,
    path: s.path,
    relative_path: s.path,
    snippet: s.snippet,
    tags: {},
  }
}

export default function AskPanel({ messages, onMessagesChange, onOpenPdf }: Props) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return

    const withUser: AskMessage[] = [...messages, { role: 'user', content: q }]
    onMessagesChange(withUser)
    setInput('')
    setLoading(true)
    setError(null)

    const response = await ask(q, messages)
    setLoading(false)

    if (response.error) {
      setError(response.error)
      return
    }

    onMessagesChange([
      ...withUser,
      {
        role: 'assistant',
        content: response.answer ?? '',
        sources: response.sources ?? [],
      },
    ])
  }

  const handleNewChat = () => {
    onMessagesChange([])
    setError(null)
  }

  return (
    <Box style={{ display: 'flex', flexDirection: 'column', minHeight: 400 }}>
      {/* Chat history */}
      <Box style={{ flex: 1, paddingBottom: '1rem' }}>
        {messages.length === 0 && !loading && (
          <Box style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <Text
              size="xl"
              style={{ fontFamily: '"DM Serif Display", serif', color: 'var(--ink)' }}
            >
              Ask a question about your documents
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
              Try: "What are the key terms in my contracts?" or "Which invoices are over $500?"
            </Text>
          </Box>
        )}

        {messages.map((msg, idx) => (
          <Box key={idx} mb="lg">
            {msg.role === 'user' ? (
              <Box style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Box
                  style={{
                    background: 'var(--accent)',
                    color: '#fff',
                    borderRadius: '12px 12px 2px 12px',
                    padding: '0.6rem 1rem',
                    maxWidth: '72%',
                  }}
                >
                  <Text size="sm">{msg.content}</Text>
                </Box>
              </Box>
            ) : (
              <Box>
                <Text
                  size="xs"
                  c="dimmed"
                  mb={4}
                  style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}
                >
                  Claude
                </Text>
                <Box
                  style={{
                    background: 'var(--card-bg)',
                    border: '1px solid var(--border)',
                    borderRadius: '2px 12px 12px 12px',
                    padding: '0.75rem 1rem',
                  }}
                  className="ask-markdown"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </Box>

                {msg.sources && msg.sources.length > 0 && (
                  <Group gap="xs" mt="xs">
                    {msg.sources.map((s, si) => (
                      <Badge
                        key={si}
                        variant="light"
                        color="teal"
                        style={{ cursor: 'pointer' }}
                        onClick={() => onOpenPdf(sourceToResult(s))}
                      >
                        {s.filename}
                      </Badge>
                    ))}
                  </Group>
                )}
              </Box>
            )}
          </Box>
        ))}

        {loading && (
          <Box>
            <Text
              size="xs"
              c="dimmed"
              mb={4}
              style={{ fontFamily: 'var(--mantine-font-family-monospace)' }}
            >
              Claude
            </Text>
            <Box
              style={{
                background: 'var(--card-bg)',
                border: '1px solid var(--border)',
                borderRadius: '2px 12px 12px 12px',
                padding: '0.75rem 1rem',
                display: 'inline-block',
              }}
            >
              <Text size="sm" c="dimmed">● ● ●</Text>
            </Box>
          </Box>
        )}

        {error && (
          <Box
            mt="sm"
            style={{
              background: '#fff5f5',
              border: '1px solid #ffc9c9',
              borderRadius: 6,
              padding: '0.75rem 1rem',
            }}
          >
            <Text size="sm" c="red">{error}</Text>
          </Box>
        )}

        <div ref={bottomRef} />
      </Box>

      {/* Input bar */}
      <Box
        component="form"
        onSubmit={handleSubmit}
        style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}
      >
        <Group gap="xs" wrap="nowrap">
          <TextInput
            flex={1}
            placeholder={messages.length > 0 ? 'Ask a follow-up…' : 'Ask a question about your documents…'}
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            size="md"
            disabled={loading}
            styles={{
              input: {
                fontFamily: 'var(--mantine-font-family)',
                background: 'var(--card-bg)',
                borderColor: 'var(--border)',
              },
            }}
          />
          {messages.length > 0 && (
            <Button
              size="md"
              variant="default"
              onClick={handleNewChat}
              title="New chat"
              disabled={loading}
            >
              <IconRefresh size={15} />
            </Button>
          )}
          <Button
            type="submit"
            size="md"
            color="teal"
            loading={loading}
            disabled={!input.trim() || loading}
          >
            <IconSend size={15} />
          </Button>
        </Group>
      </Box>
    </Box>
  )
}
