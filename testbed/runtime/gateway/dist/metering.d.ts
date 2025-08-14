export interface UsageMetrics {
    tenant_id: string;
    session_id: string;
    timestamp: string;
    cpu_ms: number;
    network_bytes: number;
    api_calls: number;
    tool_executions: number;
    data_retrievals: number;
    egress_scans: number;
    policy_checks: number;
    violations: number;
    risk_score: number;
}
export interface BillingTier {
    name: string;
    base_price_usd: number;
    cpu_price_per_ms: number;
    network_price_per_mb: number;
    api_call_price: number;
    tool_execution_price: number;
    data_retrieval_price: number;
    egress_scan_price: number;
    policy_check_price: number;
    violation_price: number;
    risk_multiplier: number;
    monthly_quota: {
        cpu_ms: number;
        network_mb: number;
        api_calls: number;
        tool_executions: number;
        data_retrievals: number;
    };
}
export interface CostBreakdown {
    base_cost: number;
    cpu_cost: number;
    network_cost: number;
    api_cost: number;
    tool_cost: number;
    data_cost: number;
    egress_cost: number;
    policy_cost: number;
    violation_cost: number;
    risk_adjustment: number;
    total_cost: number;
}
export interface InvoiceData {
    invoice_id: string;
    tenant_id: string;
    period_start: string;
    period_end: string;
    usage_metrics: UsageMetrics[];
    cost_breakdown: CostBreakdown;
    stripe_invoice_id?: string;
    status: "draft" | "sent" | "paid" | "overdue";
    created_at: string;
    due_date: string;
}
export interface StripeConfig {
    secret_key: string;
    webhook_secret: string;
    price_ids: {
        [tier: string]: string;
    };
    enabled: boolean;
}
export declare class MeteringService {
    private billingTiers;
    private stripeConfig;
    private usageStore;
    private invoiceStore;
    constructor(stripeConfig: StripeConfig);
    /**
     * Record usage metrics for a session
     */
    recordUsage(metrics: UsageMetrics): void;
    /**
     * Get current billing period (YYYY-MM format)
     */
    private getCurrentPeriod;
    /**
     * Calculate cost for usage metrics
     */
    calculateCost(tenantId: string, period: string): CostBreakdown;
    /**
     * Aggregate usage metrics for a period
     */
    private aggregateMetrics;
    /**
     * Get empty cost breakdown
     */
    private getEmptyCostBreakdown;
    /**
     * Generate invoice for a tenant and period
     */
    generateInvoice(tenantId: string, period: string): Promise<InvoiceData>;
    /**
     * Generate unique invoice ID
     */
    private generateInvoiceId;
    /**
     * Create Stripe invoice (placeholder for real integration)
     */
    private createStripeInvoice;
    /**
     * Get usage metrics for a tenant and period
     */
    getUsageMetrics(tenantId: string, period: string): UsageMetrics[];
    /**
     * Get invoices for a tenant
     */
    getInvoices(tenantId: string): InvoiceData[];
    /**
     * Export usage data to Prometheus metrics format
     */
    exportPrometheusMetrics(): string;
    /**
     * Get billing tier information
     */
    getBillingTier(tierName: string): BillingTier | undefined;
    /**
     * List all billing tiers
     */
    listBillingTiers(): BillingTier[];
    /**
     * Update billing tier for a tenant (placeholder for real implementation)
     */
    updateTenantBillingTier(tenantId: string, tierName: string): boolean;
}
//# sourceMappingURL=metering.d.ts.map