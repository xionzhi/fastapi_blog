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
      <span class="views-key">Page views</span>
      <span class="visitors-key">Daily visitors</span>
    </figcaption>
    <svg
      viewBox="0 0 720 200"
      role="img"
      aria-label="Daily page views and estimated visitors"
    >
      <title>Daily page views and estimated visitors</title>
      <path
        d="M20 25H700 M20 97H700 M20 170H700"
        fill="none"
        stroke="#e9edef"
      />
      <polyline
        :points="points('views')"
        fill="none"
        stroke="#28664f"
        stroke-width="3"
        stroke-linejoin="round"
      />
      <polyline
        :points="points('visitors')"
        fill="none"
        stroke="#6b8fb4"
        stroke-width="2"
        stroke-dasharray="5 4"
      />
      <text
        x="20"
        y="195"
      >
        {{ series[0]?.day }}
      </text>
      <text
        x="700"
        y="195"
        text-anchor="end"
      >
        {{ series.at(-1)?.day }}
      </text>
      <text
        x="700"
        y="17"
        text-anchor="end"
      >
        {{ maximum }} views
      </text>
    </svg>
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
  margin-bottom: 15px;
  font-size: 12px;
}
figcaption span::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 8px;
  border-radius: 50%;
  background: #28664f;
}
.visitors-key::before {
  background: #6b8fb4;
}
svg {
  display: block;
  width: 100%;
  height: auto;
}
text {
  fill: #65716a;
  font-size: 11px;
  font-family: inherit;
}
@media (max-width: 600px) {
  text {
    font-size: 24px;
  }
}
</style>
