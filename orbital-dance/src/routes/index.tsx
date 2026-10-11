import { createFileRoute } from '@tanstack/react-router';
import { MissionControl } from '@/components/orbital/MissionControl';
export const Route = createFileRoute('/')({
  ssr: false,
  head: () => ({ meta: [
    { title: 'ORBITAL · Conjunction & Space Traffic Risk Engine' },
    { name: 'description', content: 'Mission control for live satellite conjunction simulation, space-weather adjusted collision probability and fuel-efficient orbital avoidance.' },
    { property: 'og:title', content: 'ORBITAL · Conjunction & Space Traffic Risk Engine' },
    { property: 'og:description', content: 'Explore orbital encounters, debris intelligence and precision avoidance in a live 3D simulation.' },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:card', content: 'summary_large_image' },
  ] }),
  component: MissionControl,
});
