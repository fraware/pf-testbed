import { AgentRunner, Plan, ToolCall, ToolResult, VerificationResult, AgentConfig, AgentStatus } from "./types";
/**
 * Base agent runner implementation that provides common functionality
 * for all agent runners in the testbed
 */
export declare abstract class BaseAgentRunner implements AgentRunner {
    name: string;
    version: string;
    capabilities: string[];
    protected config: AgentConfig;
    protected startTime: number;
    protected activePlans: Set<string>;
    protected executionCount: number;
    protected errorCount: number;
    protected lastHeartbeat: number;
    constructor(name: string, version: string, capabilities: string[]);
    /**
     * Abstract methods that must be implemented by specific agent runners
     */
    abstract plan(json: any): Promise<Plan>;
    abstract executeTool(call: ToolCall): Promise<ToolResult>;
    /**
     * Default plan verification implementation
     */
    verifyPlan(plan: Plan): Promise<VerificationResult>;
    /**
     * Default plan execution implementation
     */
    executePlan(plan: Plan): Promise<Plan>;
    /**
     * Default trace export implementation
     */
    exportTrace(plan_id: string): Promise<any>;
    /**
     * Default configuration method
     */
    configure(config: AgentConfig): Promise<void>;
    /**
     * Default status method
     */
    getStatus(): Promise<AgentStatus>;
    /**
     * Utility method to validate capabilities
     */
    protected validateCapability(required: string, available: string[]): void;
    /**
     * Utility method to generate unique IDs
     */
    protected generateId(): string;
    /**
     * Utility method to check if plan is expired
     */
    protected isPlanExpired(plan: Plan): boolean;
    /**
     * Utility method to log execution metrics
     */
    protected logMetrics(plan: Plan, executionTime: number): void;
}
//# sourceMappingURL=base-runner.d.ts.map