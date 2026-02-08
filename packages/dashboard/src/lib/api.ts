import type {
  Alert,
  AlertStatus,
  AcknowledgeResponse,
  HealthResponse,
  Incident,
  IncidentStatus,
  StatsResponse
} from './types'

const API_BASE = '/api'

/**
 * Fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

/**
 * Health check
 */
export async function getHealth(): Promise<HealthResponse> {
  return fetchApi<HealthResponse>('/health')
}

/**
 * Get service statistics
 */
export async function getStats(): Promise<StatsResponse> {
  return fetchApi<StatsResponse>('/stats')
}

/**
 * Get alerts with optional filtering
 */
export async function getAlerts(params?: {
  limit?: number
  status?: AlertStatus
  severity?: string
}): Promise<Alert[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.status) searchParams.set('status', params.status)
  if (params?.severity) searchParams.set('severity', params.severity)

  const query = searchParams.toString()
  return fetchApi<Alert[]>(`/alerts${query ? `?${query}` : ''}`)
}

/**
 * Get a specific alert
 */
export async function getAlert(id: string): Promise<Alert> {
  return fetchApi<Alert>(`/alerts/${id}`)
}

/**
 * Acknowledge an alert
 */
export async function acknowledgeAlert(id: string): Promise<AcknowledgeResponse> {
  return fetchApi<AcknowledgeResponse>(`/alerts/${id}/acknowledge`, {
    method: 'POST'
  })
}

/**
 * Resolve an alert
 */
export async function resolveAlert(id: string): Promise<AcknowledgeResponse> {
  return fetchApi<AcknowledgeResponse>(`/alerts/${id}/resolve`, {
    method: 'POST'
  })
}

/**
 * Get incidents with optional filtering
 */
export async function getIncidents(params?: {
  limit?: number
  status?: IncidentStatus
}): Promise<Incident[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.status) searchParams.set('status', params.status)

  const query = searchParams.toString()
  return fetchApi<Incident[]>(`/incidents${query ? `?${query}` : ''}`)
}

/**
 * Get a specific incident
 */
export async function getIncident(id: string): Promise<Incident> {
  return fetchApi<Incident>(`/incidents/${id}`)
}

/**
 * Acknowledge an incident
 */
export async function acknowledgeIncident(id: string): Promise<AcknowledgeResponse> {
  return fetchApi<AcknowledgeResponse>(`/incidents/${id}/acknowledge`, {
    method: 'POST'
  })
}

/**
 * Resolve an incident
 */
export async function resolveIncident(id: string): Promise<AcknowledgeResponse> {
  return fetchApi<AcknowledgeResponse>(`/incidents/${id}/resolve`, {
    method: 'POST'
  })
}
