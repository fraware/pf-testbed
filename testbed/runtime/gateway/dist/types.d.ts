export interface Plan {
    id: string;
    tenant: string;
    journey: string;
    steps: PlanStep[];
    metadata: PlanMetadata;
    timestamp: string;
    expiresAt: string;
}
export interface PlanStep {
    id: string;
    type: "tool_call" | "decision" | "retrieval" | "verification";
    tool?: string;
    parameters?: Record<string, any>;
    capability?: string;
    receipt?: string;
    status: "pending" | "executing" | "completed" | "failed";
    result?: any;
    error?: string;
    timestamp: string;
    duration?: number;
}
export interface PlanMetadata {
    version: string;
    agent: string;
    model: string;
    confidence: number;
    risk_level: "low" | "medium" | "high" | "critical";
    tags: string[];
    context: Record<string, any>;
}
export interface ToolCall {
    id: string;
    tool: string;
    parameters: Record<string, any>;
    capability: string;
    timestamp: string;
    tenant: string;
}
export interface ToolResult {
    id: string;
    success: boolean;
    result?: any;
    error?: string;
    capability_consumed: string;
    trace: ToolTrace;
    timestamp: string;
}
export interface ToolTrace {
    id: string;
    tool_call_id: string;
    inputs: Record<string, any>;
    outputs: Record<string, any>;
    metadata: Record<string, any>;
    replayable: boolean;
}
export interface AccessReceipt {
    id: string;
    tenant: string;
    subject: string;
    shard: string;
    query_hash: string;
    result_hash: string;
    nonce: string;
    expires_at: string;
    signature: string;
}
export interface VerificationResult {
    plan_id: string;
    valid: boolean;
    errors: string[];
    warnings: string[];
    receipts: AccessReceipt[];
    timestamp: string;
}
export interface AgentRunner {
    name: string;
    version: string;
    capabilities: string[];
    plan(json: any): Promise<Plan>;
    verifyPlan(plan: Plan): Promise<VerificationResult>;
    executePlan(plan: Plan): Promise<Plan>;
    executeTool(call: ToolCall): Promise<ToolResult>;
    exportTrace(plan_id: string): Promise<any>;
    configure(config: AgentConfig): Promise<void>;
    getStatus(): Promise<AgentStatus>;
}
export interface AgentConfig {
    model: string;
    provider: string;
    api_key?: string;
    endpoint?: string;
    timeout: number;
    max_retries: number;
    shadow_mode: boolean;
    enforce_policies: boolean;
}
export interface AgentStatus {
    healthy: boolean;
    version: string;
    uptime: number;
    last_heartbeat: string;
    active_plans: number;
    total_executions: number;
    error_rate: number;
}
export interface GatewayConfig {
    port: number;
    host: string;
    cors_origins: string[];
    rate_limit: {
        window_ms: number;
        max_requests: number;
    };
    auth: {
        enabled: boolean;
        jwt_secret?: string;
        api_keys?: string[];
    };
    monitoring: {
        enabled: boolean;
        metrics_port: number;
        health_check_interval: number;
    };
}
export interface ExecutionContext {
    tenant: string;
    user_id?: string;
    session_id: string;
    request_id: string;
    timestamp: string;
    metadata: Record<string, any>;
}
export interface ExecutionResult {
    success: boolean;
    plan_id: string;
    execution_time: number;
    steps_completed: number;
    steps_failed: number;
    final_result?: any;
    error?: string;
    traces: any[];
    receipts: AccessReceipt[];
    timestamp: string;
}
export declare class PlanValidationError extends Error {
    errors: string[];
    constructor(message: string, errors: string[]);
}
export declare class CapabilityError extends Error {
    capability: string;
    constructor(message: string, capability: string);
}
export declare class ReceiptError extends Error {
    receipt_id: string;
    constructor(message: string, receipt_id: string);
}
export declare class ToolExecutionError extends Error {
    tool: string;
    parameters: any;
    constructor(message: string, tool: string, parameters: any);
}
export declare const SUPPORTED_JOURNEYS: readonly ["support_triage", "expense_approval", "sales_outreach", "hr_onboarding", "dev_triage"];
export declare const SUPPORTED_TOOLS: readonly ["slack", "email", "calendar", "notion", "stripe", "github", "search", "fetch"];
export declare const CAPABILITY_SCOPES: readonly ["read", "write", "delete", "admin"];
export declare const RISK_LEVELS: readonly ["low", "medium", "high", "critical"];
export interface HealthResponse {
    status: string;
    timestamp: string;
    uptime: number;
}
export interface ABACRequest {
    tenant: string;
    subject_id: string;
    subject_roles: string[];
    query: string;
    test_id?: string;
}
export interface ABACResponse {
    results: ABACResult[];
    metadata: {
        query_id: string;
        tenant: string;
        timestamp: string;
        policy_applied: string;
    };
}
export interface ABACResult {
    id: string;
    tenant: string;
    labels: string[];
    data: Record<string, any>;
    access_level: 'read' | 'write' | 'admin';
}
export interface ABACPolicy {
    id: string;
    name: string;
    description: string;
    rules: ABACRule[];
}
export interface ABACRule {
    id: string;
    condition: string;
    effect: 'allow' | 'deny';
    priority: number;
}
export interface TenantContext {
    tenant_id: string;
    allowed_roles: string[];
    data_access_level: 'isolated' | 'shared' | 'public';
}
export interface SubjectContext {
    subject_id: string;
    roles: string[];
    attributes: Record<string, any>;
    tenant: string;
}
//# sourceMappingURL=types.d.ts.map