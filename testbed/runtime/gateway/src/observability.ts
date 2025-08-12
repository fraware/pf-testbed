import { Plan, PlanStep, ToolTrace, AccessReceipt } from './types';

// Enhanced trace linking for Lean theorem integration
export interface LeanTheoremMapping {
  theorem_id: string;
  theorem_name: string;
  spec_file: string;
  spec_line: number;
  confidence: number;
  verification_status: 'verified' | 'pending' | 'failed';
  last_verified: string;
}

export interface TraceContext {
  trace_id: string;
  plan_id: string;
  tenant: string;
  journey: string;
  user_id?: string;
  session_id: string;
  request_id: string;
  timestamp: string;
  lean_theorems: LeanTheoremMapping[];
  spec_lines: string[];
  metadata: Record<string, any>;
}

export interface ObservabilityMetrics {
  latency_p95: number;
  latency_p99: number;
  throughput: number;
  error_rate: number;
  success_rate: number;
  active_traces: number;
  theorem_verification_rate: number;
}

export interface SavedView {
  id: string;
  name: string;
  tenant: string;
  journey: string;
  filters: ViewFilters;
  layout: ViewLayout;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ViewFilters {
  time_range: {
    start: string;
    end: string;
  };
  tenants: string[];
  journeys: string[];
  risk_levels: string[];
  status: string[];
  lean_theorems: string[];
}

export interface ViewLayout {
  panels: PanelConfig[];
  refresh_interval: number;
  auto_refresh: boolean;
}

export interface PanelConfig {
  id: string;
  type: 'metrics' | 'traces' | 'theorems' | 'alerts';
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  config: Record<string, any>;
}

// Core observability service
export class ObservabilityService {
  private traceContexts: Map<string, TraceContext> = new Map();
  private savedViews: Map<string, SavedView> = new Map();
  private metrics: ObservabilityMetrics = {
    latency_p95: 0,
    latency_p99: 0,
    throughput: 0,
    error_rate: 0,
    success_rate: 0,
    active_traces: 0,
    theorem_verification_rate: 0
  };

  // Create new trace context with Lean theorem linking
  createTraceContext(
    plan: Plan,
    request_id: string,
    session_id: string,
    user_id?: string
  ): TraceContext {
    const trace_id = this.generateTraceId();
    
    const context: TraceContext = {
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
        risk_level: plan.metadata.risk_level
      }
    };

    this.traceContexts.set(trace_id, context);
    this.updateMetrics();
    
    return context;
  }

  // Link trace to Lean theorem and spec lines
  linkLeanTheorem(
    trace_id: string,
    theorem: LeanTheoremMapping,
    spec_lines: string[]
  ): void {
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
  private updateTheoremVerificationStatus(trace_id: string, theorem_id: string): void {
    const context = this.traceContexts.get(trace_id);
    if (!context) return;

    const theorem = context.lean_theorems.find(t => t.theorem_id === theorem_id);
    if (theorem) {
      theorem.verification_status = 'verified';
      theorem.last_verified = new Date().toISOString();
    }
  }

  // Get complete trace context for UI calls drawer
  getTraceContext(trace_id: string): TraceContext | null {
    return this.traceContexts.get(trace_id) || null;
  }

  // Get trace chain: Trace → Plan → Theorem → Cert
  getTraceChain(trace_id: string): {
    trace: TraceContext;
    plan: Plan;
    theorems: LeanTheoremMapping[];
    certificates: any[];
  } | null {
    const context = this.traceContexts.get(trace_id);
    if (!context) return null;

    // In a real implementation, you would fetch these from your data stores
    return {
      trace: context,
      plan: {} as Plan, // Would be fetched from plan store
      theorems: context.lean_theorems,
      certificates: [] // Would be fetched from cert store
    };
  }

  // Save view for specific journey and tenant
  saveView(view: Omit<SavedView, 'id' | 'created_at' | 'updated_at'>): SavedView {
    const id = this.generateViewId();
    const now = new Date().toISOString();
    
    const savedView: SavedView = {
      ...view,
      id,
      created_at: now,
      updated_at: now
    };

    this.savedViews.set(id, savedView);
    return savedView;
  }

  // Get saved views for tenant and journey
  getSavedViews(tenant: string, journey: string): SavedView[] {
    return Array.from(this.savedViews.values()).filter(
      view => view.tenant === tenant && view.journey === journey
    );
  }

  // Update metrics
  private updateMetrics(): void {
    this.metrics.active_traces = this.traceContexts.size;
    
    // Calculate other metrics based on trace data
    const traces = Array.from(this.traceContexts.values());
    const verifiedTheorems = traces.reduce(
      (count, trace) => count + trace.lean_theorems.filter(t => t.verification_status === 'verified').length,
      0
    );
    const totalTheorems = traces.reduce(
      (count, trace) => count + trace.lean_theorems.length,
      0
    );
    
    this.metrics.theorem_verification_rate = totalTheorems > 0 ? verifiedTheorems / totalTheorems : 0;
  }

  // Get current metrics
  getMetrics(): ObservabilityMetrics {
    return { ...this.metrics };
  }

  // Clean up old traces (retention policy)
  cleanupOldTraces(retentionDays: number = 90): void {
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
  private generateTraceId(): string {
    return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateViewId(): string {
    return `view_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Export singleton instance
export const observabilityService = new ObservabilityService();
