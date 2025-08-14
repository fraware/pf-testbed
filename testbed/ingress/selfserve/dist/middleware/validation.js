"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.requestIdMiddleware = exports.TenantRateLimiter = exports.ValidationMiddleware = exports.VALIDATION_ERROR_CODES = exports.RequestValidationSchema = exports.AccessReceiptSchema = exports.PfSignatureSchema = void 0;
const zod_1 = require("zod");
const crypto_1 = require("crypto");
// Validation schemas
exports.PfSignatureSchema = zod_1.z.object({
    tenant: zod_1.z.string().min(1),
    user_id: zod_1.z.string().min(1),
    capabilities: zod_1.z.array(zod_1.z.string()).min(1),
    nonce: zod_1.z.string().min(16),
    expires_at: zod_1.z.string().datetime(),
    signature: zod_1.z.string().min(1),
});
exports.AccessReceiptSchema = zod_1.z.object({
    tenant: zod_1.z.string().min(1),
    subject: zod_1.z.string().min(1),
    shard: zod_1.z.string().min(1),
    query_hash: zod_1.z.string().min(1),
    result_hash: zod_1.z.string().min(1),
    nonce: zod_1.z.string().min(16),
    expires_at: zod_1.z.string().datetime(),
    signature: zod_1.z.string().min(1),
});
exports.RequestValidationSchema = zod_1.z.object({
    pf_signature: exports.PfSignatureSchema,
    access_receipts: zod_1.z.array(exports.AccessReceiptSchema).optional(),
});
exports.VALIDATION_ERROR_CODES = {
    PF_SIG_INVALID: "PF_SIG_INVALID",
    PF_SIG_EXPIRED: "PF_SIG_EXPIRED",
    PF_SIG_MISSING: "PF_SIG_MISSING",
    ACCESS_RECEIPT_INVALID: "ACCESS_RECEIPT_INVALID",
    ACCESS_RECEIPT_EXPIRED: "ACCESS_RECEIPT_EXPIRED",
    ACCESS_RECEIPT_MISSING: "ACCESS_RECEIPT_MISSING",
    RATE_LIMIT_EXCEEDED: "RATE_LIMIT_EXCEEDED",
    TENANT_NOT_FOUND: "TENANT_NOT_FOUND",
};
// Validation middleware class
class ValidationMiddleware {
    constructor(secretKey) {
        this.algorithm = "sha256";
        // Main validation middleware
        this.validateRequest = async (req, res, next) => {
            try {
                // Ensure request ID is set
                if (!res.locals["requestId"]) {
                    res.locals["requestId"] =
                        req.headers["x-request-id"] || "unknown";
                }
                // Extract and validate PF signature
                const pfSignature = req.headers["x-pf-signature"];
                if (!pfSignature) {
                    this.sendError(res, 403, exports.VALIDATION_ERROR_CODES.PF_SIG_MISSING, "PF signature is required");
                    return;
                }
                // Parse and validate PF signature
                const parsedSignature = this.parseAndValidatePfSignature(pfSignature);
                if (!parsedSignature.success) {
                    this.sendError(res, 403, exports.VALIDATION_ERROR_CODES.PF_SIG_INVALID, parsedSignature.error || "Unknown error");
                    return;
                }
                // Check if signature is expired
                if (this.isSignatureExpired(parsedSignature.data.expires_at)) {
                    this.sendError(res, 403, exports.VALIDATION_ERROR_CODES.PF_SIG_EXPIRED, "PF signature has expired");
                    return;
                }
                // Verify signature authenticity
                if (!this.verifySignature(parsedSignature.data)) {
                    this.sendError(res, 403, exports.VALIDATION_ERROR_CODES.PF_SIG_INVALID, "Invalid signature");
                    return;
                }
                // Validate access receipts if present
                const accessReceipts = req.headers["x-access-receipts"];
                if (accessReceipts) {
                    const receiptsValidation = this.validateAccessReceipts(accessReceipts, parsedSignature.data.tenant);
                    if (!receiptsValidation.success) {
                        this.sendError(res, 403, receiptsValidation.errorCode ||
                            exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID, receiptsValidation.error || "Unknown error");
                        return;
                    }
                }
                // Add validated data to request
                req.pfSignature = parsedSignature.data;
                req.tenant = parsedSignature.data.tenant;
                req.userId = parsedSignature.data.user_id;
                req.capabilities = parsedSignature.data.capabilities;
                next();
            }
            catch (error) {
                console.error("Validation error:", error);
                this.sendError(res, 500, "INTERNAL_ERROR", "Internal validation error");
            }
        };
        this.secretKey = secretKey;
    }
    // Parse and validate PF signature
    parseAndValidatePfSignature(signature) {
        try {
            const decoded = Buffer.from(signature, "base64").toString("utf-8");
            const parsed = JSON.parse(decoded);
            const validation = exports.PfSignatureSchema.safeParse(parsed);
            if (!validation.success) {
                return { success: false, error: "Invalid signature schema" };
            }
            return { success: true, data: validation.data };
        }
        catch (error) {
            console.error("Signature parsing error:", error);
            return { success: false, error: "Failed to parse signature" };
        }
    }
    // Validate access receipts
    validateAccessReceipts(receiptsHeader, expectedTenant) {
        try {
            const receipts = JSON.parse(receiptsHeader);
            if (!Array.isArray(receipts)) {
                return {
                    success: false,
                    errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID,
                    error: "Invalid receipts format",
                };
            }
            for (const receipt of receipts) {
                // Validate schema
                const validation = exports.AccessReceiptSchema.safeParse(receipt);
                if (!validation.success) {
                    return {
                        success: false,
                        errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID,
                        error: "Invalid receipt schema",
                    };
                }
                // Check tenant consistency
                if (receipt.tenant !== expectedTenant) {
                    return {
                        success: false,
                        errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID,
                        error: "Receipt tenant mismatch",
                    };
                }
                // Check expiration
                if (this.isSignatureExpired(receipt.expires_at)) {
                    return {
                        success: false,
                        errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_EXPIRED,
                        error: "Receipt has expired",
                    };
                }
                // Verify receipt signature
                if (!this.verifyReceiptSignature(receipt)) {
                    return {
                        success: false,
                        errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID,
                        error: "Invalid receipt signature",
                    };
                }
            }
            return { success: true };
        }
        catch (error) {
            return {
                success: false,
                errorCode: exports.VALIDATION_ERROR_CODES.ACCESS_RECEIPT_INVALID,
                error: "Failed to parse receipts",
            };
        }
    }
    // Check if signature is expired
    isSignatureExpired(expiresAt) {
        const expiryDate = new Date(expiresAt);
        const now = new Date();
        return now > expiryDate;
    }
    // Verify PF signature
    verifySignature(signatureData) {
        try {
            const { signature, ...dataToSign } = signatureData;
            const dataString = JSON.stringify(dataToSign, Object.keys(dataToSign).sort());
            const expectedSignature = (0, crypto_1.createHmac)(this.algorithm, this.secretKey)
                .update(dataString)
                .digest("hex");
            return signature === expectedSignature;
        }
        catch (error) {
            console.error("Signature verification error:", error);
            return false;
        }
    }
    // Verify receipt signature
    verifyReceiptSignature(receipt) {
        try {
            const { signature, ...dataToSign } = receipt;
            const dataString = JSON.stringify(dataToSign, Object.keys(dataToSign).sort());
            const expectedSignature = (0, crypto_1.createHmac)(this.algorithm, this.secretKey)
                .update(dataString)
                .digest("hex");
            return signature === expectedSignature;
        }
        catch (error) {
            return false;
        }
    }
    // Send structured error response
    sendError(res, statusCode, code, message, details) {
        const errorResponse = {
            code,
            message,
            details,
        };
        res.status(statusCode).json({
            error: errorResponse,
            timestamp: new Date().toISOString(),
            request_id: res.locals["requestId"] || "unknown",
        });
    }
    // Generate PF signature for testing
    generateSignature(data) {
        const expiresAt = new Date(Date.now() + data.expires_in * 1000).toISOString();
        const nonce = (0, crypto_1.randomBytes)(16).toString("hex");
        // Create signature data without expires_in (since it's not part of the final structure)
        const signatureData = {
            tenant: data.tenant,
            user_id: data.user_id,
            capabilities: data.capabilities,
            nonce,
            expires_at: expiresAt,
        };
        const dataString = JSON.stringify(signatureData, Object.keys(signatureData).sort());
        const signature = (0, crypto_1.createHmac)(this.algorithm, this.secretKey)
            .update(dataString)
            .digest("hex");
        const fullData = { ...signatureData, signature };
        const base64Data = Buffer.from(JSON.stringify(fullData)).toString("base64");
        return base64Data;
    }
    // Generate access receipt for testing
    generateAccessReceipt(data) {
        const expiresAt = new Date(Date.now() + data.expires_in * 1000).toISOString();
        const nonce = (0, crypto_1.randomBytes)(16).toString("hex");
        const receiptData = {
            ...data,
            nonce,
            expires_at: expiresAt,
        };
        const dataString = JSON.stringify(receiptData, Object.keys(receiptData).sort());
        const signature = (0, crypto_1.createHmac)(this.algorithm, this.secretKey)
            .update(dataString)
            .digest("hex");
        return { ...receiptData, signature };
    }
}
exports.ValidationMiddleware = ValidationMiddleware;
// Rate limiting middleware per tenant
class TenantRateLimiter {
    constructor(windowMs = 15 * 60 * 1000, maxRequests = 100) {
        this.limits = new Map();
        this.limitByTenant = (req, res, next) => {
            const tenant = req.tenant;
            if (!tenant) {
                next();
                return;
            }
            const now = Date.now();
            const limit = this.limits.get(tenant);
            if (!limit || now > limit.resetTime) {
                // Reset or create new limit
                this.limits.set(tenant, {
                    count: 1,
                    resetTime: now + this.windowMs,
                });
                next();
                return;
            }
            if (limit.count >= this.maxRequests) {
                res.status(429).json({
                    error: {
                        code: exports.VALIDATION_ERROR_CODES.RATE_LIMIT_EXCEEDED,
                        message: "Rate limit exceeded for tenant",
                        details: {
                            tenant,
                            limit: this.maxRequests,
                            window_ms: this.windowMs,
                            reset_time: new Date(limit.resetTime).toISOString(),
                        },
                    },
                    timestamp: new Date().toISOString(),
                    request_id: res.locals["requestId"] || "unknown",
                });
                return;
            }
            limit.count++;
            next();
        };
        this.windowMs = windowMs;
        this.maxRequests = maxRequests;
    }
    // Clean up expired limits
    cleanup() {
        const now = Date.now();
        for (const [tenant, limit] of this.limits.entries()) {
            if (now > limit.resetTime) {
                this.limits.delete(tenant);
            }
        }
    }
}
exports.TenantRateLimiter = TenantRateLimiter;
// Request ID middleware
const requestIdMiddleware = (req, res, next) => {
    const requestId = req.headers["x-request-id"] || (0, crypto_1.randomBytes)(8).toString("hex");
    res.locals["requestId"] = requestId;
    req.headers["x-request-id"] = requestId;
    next();
};
exports.requestIdMiddleware = requestIdMiddleware;
//# sourceMappingURL=validation.js.map