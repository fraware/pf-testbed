import { Plan, AccessReceipt, ToolTrace } from "../gateway/src/types";
import { LeanTheoremMapping } from "../gateway/src/observability";
export interface SafetyCaseBundle {
    id: string;
    session_id: string;
    tenant: string;
    journey: string;
    timestamp: string;
    expires_at: string;
    capability_ids: string[];
    access_receipts: AccessReceipt[];
    plan_hash: string;
    kernel_decision_log: KernelDecisionLog[];
    egress_certificate: EgressCertificate;
    attestation_quote: AttestationQuote;
    metadata: SafetyCaseMetadata;
    verification_status: "pending" | "verified" | "failed";
    verification_timestamp?: string;
    verification_errors?: string[];
}
export interface KernelDecisionLog {
    id: string;
    timestamp: string;
    decision_type: "capability_check" | "policy_enforcement" | "risk_assessment" | "access_grant";
    decision: "allow" | "deny" | "escalate";
    reason: string;
    context: Record<string, any>;
    evidence: string[];
}
export interface EgressCertificate {
    id: string;
    tenant: string;
    session_id: string;
    timestamp: string;
    expires_at: string;
    permissions: string[];
    restrictions: string[];
    signature: string;
    issuer: string;
}
export interface AttestationQuote {
    id: string;
    session_id: string;
    timestamp: string;
    platform: string;
    measurements: Record<string, string>;
    signature: string;
    public_key: string;
}
export interface SafetyCaseMetadata {
    version: string;
    created_by: string;
    risk_level: "low" | "medium" | "high" | "critical";
    compliance_frameworks: string[];
    tags: string[];
    notes?: string;
}
export declare class SafetyCaseManager {
    private bundles;
    private retentionDays;
    createBundle(session_id: string, tenant: string, journey: string, plan: Plan, receipts: AccessReceipt[], traces: ToolTrace[], theorems: LeanTheoremMapping[]): SafetyCaseBundle;
    getBundle(bundle_id: string): SafetyCaseBundle | null;
    getBundlesBySession(session_id: string): SafetyCaseBundle[];
    getBundlesByTenant(tenant: string): SafetyCaseBundle[];
    verifyBundle(bundle_id: string): boolean;
    exportBundle(bundle_id: string): Promise<Buffer>;
    cleanupExpiredBundles(): number;
    getBundleStats(): {
        total_bundles: number;
        verified_bundles: number;
        failed_bundles: number;
        pending_bundles: number;
        expired_bundles: number;
    };
    private generateBundleId;
    private extractCapabilityIds;
    private generatePlanHash;
    private generateKernelDecisionLog;
    private generateEgressCertificate;
    private generateAttestationQuote;
    private validateReceipt;
}
export declare const safetyCaseManager: SafetyCaseManager;
//# sourceMappingURL=safety_case.d.ts.map