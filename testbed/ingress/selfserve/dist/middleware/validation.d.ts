import { Request, Response, NextFunction } from "express";
import { z } from "zod";
export declare const PfSignatureSchema: z.ZodObject<{
    tenant: z.ZodString;
    user_id: z.ZodString;
    capabilities: z.ZodArray<z.ZodString, "many">;
    nonce: z.ZodString;
    expires_at: z.ZodString;
    signature: z.ZodString;
}, "strip", z.ZodTypeAny, {
    tenant: string;
    user_id: string;
    capabilities: string[];
    nonce: string;
    expires_at: string;
    signature: string;
}, {
    tenant: string;
    user_id: string;
    capabilities: string[];
    nonce: string;
    expires_at: string;
    signature: string;
}>;
export declare const AccessReceiptSchema: z.ZodObject<{
    tenant: z.ZodString;
    subject: z.ZodString;
    shard: z.ZodString;
    query_hash: z.ZodString;
    result_hash: z.ZodString;
    nonce: z.ZodString;
    expires_at: z.ZodString;
    signature: z.ZodString;
}, "strip", z.ZodTypeAny, {
    tenant: string;
    nonce: string;
    expires_at: string;
    signature: string;
    subject: string;
    shard: string;
    query_hash: string;
    result_hash: string;
}, {
    tenant: string;
    nonce: string;
    expires_at: string;
    signature: string;
    subject: string;
    shard: string;
    query_hash: string;
    result_hash: string;
}>;
export declare const RequestValidationSchema: z.ZodObject<{
    pf_signature: z.ZodObject<{
        tenant: z.ZodString;
        user_id: z.ZodString;
        capabilities: z.ZodArray<z.ZodString, "many">;
        nonce: z.ZodString;
        expires_at: z.ZodString;
        signature: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        tenant: string;
        user_id: string;
        capabilities: string[];
        nonce: string;
        expires_at: string;
        signature: string;
    }, {
        tenant: string;
        user_id: string;
        capabilities: string[];
        nonce: string;
        expires_at: string;
        signature: string;
    }>;
    access_receipts: z.ZodOptional<z.ZodArray<z.ZodObject<{
        tenant: z.ZodString;
        subject: z.ZodString;
        shard: z.ZodString;
        query_hash: z.ZodString;
        result_hash: z.ZodString;
        nonce: z.ZodString;
        expires_at: z.ZodString;
        signature: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        tenant: string;
        nonce: string;
        expires_at: string;
        signature: string;
        subject: string;
        shard: string;
        query_hash: string;
        result_hash: string;
    }, {
        tenant: string;
        nonce: string;
        expires_at: string;
        signature: string;
        subject: string;
        shard: string;
        query_hash: string;
        result_hash: string;
    }>, "many">>;
}, "strip", z.ZodTypeAny, {
    pf_signature: {
        tenant: string;
        user_id: string;
        capabilities: string[];
        nonce: string;
        expires_at: string;
        signature: string;
    };
    access_receipts?: {
        tenant: string;
        nonce: string;
        expires_at: string;
        signature: string;
        subject: string;
        shard: string;
        query_hash: string;
        result_hash: string;
    }[] | undefined;
}, {
    pf_signature: {
        tenant: string;
        user_id: string;
        capabilities: string[];
        nonce: string;
        expires_at: string;
        signature: string;
    };
    access_receipts?: {
        tenant: string;
        nonce: string;
        expires_at: string;
        signature: string;
        subject: string;
        shard: string;
        query_hash: string;
        result_hash: string;
    }[] | undefined;
}>;
export interface ValidationError {
    code: string;
    message: string;
    details?: any;
}
export declare const VALIDATION_ERROR_CODES: {
    readonly PF_SIG_INVALID: "PF_SIG_INVALID";
    readonly PF_SIG_EXPIRED: "PF_SIG_EXPIRED";
    readonly PF_SIG_MISSING: "PF_SIG_MISSING";
    readonly ACCESS_RECEIPT_INVALID: "ACCESS_RECEIPT_INVALID";
    readonly ACCESS_RECEIPT_EXPIRED: "ACCESS_RECEIPT_EXPIRED";
    readonly ACCESS_RECEIPT_MISSING: "ACCESS_RECEIPT_MISSING";
    readonly RATE_LIMIT_EXCEEDED: "RATE_LIMIT_EXCEEDED";
    readonly TENANT_NOT_FOUND: "TENANT_NOT_FOUND";
};
export declare class ValidationMiddleware {
    private readonly secretKey;
    private readonly algorithm;
    constructor(secretKey: string);
    validateRequest: (req: Request, res: Response, next: NextFunction) => Promise<void>;
    private parseAndValidatePfSignature;
    private validateAccessReceipts;
    private isSignatureExpired;
    private verifySignature;
    private verifyReceiptSignature;
    private sendError;
    generateSignature(data: {
        tenant: string;
        user_id: string;
        capabilities: string[];
        expires_in: number;
    }): string;
    generateAccessReceipt(data: {
        tenant: string;
        subject: string;
        shard: string;
        query_hash: string;
        result_hash: string;
        expires_in: number;
    }): any;
}
export declare class TenantRateLimiter {
    private limits;
    private readonly windowMs;
    private readonly maxRequests;
    constructor(windowMs?: number, maxRequests?: number);
    limitByTenant: (req: Request, res: Response, next: NextFunction) => void;
    cleanup(): void;
}
export declare const requestIdMiddleware: (req: Request, res: Response, next: NextFunction) => void;
declare global {
    namespace Express {
        interface Request {
            pfSignature?: any;
            tenant?: string;
            userId?: string;
            capabilities?: string[];
        }
    }
}
//# sourceMappingURL=validation.d.ts.map