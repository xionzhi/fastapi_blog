/** HTTP transport only. Vue state is supplied through explicit session hooks. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface SessionHooks {
  csrfToken: () => string
  onUnauthorized: () => void
}

let hooks: SessionHooks = { csrfToken: () => '', onUnauthorized: () => {} }

export function configureHttpClient(sessionHooks: SessionHooks): void {
  hooks = sessionHooks
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object'
}

function resolveErrorMessage(body: unknown, status: number): string {
  if (!record(body)) return `Request failed (${status})`
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((item: unknown) => {
        if (!record(item) || typeof item.msg !== 'string') return 'Invalid request'
        const path = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : ''
        return path ? `${path}: ${item.msg}` : item.msg
      })
      .join('; ')
  }
  return `Request failed (${status})`
}

function pause(signal?: AbortSignal | null): Promise<void> {
  return new Promise((resolve, reject) => {
    const aborted = (): void => {
      clearTimeout(timer)
      reject(signal?.reason ?? new DOMException('Request canceled', 'AbortError'))
    }
    const timer = setTimeout(
      () => {
        signal?.removeEventListener('abort', aborted)
        resolve()
      },
      350 + Math.random() * 350,
    )
    if (signal?.aborted) aborted()
    else signal?.addEventListener('abort', aborted, { once: true })
  })
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  const csrfToken = hooks.csrfToken()
  if (csrfToken && !['GET', 'HEAD'].includes(options.method ?? 'GET')) {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const retryable = ['GET', 'HEAD'].includes(options.method ?? 'GET')
  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController()
    const abort = (): void => controller.abort(options.signal?.reason)
    if (options.signal?.aborted) throw options.signal.reason
    options.signal?.addEventListener('abort', abort, { once: true })
    let timer = setTimeout(() => controller.abort(), 20000)
    try {
      const original = await fetch(`/api${path}`, {
        ...options,
        headers,
        credentials: 'same-origin',
        signal: controller.signal,
      })
      // Some browser transports expose an empty stream even for bodyless statuses.
      const bodyless = options.method === 'HEAD' || [204, 205, 304].includes(original.status)
      if (bodyless) await original.body?.cancel().catch(() => {})
      const stream = bodyless
        ? null
        : original.body?.pipeThrough(
            new TransformStream<Uint8Array, Uint8Array>({
              transform(chunk, output) {
                clearTimeout(timer)
                timer = setTimeout(() => controller.abort(), 20000)
                output.enqueue(chunk)
              },
            }),
          )
      const response = new Response(stream ?? null, {
        status: original.status,
        statusText: original.statusText,
        headers: original.headers,
      })
      if (retryable && attempt === 0 && [408, 502, 503, 504].includes(response.status)) {
        await response.body?.cancel()
      } else {
        if (!response.ok) {
          const body: unknown = await response.json().catch(() => null)
          if (response.status === 401 && !path.endsWith('/login')) hooks.onUnauthorized()
          const code =
            record(body) && typeof body.error_code === 'string' ? body.error_code : undefined
          throw new ApiError(resolveErrorMessage(body, response.status), response.status, code)
        }
        return bodyless ? (undefined as T) : ((await response.json()) as T)
      }
    } catch (cause) {
      if (options.signal?.aborted) throw options.signal.reason
      if (cause instanceof ApiError) throw cause
      if (!retryable || attempt > 0) {
        throw new ApiError(
          controller.signal.aborted
            ? 'The request timed out. Please try again.'
            : 'The connection was interrupted. Please check your network and try again.',
          0,
          controller.signal.aborted ? 'network.timeout' : 'network.interrupted',
        )
      }
    } finally {
      clearTimeout(timer)
      options.signal?.removeEventListener('abort', abort)
    }
    await pause(options.signal)
  }
  throw new ApiError('The request could not be completed.', 0, 'network.interrupted')
}

export function queryString(values: object): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  }
  return query.toString()
}
