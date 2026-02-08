import { CheckCircle, Settings as SettingsIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Badge, Card, CardContent, CardHeader, CardTitle, Spinner } from '@/components/ui'
import { getHealth, getStats } from '@/lib/api'
import type { HealthResponse, StatsResponse } from '@/lib/types'
import { formatNumber } from '@/lib/utils'

export function Settings() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [healthData, statsData] = await Promise.all([getHealth(), getStats()])
        setHealth(healthData)
        setStats(statsData)
      } catch (err) {
        console.error('Failed to fetch data:', err)
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

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">System configuration and status</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              System Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Overall Status</span>
                <Badge variant={health?.status === 'healthy' ? 'default' : 'destructive'}>
                  {health?.status || 'Unknown'}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Kafka Connection</span>
                <div className="flex items-center gap-2">
                  {health?.kafka_connected ? (
                    <CheckCircle className="h-4 w-4 text-primary" />
                  ) : (
                    <span className="h-4 w-4 rounded-full bg-destructive" />
                  )}
                  <span>{health?.kafka_connected ? 'Connected' : 'Disconnected'}</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Redis Connection</span>
                <div className="flex items-center gap-2">
                  {health?.redis_connected ? (
                    <CheckCircle className="h-4 w-4 text-primary" />
                  ) : (
                    <span className="h-4 w-4 rounded-full bg-destructive" />
                  )}
                  <span>{health?.redis_connected ? 'Connected' : 'Disconnected'}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Processing Statistics */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Alerts Processed</span>
                <span className="font-mono">{formatNumber(stats?.alerts_processed ?? 0)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Incidents Created</span>
                <span className="font-mono">{formatNumber(stats?.incidents_created ?? 0)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Incidents Updated</span>
                <span className="font-mono">{formatNumber(stats?.incidents_updated ?? 0)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Notifications Sent</span>
                <span className="font-mono">{formatNumber(stats?.notifications_sent ?? 0)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Dedup Suppressed</span>
                <span className="font-mono">{formatNumber(stats?.dedup_suppressed ?? 0)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Escalations</span>
                <span className="font-mono">{formatNumber(stats?.escalations ?? 0)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* API Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>API Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Alerting API</span>
                <span className="font-mono text-sm">http://localhost:8084</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Simulator API</span>
                <span className="font-mono text-sm">http://localhost:8083</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Kafka Broker</span>
                <span className="font-mono text-sm">localhost:9094</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Redis</span>
                <span className="font-mono text-sm">localhost:6379</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle>About</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium">ICS Anomaly Detection Dashboard</h4>
                <p className="text-sm text-muted-foreground">
                  Real-time monitoring for Industrial Control System network anomalies
                </p>
              </div>

              <div className="text-sm text-muted-foreground">
                <p>
                  This dashboard displays alerts and incidents detected by the ML-based anomaly
                  detection pipeline.
                </p>
              </div>

              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground">Version 0.1.0</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
