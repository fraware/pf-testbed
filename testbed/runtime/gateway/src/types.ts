// Canonical adapter interface for Provability Fabric Testbed
// This defines the standard interface that all agent runners must implement

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

  // Core interface methods
  plan(json: any): Promise<Plan>;
  verifyPlan(plan: Plan): Promise<VerificationResult>;
  executePlan(plan: Plan): Promise<Plan>;

  // Tool execution
  executeTool(call: ToolCall): Promise<ToolResult>;

  // Trace export
  exportTrace(plan_id: string): Promise<any>;

  // Configuration
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
  traces: ToolTrace[];
  receipts: AccessReceipt[];
  timestamp: string;
}

// Error types
export class PlanValidationError extends Error {
  constructor(
    message: string,
    public errors: string[],
  ) {
    super(message);
    this.name = "PlanValidationError";
  }
}

export class CapabilityError extends Error {
  constructor(
    message: string,
    public capability: string,
  ) {
    super(message);
    this.name = "CapabilityError";
  }
}

export class ReceiptError extends Error {
  constructor(
    message: string,
    public receipt_id: string,
  ) {
    super(message);
    this.name = "ReceiptError";
  }
}

export class ToolExecutionError extends Error {
  constructor(
    message: string,
    public tool: string,
    public parameters: any,
  ) {
    super(message);
    this.name = "ToolExecutionError";
  }
}

// Constants
export const SUPPORTED_JOURNEYS = [
  "support_triage",
  "expense_approval",
  "sales_outreach",
  "hr_onboarding",
  "dev_triage",
] as const;

export const SUPPORTED_TOOLS = [
  "slack",
  "email",
  "calendar",
  "notion",
  "stripe",
  "github",
  "search",
  "fetch",
] as const;

export const CAPABILITY_SCOPES = ["read", "write", "delete", "admin"] as const;

export const RISK_LEVELS = ["low", "medium", "high", "critical"] as const;
