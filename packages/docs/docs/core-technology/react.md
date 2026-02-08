# React

React is used for the **dashboard** - a real-time monitoring interface for alerts and incidents.

## Why React?

### Component-based architecture

React's component model maps well to dashboard UI:

- Alert cards
- Incident lists
- Status badges
- Navigation

Each component is self-contained and reusable.

### Rich ecosystem

React has the largest frontend ecosystem:

- Thousands of component libraries
- Excellent tooling (Vite, ESLint, Prettier)
- Strong TypeScript support

### Declarative UI

React's declarative approach makes complex UIs manageable:

```tsx
// UI is a function of state
function AlertList({ alerts }) {
  return alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />)
}
```

### Performance

React 19's improvements:

- Automatic batching
- Concurrent rendering
- Suspense for data fetching
- React Server Components (when needed)

### Developer experience

- Hot module replacement (HMR)
- React DevTools
- Error boundaries
- TypeScript integration

## Stack

| Technology         | Purpose                |
| ------------------ | ---------------------- |
| **React 19**       | UI framework           |
| **TypeScript**     | Type safety            |
| **Vite 7**         | Build tool, dev server |
| **Tailwind CSS 4** | Utility-first styling  |
| **React Router 7** | Client-side routing    |
| **Recharts**       | Data visualization     |
| **Lucide React**   | Icons                  |

## Alternatives considered

| Alternative | Pros                             | Cons                              |
| ----------- | -------------------------------- | --------------------------------- |
| **Vue 3**   | Simpler learning curve           | Smaller ecosystem                 |
| **Svelte**  | No virtual DOM, smaller bundle   | Smaller ecosystem, less mature    |
| **Angular** | Full framework, enterprise ready | Heavy, complex, prescriptive      |
| **Solid**   | Fine-grained reactivity, fast    | Very new, small ecosystem         |
| **HTMX**    | Simple, server-driven            | Limited for complex interactivity |

## Limitations

### Bundle size

React + ecosystem adds ~100KB+ (gzipped). Mitigations:

- Code splitting with React.lazy
- Tree shaking
- Minimal dependencies

### Learning curve

React concepts take time:

- Hooks (useState, useEffect, useContext)
- Component lifecycle
- State management patterns

### State management complexity

For larger apps, local state isn't enough. Options:

- Context API (used here)
- Zustand
- Redux Toolkit

### SEO

React SPAs need extra work for SEO. For an internal dashboard, this isn't relevant.

### No built-in routing/forms

Unlike Angular, React doesn't include:

- Routing (need react-router)
- Form handling (need react-hook-form or similar)

## Project structure

```
packages/dashboard/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Root component, routing
│   ├── index.css             # Tailwind imports, theme
│   ├── components/
│   │   ├── Layout.tsx        # Sidebar navigation
│   │   └── ui/               # Reusable UI components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── badge.tsx
│   │       └── spinner.tsx
│   ├── routes/
│   │   ├── Dashboard/        # Overview page
│   │   ├── Alerts/           # Alert management
│   │   ├── Incidents/        # Incident management
│   │   ├── Network/          # Network overview
│   │   └── Settings/         # System status
│   └── lib/
│       ├── api.ts            # API client
│       ├── types.ts          # TypeScript interfaces
│       └── utils.ts          # Utility functions
├── package.json
├── vite.config.ts
├── tsconfig.json
└── Dockerfile
```

## Styling with Tailwind

Tailwind CSS 4 provides:

- Utility-first classes
- JIT compilation
- Dark mode support
- Custom theme configuration

```tsx
// Example component with Tailwind
function Badge({ variant, children }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium',
        variant === 'critical' && 'bg-red-500/20 text-red-400',
        variant === 'warning' && 'bg-yellow-500/20 text-yellow-400'
      )}
    >
      {children}
    </span>
  )
}
```

## Running

```bash
# Development
cd packages/dashboard
yarn install
yarn dev
# Open http://localhost:3090

# Production build
yarn build
yarn preview
```

## API integration

The dashboard proxies API requests through Vite:

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

```typescript
// lib/api.ts
export async function getAlerts(): Promise<Alert[]> {
  const response = await fetch('/api/alerts')
  return response.json()
}
```
