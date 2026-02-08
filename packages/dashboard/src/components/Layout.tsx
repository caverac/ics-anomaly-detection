import {
  Activity,
  AlertTriangle,
  FileWarning,
  LayoutDashboard,
  Network,
  Settings
} from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/alerts', icon: AlertTriangle, label: 'Alerts' },
  { to: '/incidents', icon: FileWarning, label: 'Incidents' },
  { to: '/network', icon: Network, label: 'Network' },
  { to: '/settings', icon: Settings, label: 'Settings' }
]

export function Layout() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card">
        <div className="flex h-16 items-center gap-2 border-b border-border px-6">
          <Activity className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">ICS Monitor</span>
        </div>

        <nav className="flex flex-col gap-1 p-4">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="absolute bottom-4 left-4 right-4">
          <div className="rounded-md border border-border bg-secondary/50 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              System Operational
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
