import { Plan } from "./types";
export interface LeanTheoremMapping {
    theorem_id: string;
    theorem_name: string;
    spec_file: string;
    spec_line: number;
    confidence: number;
    verification_status: "verified" | "pending" | "failed";
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
    type: "metrics" | "traces" | "theorems" | "alerts";
    position: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
    config: Record<string, any>;
}
export declare class ObservabilityService {
    private traceContexts;
    private savedViews;
    private metrics;
    createTraceContext(plan: Plan, request_id: string, session_id: string, user_id?: string): TraceContext;
    linkLeanTheorem(trace_id: string, theorem: LeanTheoremMapping, spec_lines: string[]): void;
    private updateTheoremVerificationStatus;
    getTraceContext(trace_id: string): TraceContext | null;
    getTraceChain(trace_id: string): {
        trace: TraceContext;
        plan: Plan;
        theorems: LeanTheoremMapping[];
        certificates: any[];
    } | null;
    saveView(view: Omit<SavedView, "id" | "created_at" | "updated_at">): SavedView;
    getSavedViews(tenant: string, journey: string): SavedView[];
    private updateMetrics;
    getMetrics(): ObservabilityMetrics;
    cleanupOldTraces(retentionDays?: number): void;
    private generateTraceId;
    private generateViewId;
}
export declare const observabilityService: ObservabilityService;
//# sourceMappingURL=observability.d.ts.map