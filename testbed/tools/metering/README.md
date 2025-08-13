# Provability Fabric Testbed Metering & Billing Tools

This directory contains tools for tracking usage metrics, generating invoices, and managing billing for the Provability Fabric Testbed.

## Overview

The metering system provides:

- **Usage Tracking**: Monitor CPU, network, API calls, tool executions, and more
- **Billing Tiers**: Basic, Professional, and Enterprise pricing plans
- **Invoice Generation**: Automated billing with detailed cost breakdowns
- **Stripe Integration**: Optional integration with Stripe for payment processing
- **Prometheus Metrics**: Export usage data in Prometheus format for monitoring

## Quick Start

### 1. Install Dependencies

```bash
cd testbed/tools/metering
npm install
```

### 2. Set Environment Variables (Optional)

```bash
# For Stripe integration
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export STRIPE_ENABLED="true"
```

### 3. Run the CLI

```bash
# Show help
npm start -- --help

# Generate an invoice
npm start -- generate-invoice acme-corp 2025-01

# View usage metrics
npm start -- usage acme-corp 2025-01

# List billing tiers
npm start -- tiers
```

## CLI Commands

### Generate Invoice

Generate an invoice for a tenant and billing period:

```bash
npm start -- generate-invoice <tenant-id> <period> [options]
```

**Arguments:**

- `tenant-id`: The tenant identifier (e.g., "acme-corp")
- `period`: Billing period in YYYY-MM format (e.g., "2025-01")

**Options:**

- `-o, --output <file>`: Save invoice to JSON file
- `--stripe`: Enable Stripe integration

**Example:**

```bash
npm start -- generate-invoice acme-corp 2025-01 -o invoice.json
```

### View Usage Metrics

View usage metrics for a tenant and period:

```bash
npm start -- usage <tenant-id> <period> [options]
```

**Options:**

- `-f, --format <format>`: Output format (table, json, csv) [default: table]
- `-o, --output <file>`: Save output to file

**Example:**

```bash
# Table format (default)
npm start -- usage acme-corp 2025-01

# JSON format
npm start -- usage acme-corp 2025-01 -f json -o metrics.json

# CSV format
npm start -- usage acme-corp 2025-01 -f csv -o metrics.csv
```

### List Invoices

List all invoices for a tenant:

```bash
npm start -- invoices <tenant-id> [options]
```

**Options:**

- `-o, --output <file>`: Save invoices to JSON file

**Example:**

```bash
npm start -- invoices acme-corp -o invoices.json
```

### Export Prometheus Metrics

Export usage data in Prometheus metrics format:

```bash
npm start -- export-metrics [options]
```

**Options:**

- `-o, --output <file>`: Save metrics to file

**Example:**

```bash
npm start -- export-metrics -o metrics.prom
```

### List Billing Tiers

View available billing tiers and pricing:

```bash
npm start -- tiers [options]
```

**Options:**

- `-o, --output <file>`: Save tiers to JSON file

**Example:**

```bash
npm start -- tiers -o tiers.json
```

### Simulate Usage

Simulate usage metrics for testing purposes:

```bash
npm start -- simulate-usage <tenant-id> <sessions> [options]
```

**Arguments:**

- `tenant-id`: The tenant identifier
- `sessions`: Number of sessions to simulate

**Options:**

- `--period <period>`: Billing period (default: 2025-01)

**Example:**

```bash
npm start -- simulate-usage acme-corp 100 --period 2025-01
```

## Billing Tiers

### Basic Tier ($50/month)

- **CPU**: $0.36/hour
- **Network**: $0.05/MB
- **API Calls**: $0.001/call
- **Tool Executions**: $0.01/execution
- **Data Retrievals**: $0.005/retrieval
- **Monthly Quotas**:
  - CPU: 1 hour
  - Network: 1 GB
  - API Calls: 10,000
  - Tool Executions: 1,000
  - Data Retrievals: 500

### Professional Tier ($200/month)

- **CPU**: $0.288/hour (20% discount)
- **Network**: $0.04/MB (20% discount)
- **API Calls**: $0.0008/call (20% discount)
- **Tool Executions**: $0.008/execution (20% discount)
- **Data Retrievals**: $0.004/retrieval (20% discount)
- **Risk Multiplier**: 0.9x
- **Monthly Quotas**:
  - CPU: 2 hours
  - Network: 5 GB
  - API Calls: 50,000
  - Tool Executions: 5,000
  - Data Retrievals: 2,500

### Enterprise Tier ($500/month)

