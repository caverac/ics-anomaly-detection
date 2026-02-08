import { Network as NetworkIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Badge, Card, CardContent, CardHeader, CardTitle, Spinner } from '@/components/ui'
import { getIncidents } from '@/lib/api'
import type { Incident } from '@/lib/types'

interface NetworkNode {
  ip: string
  type: 'source' | 'destination'
  incidentCount: number
  maxPriority: string
}

export function Network() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getIncidents({ limit: 100 })
        setIncidents(data)
      } catch (err) {
        console.error('Failed to fetch incidents:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Aggregate network nodes from incidents
  const sourceNodes = new Map<string, NetworkNode>()
  const destNodes = new Map<string, NetworkNode>()

  incidents.forEach((incident) => {
    incident.src_ips.forEach((ip) => {
      const existing = sourceNodes.get(ip)
      if (existing) {
        existing.incidentCount++
        if (incident.priority < existing.maxPriority || !existing.maxPriority) {
          existing.maxPriority = incident.priority
        }
      } else {
        sourceNodes.set(ip, {
          ip,
          type: 'source',
          incidentCount: 1,
          maxPriority: incident.priority
        })
      }
    })

    incident.dst_ips.forEach((ip) => {
      const existing = destNodes.get(ip)
      if (existing) {
        existing.incidentCount++
        if (incident.priority < existing.maxPriority || !existing.maxPriority) {
          existing.maxPriority = incident.priority
        }
      } else {
        destNodes.set(ip, {
          ip,
          type: 'destination',
          incidentCount: 1,
          maxPriority: incident.priority
        })
      }
    })
  })

  const sortedSources = Array.from(sourceNodes.values()).sort(
    (a, b) => b.incidentCount - a.incidentCount
  )
  const sortedDests = Array.from(destNodes.values()).sort(
    (a, b) => b.incidentCount - a.incidentCount
  )

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
        <h1 className="text-2xl font-bold">Network Overview</h1>
        <p className="text-muted-foreground">
          Traffic sources and destinations involved in incidents
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Source IPs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <NetworkIcon className="h-5 w-5" />
              Source IPs ({sourceNodes.size})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sortedSources.length === 0 ? (
              <p className="text-muted-foreground">No source IPs found</p>
            ) : (
              <div className="space-y-2">
                {sortedSources.slice(0, 20).map((node) => (
                  <div
                    key={node.ip}
                    className="flex items-center justify-between rounded-md border border-border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="font-mono text-sm">{node.ip}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={node.maxPriority.toLowerCase() as 'p1' | 'p2' | 'p3' | 'p4'}>
                        {node.maxPriority}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {node.incidentCount} incident
                        {node.incidentCount > 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Destination IPs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <NetworkIcon className="h-5 w-5" />
              Destination IPs ({destNodes.size})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sortedDests.length === 0 ? (
              <p className="text-muted-foreground">No destination IPs found</p>
            ) : (
              <div className="space-y-2">
                {sortedDests.slice(0, 20).map((node) => (
                  <div
                    key={node.ip}
                    className="flex items-center justify-between rounded-md border border-border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="font-mono text-sm">{node.ip}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={node.maxPriority.toLowerCase() as 'p1' | 'p2' | 'p3' | 'p4'}>
                        {node.maxPriority}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {node.incidentCount} incident
                        {node.incidentCount > 1 ? 's' : ''}
                      </span>
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
