import { Box, Group, Skeleton, Text, UnstyledButton } from '@mantine/core'
import type { Stats } from '../types'

const EXAMPLE_SEARCHES = ['invoice', 'receipt', '2024', '2025', 'unpaid']

interface Props {
  stats: Stats | null
  companies: string[]
  onSearch: (q: string) => void
}

export default function WelcomeState({ stats, companies, onSearch }: Props) {
  const chipStyle: React.CSSProperties = {
    display: 'inline-block',
    padding: '4px 14px',
    borderRadius: 20,
    border: '1px solid var(--border)',
    background: 'var(--card-bg)',
    fontSize: 13,
    color: 'var(--ink)',
    cursor: 'pointer',
    transition: 'border-color 0.15s, background 0.15s',
  }

  return (
    <Box mt="xl">
      {/* Stats row */}
      <Group justify="center" gap="xl" mb="xl">
        {stats ? (
          <>
            <Box ta="center">
              <Text size="xl" fw={700} c="teal" ff="monospace">
                {stats.doc_count}
              </Text>
              <Text size="xs" c="dimmed" tt="uppercase" style={{ letterSpacing: 1 }}>
                Documents indexed
              </Text>
            </Box>
            {stats.last_indexed && (
              <Box ta="center">
                <Text size="xl" fw={700} c="teal" ff="monospace">
                  {stats.last_indexed}
                </Text>
                <Text size="xs" c="dimmed" tt="uppercase" style={{ letterSpacing: 1 }}>
                  Last indexed
                </Text>
              </Box>
            )}
          </>
        ) : (
          <>
            <Skeleton height={40} width={80} />
            <Skeleton height={40} width={120} />
          </>
        )}
      </Group>

      {/* Top companies */}
      {companies.length > 0 && (
        <Box mb="lg">
          <Text size="xs" c="dimmed" tt="uppercase" style={{ letterSpacing: 1 }} mb="xs">
            Top companies
          </Text>
          <Group gap="xs">
            {companies.slice(0, 12).map((c) => (
              <UnstyledButton
                key={c}
                style={chipStyle}
                onClick={() => onSearch(c)}
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)'
                  ;(e.currentTarget as HTMLElement).style.background = '#e6f7f7'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLElement).style.borderColor = 'var(--border)'
                  ;(e.currentTarget as HTMLElement).style.background = 'var(--card-bg)'
                }}
              >
                {c}
              </UnstyledButton>
            ))}
          </Group>
        </Box>
      )}

      {/* Example searches */}
      <Box>
        <Text size="xs" c="dimmed" tt="uppercase" style={{ letterSpacing: 1 }} mb="xs">
          Example searches
        </Text>
        <Group gap="xs">
          {EXAMPLE_SEARCHES.map((term) => (
            <UnstyledButton
              key={term}
              style={{ ...chipStyle, background: '#EDF8F8', borderColor: '#b2dede' }}
              onClick={() => onSearch(term)}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)'
                ;(e.currentTarget as HTMLElement).style.background = '#d4f0f0'
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLElement).style.borderColor = '#b2dede'
                ;(e.currentTarget as HTMLElement).style.background = '#EDF8F8'
              }}
            >
              {term}
            </UnstyledButton>
          ))}
        </Group>
      </Box>
    </Box>
  )
}
