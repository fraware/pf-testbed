import { AgentRunner, Plan, ExecutionContext, ExecutionResult, GatewayConfig, AccessReceipt } from "./types";
export interface NormalizedTrace {
    plan_id: string;
    agent_stack: string;
    journey: string;
    tenant: string;
    steps: NormalizedStep[];
    receipts: AccessReceipt[];
    cert_id: string;
    timings: {
        plan_start: string;
        plan_end: string;
        total_duration_ms: number;
        step_durations: Record<string, number>;
    };
    metadata: {
        model: string;
        confidence: number;
        risk_level: string;
        capabilities_used: string[];
        shadow_mode: boolean;
        enforce_policies: boolean;
    };
}
export interface NormalizedStep {
    id: string;
    type: string;
    tool: string;
    capability: string;
    status: string;
    duration_ms: number;
    timestamp: string;
    result?: any;
    error?: string;
}
/**
 * Unified Gateway that routes requests to different agent stacks
 * and provides normalized trace export with comparable metrics
 */
export declare class UnifiedGateway {
    private agents;
    private metrics;
    private config;
    private enforceMode;
    constructor(config: GatewayConfig);
    /**
     * Register an agent runner for a specific stack
     */
    registerAgent(stack: string, agent: AgentRunner): void;
    /**
     * Execute a plan using the specified agent stack
     */
    executePlan(stack: string, plan: Plan, context: ExecutionContext): Promise<ExecutionResult>;
    /**
     * Generate normalized trace export for all stacks
     */
    generateNormalizedTrace(stack: string, plan: Plan, context: ExecutionContext, executionTime: number): Promise<NormalizedTrace>;
    /**
     * Generate unique capability token ID
     */
    private generateCapabilityTokenId;
    /**
     * Get metrics for all agent stacks
     */
    getStackMetrics(): Promise<Record<string, any>>;
    /**
     * Get health status for all stacks
     */
    getHealthStatus(): Promise<Record<string, boolean>>;
    /**
     * Export all traces for a specific journey across all stacks
     */
    exportJourneyTraces(_journey: string, _tenant: string): Promise<NormalizedTrace[]>;
    /**
     * Get configuration
     */
    getConfig(): GatewayConfig;
    /**
     * Check if enforce mode is enabled
     */
    isEnforceMode(): boolean;
}
//# sourceMappingURL=unified-gateway.d.ts.map