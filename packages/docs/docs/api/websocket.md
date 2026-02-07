---
sidebar_position: 2
---

# WebSocket API

Real-time event streaming via WebSocket.

## Connection

```javascript
const ws = new WebSocket('ws://localhost:8080/ws')

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }))
}
```

## Subscriptions

### Subscribe to Alerts

```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'alerts',
  filters: {
    severity: ['critical', 'high'],
    type: ['RECONNAISSANCE', 'PROTOCOL_VIOLATION']
  }
}))
```

### Subscribe to Metrics

```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'metrics',
  interval_seconds: 5
}))
```

## Message Types

### Alert Event

```json
{
  "type": "alert",
  "data": {
    "id": "alert-123",
    "timestamp": "2024-01-15T10:30:00Z",
    "severity": "high",
    "type": "RECONNAISSANCE",
    "source_ip": "192.168.1.50",
    "anomaly_score": 0.89
  }
}
```

### Metrics Update

```json
{
  "type": "metrics",
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "inferences_per_second": 3200,
    "alerts_last_hour": 5,
    "anomaly_score_avg": 0.12
  }
}
```

## Example Client

```typescript
class AlertClient {
  private ws: WebSocket
  private reconnectAttempts = 0

  connect(token: string) {
    this.ws = new WebSocket('ws://localhost:8080/ws')

    this.ws.onopen = () => {
      this.authenticate(token)
      this.subscribe()
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      this.handleMessage(msg)
    }

    this.ws.onclose = () => {
      this.reconnect(token)
    }
  }

  private handleMessage(msg: any) {
    switch (msg.type) {
      case 'alert':
        this.onAlert(msg.data)
        break
      case 'metrics':
        this.onMetrics(msg.data)
        break
    }
  }

  private onAlert(alert: Alert) {
    console.log(`New alert: ${alert.severity} - ${alert.type}`)
  }
}
```
