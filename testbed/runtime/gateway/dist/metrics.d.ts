export declare class TestbedMetrics {
    private sloViolationsTotal;
    private requestDurationSeconds;
    private theoremVerificationRate;
    private activeTracesTotal;
    private tracesCreatedTotal;
    private honeytokenAlertsTotal;
    private accessReceiptsTotal;
    private certificateStatusTotal;
    private planExecutionsTotal;
    private planExecutionDurationSeconds;
    private errorsTotal;
    private requestsTotal;
    constructor();
    recordSloViolation(tenant: string, journey: string, sloType: string, severity: string): void;
    startRequestTimer(tenant: string, journey: string, endpoint: string, method: string): () => void;
    updateTheoremVerificationRate(tenant: string, journey: string, rate: number): void;
    incrementActiveTraces(tenant: string, journey: string, status: string): void;
    decrementActiveTraces(tenant: string, journey: string, status: string): void;
    recordTraceCreated(tenant: string, journey: string): void;
    recordHoneytokenAlert(tenant: string, type: string, severity: string): void;
    recordAccessReceipt(tenant: string, journey: string, status: string): void;
    updateCertificateStatus(tenant: string, status: string, type: string, count: number): void;
    recordPlanExecution(tenant: string, journey: string, status: string): void;
    startPlanExecutionTimer(tenant: string, journey: string): () => void;
    recordError(tenant: string, journey: string, errorType: string, severity: string): void;
    recordRequest(tenant: string, journey: string, method: string, status: string): void;
    getMetrics(): Promise<string>;
    reset(): void;
}
export declare const testbedMetrics: TestbedMetrics;
//# sourceMappingURL=metrics.d.ts.map