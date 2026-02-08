import { Activity, AlertTriangle, CheckCircle, Clock, FileWarning, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Badge, Card, CardContent, CardHeader, CardTitle, Spinner } from '@/components/ui'
import { getAlerts, getHealth, getIncidents, getStats } from '@/lib/api'
import type { Alert, HealthResponse, Incident, StatsResponse } from '@/lib/types'
import { cn, formatNumber, formatRelativeTime } from '@/lib/utils'

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [healthData, statsData, alertsData, incidentsData] = await Promise.all([
          getHealth(),
          getStats(),
          getAlerts({ limit: 5 }),
          getIncidents({ limit: 5 })
        ])
        setHealth(healthData)
        setStats(statsData)
        setAlerts(alertsData)
        setIncidents(incidentsData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="mt-4 text-lg font-semibold">Connection Error</h2>
          <p className="mt-2 text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  const openAlerts = alerts.filter((a) => a.status === 'open').length
  const activeIncidents = incidents.filter((i) => i.status === 'active').length

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">ICS Anomaly Detection Overview</p>
      </div>

      {/* Status bar */}
      <div className="mb-6 flex items-center gap-4">
        <div
          className={cn(
            'flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium',
            health?.status === 'healthy'
              ? 'bg-primary/10 text-primary'
              : 'bg-destructive/10 text-destructive'
          )}
        >
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              health?.status === 'healthy' ? 'bg-primary' : 'bg-destructive'
            )}
          />
          {health?.status === 'healthy' ? 'System Healthy' : 'System Degraded'}
        </div>
        {health?.kafka_connected && <Badge variant="secondary">Kafka Connected</Badge>}
        {health?.redis_connected && <Badge variant="secondary">Redis Connected</Badge>}
      </div>

      {/* Stats cards */}
      <div className="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Alerts Processed
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats?.alerts_processed ?? 0)}</div>
            <p className="text-xs text-muted-foreground">
              {formatNumber(stats?.dedup_suppressed ?? 0)} deduplicated
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Open Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{openAlerts}</div>
            <p className="text-xs text-muted-foreground">Requiring attention</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Incidents
            </CardTitle>
            <FileWarning className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeIncidents}</div>
            <p className="text-xs text-muted-foreground">
              {formatNumber(stats?.incidents_created ?? 0)} total created
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Escalations</CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats?.escalations ?? 0)}</div>
            <p className="text-xs text-muted-foreground">Priority increases</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Recent Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <CheckCircle className="mr-2 h-5 w-5" />
                No recent alerts
              </div>
            ) : (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-start justify-between rounded-md border border-border p-3"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={alert.severity}>{alert.severity}</Badge>
                        <span className="text-sm font-medium">{alert.title}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>
                          {alert.source.src_ip} → {alert.source.dst_ip}
                        </span>
                        <span>•</span>
                        <span>{alert.source.protocol.toUpperCase()}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(alert.created_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Incidents */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileWarning className="h-5 w-5" />
              Recent Incidents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {incidents.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <CheckCircle className="mr-2 h-5 w-5" />
                No recent incidents
              </div>
            ) : (
              <div className="space-y-3">
                {incidents.map((incident) => (
                  <div
                    key={incident.id}
                    className="flex items-start justify-between rounded-md border border-border p-3"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={incident.priority.toLowerCase() as 'p1' | 'p2' | 'p3' | 'p4'}
                        >
                          {incident.priority}
                        </Badge>
                        <span className="text-sm font-medium">{incident.title}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{incident.anomaly_count} anomalies</span>
                        <span>•</span>
                        <span>Score: {incident.max_ensemble_score.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(incident.updated_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
