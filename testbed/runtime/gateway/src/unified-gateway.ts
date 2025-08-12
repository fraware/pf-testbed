import { 
  AgentRunner, 
  Plan, 
  PlanStep, 
  ToolCall, 
  ToolResult, 
  VerificationResult, 
  AgentConfig, 
  AgentStatus,
  ExecutionContext,
  ExecutionResult,
  GatewayConfig
} from './types';
import { BaseAgentRunner } from './base-runner';
import { MetricsCollector } from './metrics';
import { ObservabilityCollector } from './observability';

// Unified trace export schema
export interface NormalizedTrace {
  plan_id: string;
  agent_stack: string;
  journey: string;
  tenant: string;
  steps: NormalizedStep[];
  receipts: string[];
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
  tool?: string;
  capability?: string;
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
export class UnifiedGateway {
  private agents: Map<string, AgentRunner> = new Map();
  private metrics: MetricsCollector;
  private observability: ObservabilityCollector;
  private config: GatewayConfig;
  private enforceMode: boolean;

  constructor(config: GatewayConfig) {
    this.config = config;
    this.metrics = new MetricsCollector();
    this.observability = new ObservabilityCollector();
    this.enforceMode = process.env.PF_ENFORCE === 'true';
  }

  /**
   * Register an agent runner for a specific stack
   */
  registerAgent(stack: string, agent: AgentRunner): void {
    this.agents.set(stack, agent);
    console.log(`Registered agent for stack: ${stack}`);
  }

  /**
   * Execute a plan using the specified agent stack
   */
  async executePlan(
    stack: string, 
    plan: Plan, 
    context: ExecutionContext
  ): Promise<ExecutionResult> {
    const startTime = Date.now();
    
    if (!this.agents.has(stack)) {
      throw new Error(`Unsupported agent stack: ${stack}`);
    }

    const agent = this.agents.get(stack)!;
    
    try {
      // Record execution start
      this.metrics.recordExecutionStart(stack, plan.journey, plan.tenant);
      this.observability.recordPlanStart(plan.id, stack, context);

      // Verify plan
      const verification = await agent.verifyPlan(plan);
      if (!verification.valid) {
        throw new Error(`Plan validation failed: ${verification.errors.join(', ')}`);
      }

      // Execute plan
      const executedPlan = await agent.executePlan(plan);
      
      // Record execution completion
      const executionTime = Date.now() - startTime;
      this.metrics.recordExecutionComplete(stack, plan.journey, plan.tenant, executionTime);
      this.observability.recordPlanComplete(plan.id, executionTime);

      // Generate normalized trace
      const trace = await this.generateNormalizedTrace(stack, executedPlan, context, executionTime);

      return {
        success: true,
        plan_id: plan.id,
        execution_time: executionTime,
        steps_completed: executedPlan.steps.filter(s => s.status === 'completed').length,
        steps_failed: executedPlan.steps.filter(s => s.status === 'failed').length,
        final_result: executedPlan,
        traces: [trace],
        receipts: verification.receipts.map(r => r.id),
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.metrics.recordExecutionError(stack, plan.journey, plan.tenant, error);
      this.observability.recordPlanError(plan.id, error, executionTime);

      return {
        success: false,
        plan_id: plan.id,
        execution_time: executionTime,
        steps_completed: 0,
        steps_failed: plan.steps.length,
        error: error instanceof Error ? error.message : 'Unknown error',
        traces: [],
        receipts: [],
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Generate normalized trace export for all stacks
   */
  async generateNormalizedTrace(
    stack: string,
    plan: Plan,
    context: ExecutionContext,
    executionTime: number
  ): Promise<NormalizedTrace> {
    const stepDurations: Record<string, number> = {};
    
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
      steps: plan.steps.map(step => ({
        id: step.id,
        type: step.type,
        tool: step.tool,
        capability: step.capability,
        status: step.status,
        duration_ms: step.duration || 0,
        timestamp: step.timestamp,
        result: step.result,
        error: step.error
      })),
      receipts: plan.steps
        .filter(s => s.type === 'retrieval' && s.receipt)
        .map(s => s.receipt!),
      cert_id: certId,
      timings: {
        plan_start: plan.timestamp,
        plan_end: new Date().toISOString(),
        total_duration_ms: executionTime,
        step_durations: stepDurations
      },
      metadata: {
        model: plan.metadata.model,
        confidence: plan.metadata.confidence,
        risk_level: plan.metadata.risk_level,
        capabilities_used: plan.steps
          .filter(s => s.capability)
          .map(s => s.capability!),
        shadow_mode: !this.enforceMode,
        enforce_policies: this.enforceMode
      }
    };
  }

  /**
   * Generate unique capability token ID
   */
  private generateCapabilityTokenId(plan: Plan, context: ExecutionContext): string {
    const components = [
      plan.tenant,
      plan.journey,
      context.session_id,
      plan.id,
      Date.now().toString()
    ];
    return btoa(components.join('|')).replace(/[^a-zA-Z0-9]/g, '');
  }

  /**
   * Get metrics for all agent stacks
   */
  async getStackMetrics(): Promise<Record<string, any>> {
    const metrics: Record<string, any> = {};
    
    for (const [stack, agent] of this.agents) {
      try {
        const status = await agent.getStatus();
        const stackMetrics = this.metrics.getStackMetrics(stack);
        
        metrics[stack] = {
          status,
          metrics: stackMetrics,
          timestamp: new Date().toISOString()
        };
      } catch (error) {
        metrics[stack] = {
          error: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date().toISOString()
        };
      }
    }
    
    return metrics;
  }

  /**
   * Get health status for all stacks
   */
  async getHealthStatus(): Promise<Record<string, boolean>> {
    const health: Record<string, boolean> = {};
    
    for (const [stack, agent] of this.agents) {
      try {
        const status = await agent.getStatus();
        health[stack] = status.healthy;
      } catch (error) {
        health[stack] = false;
      }
    }
    
    return health;
  }

  /**
   * Export all traces for a specific journey across all stacks
   */
  async exportJourneyTraces(journey: string, tenant: string): Promise<NormalizedTrace[]> {
    const traces: NormalizedTrace[] = [];
    
    // This would typically query a database or storage system
    // For now, we'll return an empty array
    // In production, this would aggregate traces from all stacks
    
    return traces;
  }

  /**
   * Get configuration
   */
  getConfig(): GatewayConfig {
    return this.config;
  }

  /**
   * Check if enforce mode is enabled
   */
  isEnforceMode(): boolean {
    return this.enforceMode;
  }
}
