const dateFormat = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'long',
  year: 'numeric',
})

export function date(value: string | null): string {
  if (!value) return 'Unpublished'
  const timestamp = new Date(value)
  return Number.isNaN(timestamp.getTime()) ? 'Unknown date' : dateFormat.format(timestamp)
}

export function slugify(value: string): string {
  return value
    .normalize('NFKC')
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}_-]+/gu, '-')
    .replace(/-+/g, '-')
    .replace(/^[-_]+|[-_]+$/g, '')
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