- **CPU**: $0.216/hour (40% discount)
- **Network**: $0.03/MB (40% discount)
- **API Calls**: $0.0005/call (50% discount)
- **Tool Executions**: $0.005/execution (50% discount)
- **Data Retrievals**: $0.003/retrieval (40% discount)
- **Risk Multiplier**: 0.8x
- **Monthly Quotas**:
  - CPU: 5 hours
  - Network: 20 GB
  - API Calls: 200,000
  - Tool Executions: 20,000
  - Data Retrievals: 10,000

## Usage Metrics

The system tracks the following metrics per session:

- **CPU Usage**: Execution time in milliseconds
- **Network Usage**: Data transfer in bytes
- **API Calls**: Number of API requests
- **Tool Executions**: Number of tool calls
- **Data Retrievals**: Number of data access operations
- **Egress Scans**: Content security scans
- **Policy Checks**: Security policy validations
- **Violations**: Security policy violations
- **Risk Score**: Calculated risk level (0-1)

## Cost Calculation

Costs are calculated as follows:

```
Total Cost = Base Price + Usage Costs + Risk Adjustment

Usage Costs = (CPU × CPU Price) + (Network × Network Price) +
              (API Calls × API Price) + (Tools × Tool Price) +
              (Data × Data Price) + (Egress × Egress Price) +
              (Policy × Policy Price) + (Violations × Violation Price)

Risk Adjustment = Total Base Cost × (Risk Multiplier - 1)
```

## Stripe Integration

The metering system can optionally integrate with Stripe for payment processing:

1. **Set Environment Variables**:

   ```bash
   export STRIPE_SECRET_KEY="sk_test_..."
   export STRIPE_WEBHOOK_SECRET="whsec_..."
   export STRIPE_ENABLED="true"
   ```

2. **Configure Price IDs**:
   Update the `price_ids` in the Stripe configuration to match your Stripe product prices.

3. **Webhook Handling**:
   Set up Stripe webhooks to handle payment events (invoices, payments, etc.).

## Prometheus Integration

Usage metrics can be exported in Prometheus format for integration with monitoring systems:

```bash
npm start -- export-metrics -o /tmp/pf_usage.prom
```

The exported metrics include:

- `pf_usage_cpu_ms`: CPU usage counter
- `pf_usage_network_bytes`: Network usage counter
- `pf_usage_api_calls`: API calls counter
- `pf_usage_tool_executions`: Tool executions counter
- `pf_usage_data_retrievals`: Data retrievals counter
- `pf_usage_egress_scans`: Egress scans counter
- `pf_usage_policy_checks`: Policy checks counter
- `pf_usage_violations`: Violations counter
- `pf_usage_risk_score`: Risk score gauge

## Testing

### Run Tests

```bash
npm test
```

### Simulate Usage

```bash
# Simulate 100 sessions for testing
npm start -- simulate-usage test-tenant 100

# Generate invoice for simulated usage
npm start -- generate-invoice test-tenant 2025-01
```

## Configuration

### Environment Variables

| Variable                | Description               | Default       |
| ----------------------- | ------------------------- | ------------- |
| `STRIPE_SECRET_KEY`     | Stripe secret key         | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret     | `whsec_...`   |
| `STRIPE_ENABLED`        | Enable Stripe integration | `false`       |

### Custom Billing Tiers

To customize billing tiers, modify the `billingTiers` Map in `metering.ts`:

```typescript
this.billingTiers = new Map([
  [
    "custom",
    {
      name: "Custom Tier",
      base_price_usd: 100.0,
      cpu_price_per_ms: 0.00000005,
      // ... other pricing
    },
  ],
]);
```

## Integration with Testbed

The metering service integrates with the testbed through:

1. **Gateway Integration**: Usage metrics are recorded during agent execution
2. **Policy Kernel**: Policy checks and violations are tracked
3. **Egress Firewall**: Egress scans are counted
4. **Retrieval Gateway**: Data retrievals are monitored

## Troubleshooting

### Common Issues

1. **No Usage Metrics Found**:
   - Ensure the tenant ID and period are correct
   - Check that usage has been recorded for the specified period

2. **Stripe Integration Errors**:
   - Verify environment variables are set correctly
   - Check Stripe API key permissions
   - Ensure webhook endpoints are configured

3. **Permission Denied Errors**:
   - Check file permissions for output files
   - Ensure the output directory exists and is writable

### Debug Mode

Enable debug logging by setting the log level:

```bash
export LOG_LEVEL=debug
npm start -- generate-invoice acme-corp 2025-01
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

Apache 2.0 License - see LICENSE file for details.
