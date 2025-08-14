"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.observabilityService = exports.ObservabilityService = void 0;
// Core observability service
class ObservabilityService {
    constructor() {
        this.traceContexts = new Map();
        this.savedViews = new Map();
        this.metrics = {
            latency_p95: 0,
            latency_p99: 0,
            throughput: 0,
            error_rate: 0,
            success_rate: 0,
            active_traces: 0,
            theorem_verification_rate: 0,
        };
    }
    // Create new trace context with Lean theorem linking
    createTraceContext(plan, request_id, session_id, user_id) {
        const trace_id = this.generateTraceId();
        const context = {
            trace_id,
            plan_id: plan.id,
            tenant: plan.tenant,
            journey: plan.journey,
            user_id,
            session_id,
            request_id,
            timestamp: new Date().toISOString(),
            lean_theorems: [],
            spec_lines: [],
            metadata: {
                agent: plan.metadata.agent,
                model: plan.metadata.model,
                confidence: plan.metadata.confidence,
                risk_level: plan.metadata.risk_level,
            },
        };
        this.traceContexts.set(trace_id, context);
        this.updateMetrics();
        return context;
    }
    // Link trace to Lean theorem and spec lines
    linkLeanTheorem(trace_id, theorem, spec_lines) {
        const context = this.traceContexts.get(trace_id);
        if (!context) {
            throw new Error(`Trace context not found: ${trace_id}`);
        }
        context.lean_theorems.push(theorem);
        context.spec_lines.push(...spec_lines);
        // Update verification status
        this.updateTheoremVerificationStatus(trace_id, theorem.theorem_id);
    }
    // Update theorem verification status
    updateTheoremVerificationStatus(trace_id, theorem_id) {
        const context = this.traceContexts.get(trace_id);
        if (!context)
            return;
        const theorem = context.lean_theorems.find((t) => t.theorem_id === theorem_id);
        if (theorem) {
            theorem.verification_status = "verified";
            theorem.last_verified = new Date().toISOString();
        }
    }
    // Get complete trace context for UI calls drawer
    getTraceContext(trace_id) {
        return this.traceContexts.get(trace_id) || null;
    }
    // Get trace chain: Trace → Plan → Theorem → Cert
    getTraceChain(trace_id) {
        const context = this.traceContexts.get(trace_id);
        if (!context)
            return null;
        // In a real implementation, you would fetch these from your data stores
        return {
            trace: context,
            plan: {}, // Would be fetched from plan store
            theorems: context.lean_theorems,
            certificates: [], // Would be fetched from cert store
        };
    }
    // Save view for specific journey and tenant
    saveView(view) {
        const id = this.generateViewId();
        const now = new Date().toISOString();
        const savedView = {
            ...view,
            id,
            created_at: now,
            updated_at: now,
        };
        this.savedViews.set(id, savedView);
        return savedView;
    }
    // Get saved views for tenant and journey
    getSavedViews(tenant, journey) {
        return Array.from(this.savedViews.values()).filter((view) => view.tenant === tenant && view.journey === journey);
    }
    // Update metrics
    updateMetrics() {
        this.metrics.active_traces = this.traceContexts.size;
        // Calculate other metrics based on trace data
        const traces = Array.from(this.traceContexts.values());
        const verifiedTheorems = traces.reduce((count, trace) => count +
            trace.lean_theorems.filter((t) => t.verification_status === "verified")
                .length, 0);
        const totalTheorems = traces.reduce((count, trace) => count + trace.lean_theorems.length, 0);
        this.metrics.theorem_verification_rate =
            totalTheorems > 0 ? verifiedTheorems / totalTheorems : 0;
    }
    // Get current metrics
    getMetrics() {
        return { ...this.metrics };
    }
    // Clean up old traces (retention policy)
    cleanupOldTraces(retentionDays = 90) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - retentionDays);
        for (const [trace_id, context] of this.traceContexts.entries()) {
            if (new Date(context.timestamp) < cutoff) {
                this.traceContexts.delete(trace_id);
            }
        }
        this.updateMetrics();
    }
    // Generate unique IDs
    generateTraceId() {
        return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    generateViewId() {
        return `view_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}
exports.ObservabilityService = ObservabilityService;
// Export singleton instance
exports.observabilityService = new ObservabilityService();
//# sourceMappingURL=observability.js.map