import { Check, CheckCircle, Clock, Eye, FileWarning, RefreshCw } from 'lucide-react'
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
import { acknowledgeIncident, getIncidents, resolveIncident } from '@/lib/api'
import type { Incident, IncidentStatus } from '@/lib/types'
import { cn, formatDate, formatRelativeTime } from '@/lib/utils'

type FilterStatus = 'all' | IncidentStatus

export function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchIncidents = async () => {
    try {
      const data = await getIncidents({
        limit: 100,
        status: filterStatus === 'all' ? undefined : filterStatus
      })
      setIncidents(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch incidents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchIncidents()
    const interval = setInterval(fetchIncidents, 10000)
    return () => clearInterval(interval)
  }, [filterStatus])

  const handleAcknowledge = async (id: string) => {
    setActionLoading(id)
    try {
      await acknowledgeIncident(id)
      await fetchIncidents()
      if (selectedIncident?.id === id) {
        setSelectedIncident(null)
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
      await resolveIncident(id)
      await fetchIncidents()
      if (selectedIncident?.id === id) {
        setSelectedIncident(null)
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
      {/* Incident list */}
      <div className="flex-1 border-r border-border">
        <div className="border-b border-border p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">Incidents</h1>
              <p className="text-sm text-muted-foreground">
                {incidents.length} incidents
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={fetchIncidents}>
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
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>

        {/* Incident list */}
        <div className="h-[calc(100vh-180px)] overflow-auto scrollbar-thin">
          {error ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              {error}
            </div>
          ) : incidents.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mb-2" />
              <p>No incidents found</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {incidents.map((incident) => (
                <div
                  key={incident.id}
                  className={cn(
                    'cursor-pointer p-4 transition-colors hover:bg-secondary/50',
                    selectedIncident?.id === incident.id && 'bg-secondary'
                  )}
                  onClick={() => setSelectedIncident(incident)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            incident.priority.toLowerCase() as 'p1' | 'p2' | 'p3' | 'p4'
                          }
                        >
                          {incident.priority}
                        </Badge>
                        <Badge variant={incident.status}>{incident.status}</Badge>
                      </div>
                      <h3 className="mt-2 font-medium">{incident.title}</h3>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{incident.anomaly_count} anomalies</span>
                        <span>•</span>
                        <span>Score: {incident.max_ensemble_score.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(incident.updated_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Incident detail */}
      <div className="w-96 bg-card">
        {selectedIncident ? (
          <div className="h-full overflow-auto p-4 scrollbar-thin">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Incident Details</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedIncident(null)}
              >
                ×
              </Button>
            </div>

            <div className="space-y-4">
              <div className="flex gap-2">
                <Badge
                  variant={
                    selectedIncident.priority.toLowerCase() as 'p1' | 'p2' | 'p3' | 'p4'
                  }
                >
                  {selectedIncident.priority}
                </Badge>
                <Badge variant={selectedIncident.status}>
                  {selectedIncident.status}
                </Badge>
              </div>

              <div>
                <h3 className="font-medium">{selectedIncident.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Created: {formatDate(selectedIncident.created_at)}
                </p>
                <p className="text-sm text-muted-foreground">
                  Updated: {formatDate(selectedIncident.updated_at)}
                </p>
              </div>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Statistics</CardTitle>
                </CardHeader>
                <CardContent className="text-sm">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Anomaly Count</span>
                      <span className="font-mono">{selectedIncident.anomaly_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Max Score</span>
                      <span className="font-mono">
                        {selectedIncident.max_ensemble_score.toFixed(3)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Alert Count</span>
                      <span className="font-mono">
                        {selectedIncident.alert_ids.length}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Source IPs</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1">
                    {selectedIncident.src_ips.map((ip) => (
                      <Badge key={ip} variant="secondary">
                        {ip}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Destination IPs</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-1">
                    {selectedIncident.dst_ips.map((ip) => (
                      <Badge key={ip} variant="secondary">
                        {ip}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {selectedIncident.anomaly_types.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Anomaly Types</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1">
                      {selectedIncident.anomaly_types.map((type) => (
                        <Badge key={type} variant="outline">
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Description</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {selectedIncident.description}
                  </p>
                </CardContent>
              </Card>

              {selectedIncident.status !== 'resolved' && (
                <div className="flex gap-2">
                  {selectedIncident.status === 'active' && (
                    <Button
                      className="flex-1"
                      variant="outline"
                      onClick={() => handleAcknowledge(selectedIncident.id)}
                      disabled={actionLoading === selectedIncident.id}
                    >
                      {actionLoading === selectedIncident.id ? (
                        <Spinner size="sm" className="mr-2" />
                      ) : (
                        <Eye className="mr-2 h-4 w-4" />
                      )}
                      Acknowledge
                    </Button>
                  )}
                  <Button
                    className="flex-1"
                    onClick={() => handleResolve(selectedIncident.id)}
                    disabled={actionLoading === selectedIncident.id}
                  >
                    {actionLoading === selectedIncident.id ? (
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
              <FileWarning className="mx-auto h-12 w-12 mb-2" />
              <p>Select an incident to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
