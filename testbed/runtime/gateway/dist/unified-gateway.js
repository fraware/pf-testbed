"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.UnifiedGateway = void 0;
const metrics_1 = require("./metrics");
/**
 * Unified Gateway that routes requests to different agent stacks
 * and provides normalized trace export with comparable metrics
 */
class UnifiedGateway {
    constructor(config) {
        this.agents = new Map();
        this.config = config;
        this.metrics = new metrics_1.TestbedMetrics();
        this.enforceMode = process.env["PF_ENFORCE"] === "true";
    }
    /**
     * Register an agent runner for a specific stack
     */
    registerAgent(stack, agent) {
        this.agents.set(stack, agent);
        console.log(`Registered agent for stack: ${stack}`);
    }
    /**
     * Execute a plan using the specified agent stack
     */
    async executePlan(stack, plan, context) {
        const startTime = Date.now();
        if (!this.agents.has(stack)) {
            throw new Error(`Unsupported agent stack: ${stack}`);
        }
        const agent = this.agents.get(stack);
        try {
            // Record execution start
            this.metrics.recordPlanExecution(plan.tenant, plan.journey, "started");
            // Verify plan
            const verification = await agent.verifyPlan(plan);
            if (!verification.valid) {
                throw new Error(`Plan validation failed: ${verification.errors.join(", ")}`);
            }
            // Execute plan
            const executedPlan = await agent.executePlan(plan);
            // Record execution completion
            const executionTime = Date.now() - startTime;
            this.metrics.recordPlanExecution(plan.tenant, plan.journey, "completed");
            // Generate normalized trace
            const trace = await this.generateNormalizedTrace(stack, executedPlan, context, executionTime);
            return {
                success: true,
                plan_id: plan.id,
                execution_time: executionTime,
                steps_completed: executedPlan.steps.filter((s) => s.status === "completed").length,
                steps_failed: executedPlan.steps.filter((s) => s.status === "failed")
                    .length,
                final_result: executedPlan,
                traces: [trace],
                receipts: verification.receipts.map((r) => ({
                    id: r.id,
                    tenant: plan.tenant,
                    subject: "unknown",
                    shard: "default",
                    query_hash: "unknown",
                    result_hash: "unknown",
                    nonce: "unknown",
                    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
                    signature: "unknown"
                })),
                timestamp: new Date().toISOString(),
            };
        }
        catch (error) {
            const executionTime = Date.now() - startTime;
            this.metrics.recordError(plan.tenant, plan.journey, "execution_error", "high");
            return {
                success: false,
                plan_id: plan.id,
                execution_time: executionTime,
                steps_completed: 0,
                steps_failed: plan.steps.length,
                error: error instanceof Error ? error.message : "Unknown error",
                traces: [],
                receipts: [],
                timestamp: new Date().toISOString(),
            };
        }
    }
    /**
     * Generate normalized trace export for all stacks
     */
    async generateNormalizedTrace(stack, plan, context, executionTime) {
        const stepDurations = {};
        // Calculate step durations
        for (const step of plan.steps) {
            if (step.duration) {
                stepDurations[step.id] = step.duration;
            }
        }
        // Generate capability token ID
        const certId = this.generateCapabilityTokenId(plan, context);
        return {
            plan_id: plan.id,
            agent_stack: stack,
            journey: plan.journey,
            tenant: plan.tenant,
            steps: plan.steps.map((step) => ({
                id: step.id,
                type: step.type,
                tool: step.tool || "unknown",
                capability: step.capability || "unknown",
                status: step.status,
                duration_ms: step.duration || 0,
                timestamp: step.timestamp,
                result: step.result,
                error: step.error || "",
            })),
            receipts: plan.steps
                .filter((s) => s.type === "retrieval" && s.receipt)
                .map((s) => ({
                id: s.receipt,
                tenant: plan.tenant,
                subject: "unknown",
                shard: "default",
                query_hash: "unknown",
                result_hash: "unknown",
                nonce: "unknown",
                expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
                signature: "unknown"
            })),
            cert_id: certId,
            timings: {
                plan_start: plan.timestamp,
                plan_end: new Date().toISOString(),
                total_duration_ms: executionTime,
                step_durations: stepDurations,
            },
            metadata: {
                model: plan.metadata.model,
                confidence: plan.metadata.confidence,
                risk_level: plan.metadata.risk_level,
                capabilities_used: plan.steps
                    .filter((s) => s.capability)
                    .map((s) => s.capability),
                shadow_mode: !this.enforceMode,
                enforce_policies: this.enforceMode,
            },
        };
    }
    /**
     * Generate unique capability token ID
     */
    generateCapabilityTokenId(plan, context) {
        const components = [
            plan.tenant,
            plan.journey,
            context.session_id,
            plan.id,
            Date.now().toString(),
        ];
        return btoa(components.join("|")).replace(/[^a-zA-Z0-9]/g, "");
    }
    /**
     * Get metrics for all agent stacks
     */
    async getStackMetrics() {
        const metrics = {};
        for (const [stack, agent] of this.agents) {
            try {
                const status = await agent.getStatus();
                const stackMetrics = this.metrics.getMetrics();
                metrics[stack] = {
                    status,
                    metrics: stackMetrics,
                    timestamp: new Date().toISOString(),
                };
            }
            catch (error) {
                metrics[stack] = {
                    error: error instanceof Error ? error.message : "Unknown error",
                    timestamp: new Date().toISOString(),
                };
            }
        }
        return metrics;
    }
    /**
     * Get health status for all stacks
     */
    async getHealthStatus() {
        const health = {};
        for (const [stack, agent] of this.agents) {
            try {
                const status = await agent.getStatus();
                health[stack] = status.healthy;
            }
            catch (error) {
                health[stack] = false;
            }
        }
        return health;
    }
    /**
     * Export all traces for a specific journey across all stacks
     */
    async exportJourneyTraces(_journey, _tenant) {
        const traces = [];
        // This would typically query a database or storage system
        // For now, we'll return an empty array
        // In production, this would aggregate traces from all stacks
        return traces;
    }
    /**
     * Get configuration
     */
    getConfig() {
        return this.config;
    }
    /**
     * Check if enforce mode is enabled
     */
    isEnforceMode() {
        return this.enforceMode;
    }
}
exports.UnifiedGateway = UnifiedGateway;
//# sourceMappingURL=unified-gateway.js.map