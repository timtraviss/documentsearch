import { useEffect, useState } from 'react'
import {
  Box,
  Drawer,
  Group,
  Loader,
  Progress,
  RingProgress,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { getStatsBreakdown } from '../api'

interface Breakdown {
  by_company: Record<string, number>
  by_type: Record<string, number>
  by_year: Record<string, number>
  tagged_docs: number
  total_docs: number
}

interface Props {
  opened: boolean
  onClose: () => void
}

function BarSection({ title, counts }: { title: string; counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (!entries.length) return null
  const max = Math.max(...entries.map(([, v]) => v))
  return (
    <Box>
      <Text size="xs" tt="uppercase" c="dimmed" style={{ letterSpacing: 1 }} mb="sm">
        {title}
      </Text>
      <Stack gap={6}>
        {entries.map(([label, count]) => (
          <Group key={label} gap="xs" wrap="nowrap">
            <Text
              size="xs"
              style={{
                width: 140,
                minWidth: 140,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: 'var(--ink-muted)',
              }}
              title={label}
            >
              {label}
            </Text>
            <Progress
              flex={1}
              value={max ? (count / max) * 100 : 0}
              color="teal"
              size="sm"
              radius="xl"
            />
            <Text size="xs" c="dimmed" w={28} ta="right">
              {count}
            </Text>
          </Group>
        ))}
      </Stack>
    </Box>
  )
}

export default function StatsPanel({ opened, onClose }: Props) {
  const [data, setData] = useState<Breakdown | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!opened) return
    setLoading(true)
    getStatsBreakdown()
      .then((d) => setData(d as unknown as Breakdown))
      .catch(() => notifications.show({ color: 'red', message: 'Could not load stats' }))
      .finally(() => setLoading(false))
  }, [opened])

  const total = data?.total_docs ?? 0
  const tagged = data?.tagged_docs ?? 0
  const untagged = total - tagged
  const pct = total ? Math.round((tagged / total) * 100) : 0

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title="Stats Dashboard"
      position="right"
      size="md"
      styles={{
        title: { fontFamily: '"DM Serif Display", serif', fontSize: 22, fontWeight: 400 },
      }}
    >
      {loading && (
        <Box ta="center" pt="xl">
          <Loader size="sm" />
        </Box>
      )}

      {!loading && data && (
        <Stack gap="xl">
          {/* Summary ring + stat tiles */}
          <Group justify="center" align="center" gap="xl">
            <RingProgress
              size={120}
              thickness={12}
              roundCaps
              sections={[{ value: pct, color: 'teal' }]}
              label={
                <Text ta="center" size="xl" fw={700} c="teal">
                  {pct}%
                </Text>
              }
            />
            <SimpleGrid cols={2} spacing="sm">
              {[
                { label: 'Total', value: total, color: 'var(--ink)' },
                { label: 'Tagged', value: tagged, color: 'var(--accent)' },
                { label: 'Untagged', value: untagged, color: '#10b981' },
              ].map(({ label, value, color }) => (
                <Box
                  key={label}
                  p="sm"
                  style={{
                    background: 'var(--card-bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    textAlign: 'center',
                  }}
                >
                  <Text size="xl" fw={700} style={{ color }}>
                    {value}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {label}
                  </Text>
                </Box>
              ))}
            </SimpleGrid>
          </Group>

          <BarSection title="By document type" counts={data.by_type} />
          <BarSection title="By company" counts={data.by_company} />
          <BarSection title="By year" counts={data.by_year} />
        </Stack>
      )}
    </Drawer>
  )
}
