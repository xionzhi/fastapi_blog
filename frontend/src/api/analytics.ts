import { api } from './request'

export interface DailyTraffic {
  day: string
  views: number
  visitors: number
}

export interface TrafficOverview {
  enabled: boolean
  days: number
  timezone: string
  total_views: number
  average_daily_visitors: number
  today_views: number
  today_visitors: number
  daily_limit_reached: boolean
  retention_days: number
  series: DailyTraffic[]
  popular_pages: { path: string; title: string; views: number }[]
}

export const getTraffic = (days: number, signal?: AbortSignal): Promise<TrafficOverview> =>
  api(`/admin/analytics?days=${days}`, { signal })

export const recordPageView = (path: string, visitorId: string): Promise<void> =>
  api('/analytics/events', {
    method: 'POST',
    body: JSON.stringify({ path, visitor_id: visitorId, event_id: crypto.randomUUID() }),
    keepalive: true,
  })
