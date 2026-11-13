<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getTraffic, type TrafficOverview } from '../api/analytics'
import TrafficChart from '../components/analytics/TrafficChart.vue'
import { errorMessage } from '../utils/format'

const days = ref(30)
const data = ref<TrafficOverview>()
const loading = ref(false)
const error = ref('')
let request: AbortController | undefined
const numbers = new Intl.NumberFormat('en')
const cards = computed(() => [
  { label: 'Page views', value: data.value?.total_views ?? 0 },
  { label: 'Avg. daily visitors', value: data.value?.average_daily_visitors ?? 0 },
  { label: 'Views today', value: data.value?.today_views ?? 0 },
  { label: 'Visitors today', value: data.value?.today_visitors ?? 0 },
])
async function load(): Promise<void> {
  request?.abort()
  const current = new AbortController()
  request = current
  loading.value = true
  error.value = ''
  try {
    const result = await getTraffic(days.value, current.signal)
    if (!current.signal.aborted) data.value = result
  } catch (cause) {
    if (!current.signal.aborted) error.value = errorMessage(cause)
  } finally {
    if (!current.signal.aborted) loading.value = false
  }
}
watch(days, load, { immediate: true })
onBeforeUnmount(() => request?.abort())
</script>
<template>
  <div class="admin-page traffic-page">
    <header class="admin-page-heading">
      <div>
        <p class="eyebrow">YOUR READERS</p>
        <h1>Analytics</h1>
        <p class="muted">Anonymous traffic estimates for your public blog.</p>
      </div>
      <label>
        Period
        <select v-model.number="days">
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
          <option :value="90">Last 90 days</option>
        </select>
      </label>
    </header>
    <div
      v-if="error"
      class="form-error"
      role="alert"
    >
      <p>{{ error }}</p>
      <button
        class="button-secondary"
        @click="load"
      >
        Try again
      </button>
    </div>
    <p
      v-if="loading"
      class="muted"
      role="status"
    >
      Loading traffic…
    </p>
    <template v-if="data && !error">
      <p
        v-if="!data.enabled"
        class="traffic-note"
      >
        Traffic collection is disabled.
      </p>
      <p
        v-if="data.daily_limit_reached"
        class="traffic-note"
      >
        Today's collection limit has been reached. Collection resumes on the next UTC day.
      </p>
      <div class="stats-row traffic-cards">
        <div
          v-for="card in cards"
          :key="card.label"
        >
          <span>{{ card.label }}</span>
          <strong>{{ numbers.format(card.value) }}</strong>
        </div>
      </div>
      <section class="content-panel traffic-panel">
        <h2>Traffic over time</h2>
        <p
          v-if="!data.total_views"
          class="muted"
        >
          No traffic recorded for this period yet.
        </p>
        <TrafficChart :series="data.series" />
      </section>
      <section class="content-panel traffic-panel">
        <h2>Popular pages</h2>
        <p
          v-if="!data.popular_pages.length"
          class="muted"
        >
          Published pages appear here after a visit.
        </p>
        <ol
          v-else
          class="popular-pages"
        >
          <li
            v-for="page in data.popular_pages"
            :key="page.path"
          >
            <a
              :href="page.path"
              target="_blank"
              rel="noopener noreferrer"
            >
              <strong>{{ page.title }}</strong>
              <small>{{ page.path }}</small>
            </a>
            <span>{{ numbers.format(page.views) }} views</span>
          </li>
        </ol>
      </section>
      <p class="traffic-privacy">
        Dates use UTC. Visitors are estimated per browser and day; the period average includes days
        with no visits. Common bots, background prefetches and signed-in administrators are
        excluded. Privacy signals (DNT/GPC) are respected. Daily anonymous IDs are cleaned hourly
        after the day ends; only aggregates remain for {{ data.retention_days }} days. No raw IP
        addresses, user agents, search terms or full referrers are stored in analytics.
      </p>
    </template>
  </div>
</template>
<style scoped>
.admin-page-heading label {
  min-width: 160px;
}
.traffic-cards {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.traffic-cards strong {
  font-size: clamp(20px, 2.2vw, 30px);
}
.traffic-panel {
  padding: 26px;
  margin-bottom: 24px;
}
.traffic-panel h2 {
  margin: 0 0 22px;
  font-size: 17px;
}
.traffic-note {
  padding: 15px;
  border: 1px solid #e5dec7;
  border-radius: 6px;
  background: #fbf8ed;
  font-size: 13px;
}
.popular-pages {
  margin: 0;
  padding: 0;
  list-style: none;
}
.popular-pages li {
  display: flex;
  gap: 20px;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  margin: 0;
  border-top: 1px solid #edf0e9;
}
.popular-pages a {
  min-width: 0;
  overflow-wrap: anywhere;
}
.popular-pages strong {
  font-size: 14px;
  font-weight: 500;
}
.popular-pages small {
  display: block;
  margin-top: 5px;
}
.popular-pages li > span {
  flex-shrink: 0;
  font-size: 12px;
  color: #65716a;
}
.traffic-privacy {
  font-size: 12px;
  line-height: 1.9;
  color: #65716a;
}
@media (max-width: 1000px) {
  .traffic-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 600px) {
  .admin-page-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .traffic-panel {
    padding: 20px;
  }
  .popular-pages li {
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
