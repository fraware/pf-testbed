# Prometheus Configuration

Prometheus monitoring configuration for the Provability Fabric testbed.

## Structure

- `scrape_config/` - Service discovery and scraping rules

## Metrics

### Core Metrics
- `testbed_slo_violations_total` - SLO violation counter
- `testbed_request_duration_seconds` - Request latency histogram
- `testbed_theorem_verification_rate` - Theorem verification gauge
- `testbed_active_traces` - Active trace count
- `testbed_honeytoken_alerts` - Security alert counter

### Service Metrics
- Gateway performance and health
- Ingress request patterns
- Ledger transaction metrics
- Egress firewall processing stats

### Business Metrics
- Tenant isolation effectiveness
- Policy enforcement rates
- Certificate generation metrics
- Agent capability utilization

## Scraping Configuration

- **Gateway**: Every 15s
- **Ingress**: Every 15s
- **Ledger**: Every 30s
- **Egress Firewall**: Every 15s
- **Custom Metrics**: Every 60s

## Alerting Rules

- SLO violations
- High latency (> 5s P95)
- High error rates (> 5%)
- Security incidents
- Service unavailability

## Usage

```bash
# Start Prometheus
docker-compose up prometheus

# Access at http://localhost:9090
# View targets, metrics, and alerts
```
