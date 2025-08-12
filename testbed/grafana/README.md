# Grafana Configuration

Grafana dashboards and provisioning for the Provability Fabric testbed.

## Structure

- `dashboards/` - Custom dashboard definitions
- `provisioning/` - Data source and dashboard provisioning

## Dashboards

### SLO Overview
- Real-time SLO violation tracking
- Performance metrics visualization
- Alert status and history

### Latency Metrics
- P95/P99 performance monitoring
- Request duration histograms
- Service dependency mapping

### Theorem Verification
- Lean proof validation rates
- Theorem execution metrics
- Proof complexity analysis

### Active Traces
- Tenant and journey breakdowns
- Trace lifecycle monitoring
- Performance correlation

### Security Alerts
- Honeytoken and certificate status
- Policy violation tracking
- Threat detection metrics

## Provisioning

Automated setup of:
- Data sources (Prometheus, etc.)
- Dashboard imports
- User and team management
- Alert rules and notifications

## Usage

```bash
# Start Grafana with provisioning
docker-compose up grafana

# Access at http://localhost:3100
# Default credentials: admin/admin
```
