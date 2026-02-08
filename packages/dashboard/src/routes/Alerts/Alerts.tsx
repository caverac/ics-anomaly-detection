import { AlertTriangle, Check, CheckCircle, Clock, Eye, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner
} from '@/components/ui'
import { acknowledgeAlert, getAlerts, resolveAlert } from '@/lib/api'
import type { Alert, AlertSeverity, AlertStatus } from '@/lib/types'
import { cn, formatDate, formatRelativeTime } from '@/lib/utils'

type FilterStatus = 'all' | AlertStatus
type FilterSeverity = 'all' | AlertSeverity

export function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [filterSeverity, setFilterSeverity] = useState<FilterSeverity>('all')
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchAlerts = async () => {
    try {
      const data = await getAlerts({
        limit: 100,
        status: filterStatus === 'all' ? undefined : filterStatus,
        severity: filterSeverity === 'all' ? undefined : filterSeverity
      })
      setAlerts(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
    const interval = setInterval(fetchAlerts, 10000)
    return () => clearInterval(interval)
  }, [filterStatus, filterSeverity])

  const handleAcknowledge = async (id: string) => {
    setActionLoading(id)
    try {
      await acknowledgeAlert(id)
      await fetchAlerts()
      if (selectedAlert?.id === id) {
        setSelectedAlert(null)
      }
    } catch (err) {
      console.error('Failed to acknowledge:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleResolve = async (id: string) => {
    setActionLoading(id)
    try {
      await resolveAlert(id)
      await fetchAlerts()
      if (selectedAlert?.id === id) {
        setSelectedAlert(null)
      }
    } catch (err) {
      console.error('Failed to resolve:', err)
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Alert list */}
      <div className="flex-1 border-r border-border">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">Alerts</h1>
              <p className="text-sm text-muted-foreground">
                {alerts.length} alerts
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={fetchAlerts}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>

          {/* Filters */}
          <div className="mt-4 flex gap-2">
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
            >
              <option value="all">All Status</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>

            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value as FilterSeverity)}
            >
              <option value="all">All Severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {/* Alert list */}
        <div className="h-[calc(100vh-180px)] overflow-auto scrollbar-thin">
          {error ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              {error}
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mb-2" />
              <p>No alerts found</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={cn(
                    'cursor-pointer p-4 transition-colors hover:bg-secondary/50',
                    selectedAlert?.id === alert.id && 'bg-secondary'
                  )}
                  onClick={() => setSelectedAlert(alert)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={alert.severity}>{alert.severity}</Badge>
                        <Badge variant={alert.status}>{alert.status}</Badge>
                      </div>
                      <h3 className="mt-2 font-medium">{alert.title}</h3>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>
                          {alert.source.src_ip} → {alert.source.dst_ip}
                        </span>
                        <span>•</span>
                        <span>{alert.source.protocol.toUpperCase()}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(alert.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Alert detail */}
      <div className="w-96 bg-card">
        {selectedAlert ? (
          <div className="h-full overflow-auto p-4 scrollbar-thin">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Alert Details</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedAlert(null)}
              >
                ×
              </Button>
            </div>

            <div className="space-y-4">
              <div className="flex gap-2">
                <Badge variant={selectedAlert.severity}>
                  {selectedAlert.severity}
                </Badge>
                <Badge variant={selectedAlert.status}>{selectedAlert.status}</Badge>
              </div>

              <div>
                <h3 className="font-medium">{selectedAlert.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {formatDate(selectedAlert.created_at)}
                </p>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Source</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-muted-foreground">Source IP:</span>
                      <br />
                      {selectedAlert.source.src_ip}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Dest IP:</span>
                      <br />
                      {selectedAlert.source.dst_ip}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Protocol:</span>
                      <br />
                      {selectedAlert.source.protocol.toUpperCase()}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Window:</span>
                      <br />
                      {selectedAlert.source.window_size}s
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Detection</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Ensemble Score</span>
                      <span className="font-mono">
                        {selectedAlert.ensemble_score.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Confidence</span>
                      <span className="font-mono">
                        {(selectedAlert.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Anomaly Type</span>
                      <span>{selectedAlert.anomaly_type || 'Unknown'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="whitespace-pre-wrap text-xs text-muted-foreground">
                    {selectedAlert.description}
                  </pre>
                </CardContent>
              </Card>

              {selectedAlert.status !== 'resolved' && (
                <div className="flex gap-2">
                  {selectedAlert.status === 'open' && (
                    <Button
                      className="flex-1"
                      variant="outline"
                      onClick={() => handleAcknowledge(selectedAlert.id)}
                      disabled={actionLoading === selectedAlert.id}
                    >
                      {actionLoading === selectedAlert.id ? (
                        <Spinner size="sm" className="mr-2" />
                      ) : (
                        <Eye className="mr-2 h-4 w-4" />
                      )}
                      Acknowledge
                    </Button>
                  )}
                  <Button
                    className="flex-1"
                    onClick={() => handleResolve(selectedAlert.id)}
                    disabled={actionLoading === selectedAlert.id}
                  >
                    {actionLoading === selectedAlert.id ? (
                      <Spinner size="sm" className="mr-2" />
                    ) : (
                      <Check className="mr-2 h-4 w-4" />
                    )}
                    Resolve
                  </Button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <div className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 mb-2" />
              <p>Select an alert to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
