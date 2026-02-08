# Dashboard

The dashboard is a React application providing real-time monitoring of alerts, incidents, and system status.

## Overview

| Property  | Value                   |
| --------- | ----------------------- |
| Language  | TypeScript              |
| Framework | React 19                |
| Location  | `packages/dashboard/`   |
| Port      | 3090                    |
| API Proxy | Alerting service (8084) |

## What it does

1. **Displays real-time alerts** from the alerting service
2. **Shows incident summaries** with status and priority
3. **Provides network overview** of monitored connections
4. **Enables alert/incident management** (acknowledge, resolve)
5. **Shows system status** and configuration

## Package structure

```
packages/dashboard/
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Root component, routing
│   ├── index.css                   # Tailwind imports, theme
│   ├── components/
│   │   ├── Layout.tsx              # Sidebar navigation
│   │   └── ui/                     # Reusable components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── badge.tsx
│   │       └── spinner.tsx
│   ├── routes/
│   │   ├── Dashboard/              # Overview page
│   │   ├── Alerts/                 # Alert list and management
│   │   ├── Incidents/              # Incident list and details
│   │   ├── Network/                # Network topology view
│   │   └── Settings/               # System configuration
│   ├── hooks/                      # Custom React hooks
│   └── lib/
│       ├── api.ts                  # API client
│       ├── types.ts                # TypeScript interfaces
│       └── utils.ts                # Utility functions
├── public/                         # Static assets
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── Dockerfile
```

## Routes

| Path         | Component | Description               |
| ------------ | --------- | ------------------------- |
| `/`          | Redirect  | Redirects to `/dashboard` |
| `/dashboard` | Dashboard | Overview with key metrics |
| `/alerts`    | Alerts    | Alert list with filtering |
| `/incidents` | Incidents | Incident management       |
| `/network`   | Network   | Network topology view     |
| `/settings`  | Settings  | System status and config  |

## Technology stack

| Technology   | Version | Purpose                |
| ------------ | ------- | ---------------------- |
| React        | 19      | UI framework           |
| TypeScript   | 5.x     | Type safety            |
| Vite         | 7       | Build tool, dev server |
| Tailwind CSS | 4       | Utility-first styling  |
| React Router | 7       | Client-side routing    |
| Recharts     | 2.x     | Data visualization     |
| Lucide React | -       | Icons                  |

## API integration

The dashboard proxies API requests to the alerting service:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 3090,
    proxy: {
      '/api': {
        target: 'http://localhost:8084',
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

API calls in the app use the `/api` prefix:

```typescript
// lib/api.ts
export async function getAlerts(): Promise<Alert[]> {
  const response = await fetch('/api/alerts')
  return response.json()
}

export async function acknowledgeAlert(id: string): Promise<void> {
  await fetch(`/api/alerts/${id}/acknowledge`, { method: 'POST' })
}
```

## UI components

### Layout

Sidebar navigation with links to all routes. Displays current page title and system status indicator.

### Card

Container component for content sections with optional title and description.

### Badge

Status indicators with severity-based coloring:

- **Critical**: Red
- **High**: Orange
- **Medium**: Yellow
- **Low**: Blue

### Button

Action buttons with variants (primary, secondary, outline) and loading states.

## Styling

Tailwind CSS 4 with custom theme configuration:

```css
/* index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* ... */
}
```

Components use the `cn()` utility for conditional classes:

```tsx
import { cn } from '@/lib/utils'

function Badge({ variant, children }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium',
        variant === 'critical' && 'bg-red-500/20 text-red-400',
        variant === 'high' && 'bg-orange-500/20 text-orange-400'
      )}
    >
      {children}
    </span>
  )
}
```

## Configuration

| Environment Variable | Description         | Default |
| -------------------- | ------------------- | ------- |
| `VITE_API_URL`       | API base URL (prod) | `/api`  |

## How to run

### With Docker Compose

```bash
# Start dashboard with full stack
make dev-full

# Access at http://localhost:3090
```

### Local development

```bash
cd packages/dashboard

# Install dependencies
npm install

# Start dev server
npm run dev
# Open http://localhost:3090

# Production build
npm run build
npm run preview
```

## Key dependencies

| Package            | Purpose                |
| ------------------ | ---------------------- |
| `react`            | UI framework           |
| `react-router-dom` | Routing                |
| `recharts`         | Charts and graphs      |
| `lucide-react`     | Icons                  |
| `clsx`             | Conditional classes    |
| `tailwind-merge`   | Merge Tailwind classes |
