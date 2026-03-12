import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Divider,
  Loader,
  Modal,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { getTagValues, renameTag } from '../api'
import type { TagValues } from '../types'

interface Props {
  opened: boolean
  onClose: () => void
  onRenamed: () => void
}

const FIELDS: { key: keyof TagValues; label: string }[] = [
  { key: 'company', label: 'Company' },
  { key: 'type', label: 'Document Type' },
  { key: 'year', label: 'Year' },
]

export default function TagMgmt({ opened, onClose, onRenamed }: Props) {
  const [tagValues, setTagValues] = useState<TagValues | null>(null)
  const [loading, setLoading] = useState(false)
  const [renaming, setRenaming] = useState<Record<string, boolean>>({})
  const [inputs, setInputs] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!opened) return
    setLoading(true)
    getTagValues()
      .then(setTagValues)
      .catch(() => notifications.show({ color: 'red', message: 'Could not load tag values' }))
      .finally(() => setLoading(false))
  }, [opened])

  const rowKey = (field: string, val: string) => `${field}::${val}`

  const handleRename = async (field: string, oldValue: string) => {
    const key = rowKey(field, oldValue)
    const newValue = (inputs[key] ?? '').trim()
    if (!newValue || newValue === oldValue) return
    setRenaming((r) => ({ ...r, [key]: true }))
    try {
      await renameTag(field, oldValue, newValue)
      notifications.show({ color: 'teal', message: `Renamed "${oldValue}" → "${newValue}"` })
      onRenamed()
      // Reload tag values
      const fresh = await getTagValues()
      setTagValues(fresh)
      setInputs((prev) => ({ ...prev, [key]: '' }))
    } catch {
      notifications.show({ color: 'red', message: 'Rename failed' })
    } finally {
      setRenaming((r) => ({ ...r, [key]: false }))
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Manage Tags"
      size="lg"
      styles={{
        title: { fontFamily: '"DM Serif Display", serif', fontSize: 22, fontWeight: 400 },
        body: { padding: 0 },
      }}
    >
      <ScrollArea h="70vh" px="lg" py="md">
        {loading && (
          <Box ta="center" py="xl">
            <Loader size="sm" />
          </Box>
        )}

        {!loading && tagValues && (
          <Stack gap="xl">
            <Text size="sm" c="dimmed">
              Rename a value to update it across all tagged documents.
            </Text>

            {FIELDS.map(({ key, label }) => {
              const entries = Object.entries(tagValues[key] ?? {}).sort((a, b) => b[1] - a[1])
              if (!entries.length) return null
              return (
                <Box key={key}>
                  <Text
                    size="xs"
                    tt="uppercase"
                    c="dimmed"
                    style={{ letterSpacing: 1 }}
                    mb="xs"
                  >
                    {label}
                  </Text>
                  <Table
                    styles={{
                      table: { fontSize: 13 },
                      th: { color: 'var(--ink-muted)', fontWeight: 500, fontSize: 12 },
                    }}
                  >
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Current value</Table.Th>
                        <Table.Th w={55} ta="center">Docs</Table.Th>
                        <Table.Th>Rename to</Table.Th>
                        <Table.Th w={70} />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {entries.map(([val, count]) => {
                        const k = rowKey(key, val)
                        return (
                          <Table.Tr key={val}>
                            <Table.Td fw={500}>{val}</Table.Td>
                            <Table.Td ta="center" c="dimmed">{count}</Table.Td>
                            <Table.Td>
                              <TextInput
                                size="xs"
                                placeholder={val}
                                value={inputs[k] ?? ''}
                                onChange={(e) =>
                                  setInputs((prev) => ({ ...prev, [k]: e.currentTarget.value }))
                                }
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleRename(key, val)
                                }}
                              />
                            </Table.Td>
                            <Table.Td>
                              <Button
                                size="xs"
                                variant="light"
                                color="teal"
                                loading={renaming[k]}
                                disabled={!inputs[k]?.trim() || inputs[k] === val}
                                onClick={() => handleRename(key, val)}
                              >
                                Save
                              </Button>
                            </Table.Td>
                          </Table.Tr>
                        )
                      })}
                    </Table.Tbody>
                  </Table>
                  <Divider mt="md" color="var(--border)" />
                </Box>
              )
            })}

            {FIELDS.every(({ key }) => !Object.keys(tagValues[key] ?? {}).length) && (
              <Text c="dimmed" ta="center" py="xl">No tags saved yet.</Text>
            )}
          </Stack>
        )}
      </ScrollArea>
    </Modal>
  )
}
