# Provability Fabric Testbed - Paper-Faithful Implementation

This document describes the implementation of the Provability Fabric testbed that faithfully follows the architecture and methodologies described in the research paper "Provability Fabric: Provable Runtime Control for AI Agents".

## Overview

The testbed implements the paper's end-to-end flow diagram and provides comprehensive observability, monitoring, and validation capabilities. It ensures that the code implementation aligns precisely with the theoretical foundations and security guarantees described in the paper.

## Architecture Alignment

### 1. Decision Path Flow (Prompt 91)

The testbed implements the complete decision path flow as specified in the paper:

```
observe → retrieve(receipt) → plan → kernel → tool broker → egress(cert) → safety case
```

**Key Components:**
- **`testbed/runtime/gateway/src/decision_path.ts`** - Core decision path engine
- **`testbed/runtime/gateway/src/observability.ts`** - Enhanced observability with paper-faithful metrics
- **`testbed/grafana/dashboards/paper-faithful-kpis.json`** - Grafana dashboard mirroring paper KPIs
- **`testbed/tools/synthetic-probe.ts`** - Continuous monitoring probe

**Paper Alignment:**
- Implements the labeled alphabet Σ with explicit label metadata
- Provides complete mediation of tool IPC, filesystem writes, and egress
- Generates signed access receipts with field commitments
- Creates egress certificates with non-interference verdicts
- Produces comprehensive safety cases with evidence chains

### 2. Non-Interference (MonNI) Bridge

**Implementation:**
- Local monitor predicate `MonNI_L(τ)` computed online by the sidecar
- Bridge to global NI claims via proof hashes
- Unwinding obligations (OC, SC, DA) mechanized in Lean

**Paper Alignment:**
- Theorem 4.2: Local-to-global NI bridge
- Lemma 4.1: Local monitor soundness w.r.t. unwinding
- Separation of `ni_claim` from online `ni_monitor`

### 3. Egress Filtering & Certificates

**Implementation:**
- Deterministic PII/secret detectors
- SimHash near-duplicate detection
- Configurable "never reveal X" templates
- Per-emission certificates with redaction summaries

**Paper Alignment:**
- Section 4.4: Egress filtering and certificates
- Certificate schema with `redaction_summary` and `non_interference`
- Defense-in-depth approach (not confidentiality proofs)

### 4. Policy Kernel v2

**Implementation:**
- Model-assisted hints and validation
- DENY→REPLAN loop with structured denial reasons
- Capability/receipt/labels/refinements validation

**Paper Alignment:**
- Section 3.4: Plan-DSL and ActionDSL
- Authorization soundness and policy safety
- Monitor acceptance via prefix-closed languages

## Key Metrics & KPIs

The testbed provides comprehensive metrics that mirror the paper's performance and security requirements:

### Decision Path Metrics
- Phase execution counts and success rates
- Average duration per phase
- Phase-specific metrics (receipts, certificates, tools executed)

### Non-Interference Metrics
- Total checks performed
- Pass/fail rates
- Success rate trends

### Certificate Metrics
- Total certificates generated
- PII/secrets/near-dup detection counts
- Average processing time

### Receipt Metrics
- Total receipts generated
- Valid signature rates
- Expiration tracking

### Performance SLOs
- p95 latency < 2.0s
- p99 latency < 4.0s
- End-to-end journey completion rates

## Continuous Monitoring

### Synthetic Probe
The testbed includes a synthetic probe that runs every minute to verify:

1. **Cert Present** - Egress certificates are generated and valid
2. **Policy Hash Match** - Policy hashes are consistent and untampered
3. **Receipts Verified** - Access receipts have valid signatures and haven't expired
4. **Non-Interference Pass** - All NI checks are passing
5. **Decision Path Complete** - All phases complete successfully

### CI Gates
Comprehensive CI pipeline with 12 jobs covering:

- Synthetic probe validation
- Decision path flow validation
- Non-interference validation
- Egress certificate validation
- Access receipt validation
- Policy kernel validation
- Tool broker mediation
- Safety case generation
- End-to-end integration
- Performance & SLO validation
- Security & compliance
- Final summary & notifications

## Security Guarantees

The testbed provides the security guarantees stated in the paper:

### 1. Authorization Soundness
Every concrete `call(t,_)` is justified by a role–tool relation R under pre-state guards.

### 2. Policy Safety via Monitor Acceptance
Prefix-closed language captured by executable monitors matching the formal semantics.

### 3. Declassification-aware Non-interference
For s₀≈ₗs₀', permitted declassifications, and any j, the low-view verdicts agree.

### 4. Labeler Correctness and Witness Non-forgeability
Emitted labels equal those from schema/taint rules, with membership proofs.

