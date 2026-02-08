import type { SidebarsConfig } from '@docusaurus/plugin-content-docs'

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/overview',
        'getting-started/installation',
        'getting-started/quickstart',
        'getting-started/docker-setup'
      ]
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/system-context',
        'architecture/containers',
        'architecture/components',
        'architecture/data-flow',
        'architecture/deployment'
      ]
    },
    {
      type: 'category',
      label: 'Domain',
      items: ['domain/ics-fundamentals', 'domain/threat-landscape', 'domain/anomaly-types']
    },
    {
      type: 'category',
      label: 'Core Technology',
      items: [
        'core-technology/go',
        'core-technology/rust',
        'core-technology/python',
        'core-technology/kafka',
        'core-technology/redis',
        'core-technology/prometheus',
        'core-technology/react'
      ]
    },
    {
      type: 'category',
      label: 'Code Structure',
      items: [
        'code-structure/capture',
        'code-structure/simulator',
        'code-structure/parser',
        'code-structure/feature-engine',
        'code-structure/anomaly-detection',
        'code-structure/alerting',
        'code-structure/dashboard',
        'code-structure/infrastructure'
      ]
    },
    {
      type: 'category',
      label: 'ML Pipeline',
      items: [
        'ml-pipeline/data-ingestion',
        'ml-pipeline/feature-engineering',
        'ml-pipeline/models',
        'ml-pipeline/training',
        'ml-pipeline/inference'
      ]
    },
    {
      type: 'category',
      label: 'Simulation',
      items: ['simulation/traffic-generator', 'simulation/attack-scenarios', 'simulation/datasets']
    },
    {
      type: 'category',
      label: 'API Reference',
      items: ['api/rest-api', 'api/websocket', 'api/metrics']
    },
    {
      type: 'category',
      label: 'Operations',
      items: ['operations/monitoring', 'operations/alerting', 'operations/troubleshooting']
    }
  ]
}

export default sidebars
