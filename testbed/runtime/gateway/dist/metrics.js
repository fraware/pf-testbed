"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.testbedMetrics = exports.TestbedMetrics = void 0;
const prom_client_1 = require("prom-client");
// Prometheus metrics for testbed observability
class TestbedMetrics {
  // Constructor - register all metrics
  constructor() {
    // SLO and violation metrics
    this.sloViolationsTotal = new prom_client_1.Counter({
      name: "testbed_slo_violations_total",
      help: "Total number of SLO violations",
      labelNames: ["tenant", "journey", "slo_type", "severity"],
    });
    // Latency metrics
    this.requestDurationSeconds = new prom_client_1.Histogram({
      name: "testbed_request_duration_seconds",
      help: "Request duration in seconds",
      labelNames: ["tenant", "journey", "endpoint", "method"],
      buckets: [0.1, 0.25, 0.5, 1, 2, 5, 10],
    });
    // Theorem verification metrics
    this.theoremVerificationRate = new prom_client_1.Gauge({
      name: "testbed_theorem_verification_rate",
      help: "Rate of theorem verification success",
      labelNames: ["tenant", "journey"],
    });
    // Trace metrics
    this.activeTracesTotal = new prom_client_1.Gauge({
      name: "testbed_active_traces_total",
      help: "Total number of active traces",
      labelNames: ["tenant", "journey", "status"],
    });
    this.tracesCreatedTotal = new prom_client_1.Counter({
      name: "testbed_traces_created_total",
      help: "Total number of traces created",
      labelNames: ["tenant", "journey"],
    });
    // Honeytoken metrics
    this.honeytokenAlertsTotal = new prom_client_1.Counter({
      name: "testbed_honeytoken_alerts_total",
      help: "Total number of honeytoken alerts",
      labelNames: ["tenant", "type", "severity"],
    });
    // Access receipt metrics
    this.accessReceiptsTotal = new prom_client_1.Counter({
      name: "testbed_access_receipts_total",
      help: "Total number of access receipts",
      labelNames: ["tenant", "journey", "status"],
    });
    // Certificate metrics
    this.certificateStatusTotal = new prom_client_1.Gauge({
      name: "testbed_certificate_status_total",
      help: "Total certificates by status",
      labelNames: ["tenant", "status", "type"],
    });
    // Plan execution metrics
    this.planExecutionsTotal = new prom_client_1.Counter({
      name: "testbed_plan_executions_total",
      help: "Total number of plan executions",
      labelNames: ["tenant", "journey", "status"],
    });
    this.planExecutionDurationSeconds = new prom_client_1.Histogram({
      name: "testbed_plan_execution_duration_seconds",
      help: "Plan execution duration in seconds",
      labelNames: ["tenant", "journey"],
      buckets: [1, 5, 10, 30, 60, 120, 300],
    });
    // Error metrics
    this.errorsTotal = new prom_client_1.Counter({
      name: "testbed_errors_total",
      help: "Total number of errors",
      labelNames: ["tenant", "journey", "error_type", "severity"],
    });
    // Throughput metrics
    this.requestsTotal = new prom_client_1.Counter({
      name: "testbed_requests_total",
      help: "Total number of requests",
      labelNames: ["tenant", "journey", "method", "status"],
    });
    // Register all metrics with Prometheus
    prom_client_1.register.registerMetric(this.sloViolationsTotal);
    prom_client_1.register.registerMetric(this.requestDurationSeconds);
    prom_client_1.register.registerMetric(this.theoremVerificationRate);
    prom_client_1.register.registerMetric(this.activeTracesTotal);
    prom_client_1.register.registerMetric(this.tracesCreatedTotal);
    prom_client_1.register.registerMetric(this.honeytokenAlertsTotal);
    prom_client_1.register.registerMetric(this.accessReceiptsTotal);
    prom_client_1.register.registerMetric(this.certificateStatusTotal);
    prom_client_1.register.registerMetric(this.planExecutionsTotal);
    prom_client_1.register.registerMetric(this.planExecutionDurationSeconds);
    prom_client_1.register.registerMetric(this.errorsTotal);
    prom_client_1.register.registerMetric(this.requestsTotal);
  }
  // SLO violation tracking
  recordSloViolation(tenant, journey, sloType, severity) {
    this.sloViolationsTotal.inc({
      tenant,
      journey,
      slo_type: sloType,
      severity,
    });
  }
  // Request duration tracking
  startRequestTimer(tenant, journey, endpoint, method) {
    const timer = this.requestDurationSeconds.startTimer({
      tenant,
      journey,
      endpoint,
      method,
    });
    return () => timer();
  }
  // Theorem verification tracking
  updateTheoremVerificationRate(tenant, journey, rate) {
    this.theoremVerificationRate.set({ tenant, journey }, rate);
  }
  // Trace tracking
  incrementActiveTraces(tenant, journey, status) {
    this.activeTracesTotal.inc({ tenant, journey, status });
  }
  decrementActiveTraces(tenant, journey, status) {
    this.activeTracesTotal.dec({ tenant, journey, status });
  }
  recordTraceCreated(tenant, journey) {
    this.tracesCreatedTotal.inc({ tenant, journey });
  }
  // Honeytoken tracking
  recordHoneytokenAlert(tenant, type, severity) {
    this.honeytokenAlertsTotal.inc({ tenant, type, severity });
  }
  // Access receipt tracking
  recordAccessReceipt(tenant, journey, status) {
    this.accessReceiptsTotal.inc({ tenant, journey, status });
  }
  // Certificate tracking
  updateCertificateStatus(tenant, status, type, count) {
    this.certificateStatusTotal.set({ tenant, status, type }, count);
  }
  // Plan execution tracking
  recordPlanExecution(tenant, journey, status) {
    this.planExecutionsTotal.inc({ tenant, journey, status });
  }
  startPlanExecutionTimer(tenant, journey) {
    const timer = this.planExecutionDurationSeconds.startTimer({
      tenant,
      journey,
    });
    return () => timer();
  }
  // Error tracking
  recordError(tenant, journey, errorType, severity) {
    this.errorsTotal.inc({ tenant, journey, error_type: errorType, severity });
  }
  // Request tracking
  recordRequest(tenant, journey, method, status) {
    this.requestsTotal.inc({ tenant, journey, method, status });
  }
  // Get metrics for Prometheus endpoint
  getMetrics() {
    return prom_client_1.register.metrics();
  }
  // Reset all metrics (useful for testing)
  reset() {
    prom_client_1.register.clear();
  }
}
exports.TestbedMetrics = TestbedMetrics;
// Export singleton instance
exports.testbedMetrics = new TestbedMetrics();
//# sourceMappingURL=metrics.js.map
