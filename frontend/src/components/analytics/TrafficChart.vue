<script setup lang="ts">
import { computed } from 'vue'
import type { DailyTraffic } from '../../api/analytics'

const props = defineProps<{ series: DailyTraffic[] }>()
const maximum = computed(() => Math.max(1, ...props.series.map((day) => day.views)))
function points(field: 'views' | 'visitors'): string {
  return props.series
    .map(
      (day, index) =>
        `${20 + (index / Math.max(1, props.series.length - 1)) * 680},${170 - (day[field] / maximum.value) * 145}`,
    )
    .join(' ')
}
</script>
<template>
  <figure class="traffic-chart">
    <figcaption>
      <span class="chart-key">Page views</span>
      <span class="chart-key visitors-key">Daily visitors</span>
      <span class="chart-scale">Scale: {{ maximum }} views</span>
    </figcaption>
    <svg
      viewBox="0 0 720 178"
      role="img"
      aria-label="Daily page views and estimated visitors"
    >
      <title>Daily page views and estimated visitors</title>
      <path
        d="M20 25H700 M20 97H700 M20 170H700"
        fill="none"
        stroke="var(--line)"
        vector-effect="non-scaling-stroke"
      />
      <polyline
        :points="points('views')"
        fill="none"
        stroke="var(--green)"
        stroke-width="2"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
      <polyline
        :points="points('visitors')"
        fill="none"
        stroke="var(--admin-chart-secondary)"
        stroke-width="1.5"
        stroke-dasharray="5 4"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    <div
      v-if="series.length"
      class="chart-dates"
    >
      <span>{{ series[0]?.day }}</span>
      <span>{{ series.at(-1)?.day }}</span>
    </div>
  </figure>
</template>
<style scoped>
.traffic-chart {
  margin: 0;
}
figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 13px;
}
.chart-key::before {
  content: '';
  display: inline-block;
  width: 18px;
  margin-right: 8px;
  vertical-align: middle;
  border-top: 2px solid var(--green);
}
.visitors-key::before {
  border-top: 2px dashed var(--admin-chart-secondary);
}
.chart-scale {
  margin-left: auto;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
svg {
  display: block;
  width: 100%;
  height: auto;
}
.chart-dates {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding-inline: 2.78%;
  color: var(--muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
</style>
