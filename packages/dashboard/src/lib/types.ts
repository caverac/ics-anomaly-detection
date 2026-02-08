/**
 * Alert severity levels
 */
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'

/**
 * Alert status
 */
export type AlertStatus = 'open' | 'acknowledged' | 'resolved'

/**
 * Incident priority levels
 */
export type IncidentPriority = 'P1' | 'P2' | 'P3' | 'P4'

/**
 * Incident status
 */
export type IncidentStatus = 'active' | 'acknowledged' | 'resolved'

/**
 * Alert source information
 */
export interface AlertSource {
  src_ip: string
  dst_ip: string
  protocol: string
  window_size: number
  window_start: number
}

/**
 * Alert from the alerting service
 */
export interface Alert {
  id: string
  incident_id: string | null
  created_at: string
  severity: AlertSeverity
  status: AlertStatus
  title: string
  description: string
  source: AlertSource
  anomaly_type: string | null
  ensemble_score: number
  confidence: number
  related_anomaly_count: number
  feature_contributions: Record<string, number>
}

/**
 * Incident from the alerting service
 */
export interface Incident {
  id: string
  correlation_key: string
  created_at: string
  updated_at: string
  status: IncidentStatus
  priority: IncidentPriority
  anomaly_count: number
  alert_ids: string[]
  max_ensemble_score: number
  src_ips: string[]
  dst_ips: string[]
  anomaly_types: string[]
  title: string
  description: string
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded'
  kafka_connected: boolean
  redis_connected: boolean
}

/**
 * Service statistics
 */
export interface StatsResponse {
  alerts_processed: number
  incidents_created: number
  incidents_updated: number
  notifications_sent: number
  dedup_suppressed: number
  escalations: number
}

/**
 * Acknowledgement response
 */
export interface AcknowledgeResponse {
  id: string
  status: string
  acknowledged: boolean
}