### 5. Implementation Refinement
Traces under documented scheduling and clocks refine the formal semantics.

### 6. Provenance Integrity
Proofs, automata, labelers, and artifacts are cryptographically bound.

### 7. Replay Determinism
Re-execution reproduces low-observable behavior modulo declared redaction.

## Usage

### Starting the Synthetic Probe
```bash
cd testbed
npx ts-node tools/synthetic-probe.ts --start
```

### Checking Probe Status
```bash
cd testbed
npx ts-node tools/synthetic-probe.ts --status
```

### Running Decision Path Flow
```typescript
import { decisionPathEngine } from './runtime/gateway/src/decision_path';
import { observabilityService } from './runtime/gateway/src/observability';

// Execute complete decision path
const trace = await decisionPathEngine.executeDecisionPath(plan, context);

// Get observability metrics
const metrics = observabilityService.getMetrics();
const analytics = observabilityService.getDecisionPathAnalytics();
```

### Accessing Grafana Dashboard
1. Start Grafana: `cd testbed/grafana && make up`
2. Navigate to `http://localhost:3000`
3. Import the `paper-faithful-kpis.json` dashboard
4. Configure Prometheus data source

## Testing

### Unit Tests
```bash
cd testbed/runtime/gateway
npm run test:decision-path
npm run test:monni
npm run test:safety-case
```

### Integration Tests
```bash
cd testbed
npx ts-node tools/run-integration-test.ts
```

### Performance Tests
```bash
cd testbed
npx ts-node tools/run-performance-tests.ts
```

## Configuration

### Environment Variables
- `PF_ENFORCE=true` - Enable policy enforcement mode
- `PF_SYNTHETIC_PROBE=true` - Enable synthetic probe
- `PF_ALERT_THRESHOLD=0.95` - Success rate threshold for alerts

### Probe Configuration
```typescript
const config: ProbeConfig = {
  interval_ms: 60 * 1000,    // 1 minute
  timeout_ms: 30 * 1000,     // 30 seconds
  max_retries: 3,
  alert_threshold: 0.95,     // 95% success rate
  enabled_checks: [
    "cert_present",
    "policy_hash_match", 
    "receipts_verified",
    "non_interference_pass",
    "decision_path_complete"
  ]
};
```

## Monitoring & Alerting

### Security Alerts
The testbed generates security alerts for:
- Policy violations
- Non-interference failures
- Receipt forgery attempts
- Certificate tampering
- Decision path failures

### Alert Severity Levels
- **Critical** - Policy hash mismatches, NI violations
- **High** - Missing certificates, receipt verification failures
- **Medium** - Incomplete decision paths
- **Low** - Performance degradation

### Alert Channels
- Grafana dashboard
- Security alert API
- CI pipeline notifications
- Log aggregation

## Compliance & Auditing

### Evidence Collection
- Decision path traces with complete audit trails
- Signed certificates and receipts
- Safety case evidence chains
- Non-interference proof hashes

### Audit Reports
- Weekly compliance reports
- Security posture assessments
- Performance trend analysis
- Violation summaries

## Future Enhancements

### Planned Features
1. **Lean Integration** - Direct Lean theorem verification
2. **Proof Generation** - Automated proof synthesis
3. **Policy Compilation** - Provider-native guardrails
4. **Advanced Routing** - Risk-aware model selection
5. **Red-team Suites** - Adversarial testing frameworks

### Research Extensions
- Multi-tenant isolation proofs
- Advanced declassification policies
- Temporal logic extensions
- Compositional verification

## Contributing

When contributing to the testbed:

1. **Maintain Paper Alignment** - Ensure all changes align with the research paper
2. **Update Tests** - Add corresponding tests for new functionality
3. **Document Changes** - Update this README and relevant documentation
4. **Run CI Gates** - Ensure all CI checks pass before merging
5. **Update Metrics** - Add new metrics to observability service

## References

- **Research Paper**: "Provability Fabric: Provable Runtime Control for AI Agents"
- **Architecture**: End-to-end flow diagram and security guarantees
- **Theorems**: Micro-refinement, NI bridge, implementation refinement
- **Implementation**: Lean mechanization, Rust sidecar, TypeScript testbed

## Support

For questions about the paper-faithful implementation:

1. Check the research paper for theoretical foundations
2. Review the code comments for implementation details
3. Run the synthetic probe for system health checks
4. Consult the Grafana dashboard for real-time metrics
5. Review CI pipeline results for validation status

---

**Note**: This implementation is designed to be a faithful reproduction of the research paper's architecture. All security guarantees, performance characteristics, and theoretical properties should align with the paper's specifications. Any deviations should be documented and justified.
