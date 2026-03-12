import { useState } from 'react'
import {
  Autocomplete,
  Badge,
  Button,
  Group,
  Select,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconTag, IconX } from '@tabler/icons-react'
import { bulkTags } from '../api'
import type { DocumentTags } from '../types'

const DOC_TYPES = [
  { value: '', label: '— keep existing —' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'receipt', label: 'Receipt' },
  { value: 'contract', label: 'Contract' },
  { value: 'quote', label: 'Quote' },
  { value: 'statement', label: 'Statement' },
  { value: 'other', label: 'Other' },
]

const YEAR_OPTIONS = [
  { value: '', label: '— keep existing —' },
  ...Array.from({ length: 31 }, (_, i) => {
    const y = String(2030 - i)
    return { value: y, label: y }
  }),
]

interface Props {
  selectedPaths: Set<string>
  companies: string[]
  onApplied: () => void
  onDeselect: () => void
}

export default function BulkToolbar({ selectedPaths, companies, onApplied, onDeselect }: Props) {
  const [type, setType] = useState('')
  const [company, setCompany] = useState('')
  const [year, setYear] = useState('')
  const [saving, setSaving] = useState(false)

  if (selectedPaths.size === 0) return null

  const handleApply = async () => {
    const tags: DocumentTags = {}
    if (type) tags.type = type
    if (company.trim()) tags.company = company.trim()
    if (year) tags.year = year

    if (!Object.keys(tags).length) {
      notifications.show({ color: 'orange', message: 'Set at least one field to apply' })
      return
    }

    setSaving(true)
    try {
      await bulkTags(Array.from(selectedPaths), tags)
      notifications.show({
        color: 'teal',
        message: `Labels applied to ${selectedPaths.size} document${selectedPaths.size > 1 ? 's' : ''}`,
      })
      setType('')
      setCompany('')
      setYear('')
      onApplied()
    } catch {
      notifications.show({ color: 'red', message: 'Bulk tag failed' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Group
      px="lg"
      py="sm"
      gap="sm"
      wrap="nowrap"
      style={{
        position: 'sticky',
        bottom: 24,
        zIndex: 200,
        background: 'var(--card-bg)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
        marginTop: 8,
        overflowX: 'auto',
      }}
    >
      <Badge
        size="lg"
        color="teal"
        variant="filled"
        leftSection={<IconTag size={11} />}
        style={{ flexShrink: 0 }}
      >
        {selectedPaths.size} selected
      </Badge>

      <Select
        size="xs"
        placeholder="Type"
        data={DOC_TYPES}
        value={type}
        onChange={(v) => setType(v ?? '')}
        style={{ minWidth: 140 }}
        clearable
      />

      <Autocomplete
        size="xs"
        placeholder="Company"
        data={companies}
        value={company}
        onChange={setCompany}
        style={{ minWidth: 160 }}
      />

      <Select
        size="xs"
        placeholder="Year"
        data={YEAR_OPTIONS}
        value={year}
        onChange={(v) => setYear(v ?? '')}
        style={{ minWidth: 100 }}
        clearable
      />

      <Button
        size="xs"
        color="teal"
        loading={saving}
        onClick={handleApply}
        style={{ flexShrink: 0 }}
      >
        Apply to selected
      </Button>

      <Button
        size="xs"
        variant="subtle"
        color="gray"
        leftSection={<IconX size={12} />}
        onClick={onDeselect}
        style={{ flexShrink: 0 }}
      >
        <Text size="xs">Deselect all</Text>
      </Button>
    </Group>
  )
}
