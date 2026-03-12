import { createTheme, rem } from '@mantine/core'

export const theme = createTheme({
  // Editorial ink-on-cream palette
  primaryColor: 'teal',
  colors: {
    teal: [
      '#e6f7f7', // 0
      '#cceeee', // 1
      '#99dddd', // 2
      '#66cccc', // 3
      '#33bbbb', // 4
      '#0D7377', // 5 — primary accent
      '#0b5e61', // 6
      '#08494c', // 7
      '#063437', // 8
      '#031f22', // 9
    ],
    sienna: [
      '#fdf0ec',
      '#fae1d9',
      '#f5c3b3',
      '#f0a58d',
      '#eb8767',
      '#C0392B', // 5 — destructive / warning accent
      '#9a2e22',
      '#73221a',
      '#4d1711',
      '#260b09',
    ],
  },

  fontFamily: '"DM Serif Display", Georgia, serif',
  fontFamilyMonospace: '"DM Mono", "Fira Code", monospace',

  headings: {
    fontFamily: '"DM Serif Display", Georgia, serif',
    sizes: {
      h1: { fontSize: rem(36), fontWeight: '400' },
      h2: { fontSize: rem(24), fontWeight: '400' },
      h3: { fontSize: rem(18), fontWeight: '400' },
    },
  },

  defaultRadius: 'sm',

  other: {
    pageBg: '#F5F0E8',
    cardBg: '#FEFCF8',
    ink: '#1A1A2E',
    inkMuted: '#4A4A6A',
    border: '#DDD8CC',
    accent: '#0D7377',
    accentWarm: '#C0392B',
    fontMono: '"DM Mono", "Fira Code", monospace',
  },
})
