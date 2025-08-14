"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const helmet_1 = __importDefault(require("helmet"));
const compression_1 = __importDefault(require("compression"));
const winston_1 = require("winston");
const prom_client_1 = require("prom-client");
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const validation_1 = require("./middleware/validation");
// Initialize logger
const logger = (0, winston_1.createLogger)({
    format: winston_1.format.combine(winston_1.format.timestamp(), winston_1.format.errors({ stack: true }), winston_1.format.json()),
    transports: [
        new winston_1.transports.Console({
            format: winston_1.format.combine(winston_1.format.colorize(), winston_1.format.simple()),
        }),
    ],
});
// Initialize Prometheus metrics
(0, prom_client_1.collectDefaultMetrics)();
prom_client_1.register.setDefaultLabels({ app: "pf-testbed-ingress" });
// Initialize Express app
const app = (0, express_1.default)();
const port = process.env.INGRESS_PORT || 3001;
// Rate limiting
const limiter = (0, express_rate_limit_1.default)({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: "Too many requests from this IP, please try again later.",
});
// Initialize validation middleware
const validationMiddleware = new validation_1.ValidationMiddleware(process.env.PF_SIGNATURE_SECRET || "default-secret-key-change-in-production");
// Middleware
app.use((0, helmet_1.default)());
app.use((0, cors_1.default)());
app.use((0, compression_1.default)());
app.use(express_1.default.json());
app.use(limiter);
// Apply validation middleware to all routes
app.use(validationMiddleware.validateRequest);
// Health check endpoint
app.get("/health", (req, res) => {
    res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        service: "pf-testbed-ingress",
    });
});
// Metrics endpoint
app.get("/metrics", async (req, res) => {
    try {
        res.set("Content-Type", prom_client_1.register.contentType);
        res.end(await prom_client_1.register.metrics());
    }
    catch (err) {
        res.status(500).end(err);
    }
});
// Test endpoint for validation
app.post("/api/test", (req, res) => {
    res.json({
        message: "Request validated successfully",
        timestamp: new Date().toISOString(),
        headers: req.headers,
    });
});
// Proxy endpoint to gateway
app.all("/api/*", (req, res) => {
    // This would proxy to the gateway service
    // For now, just return a placeholder response
    res.json({
        message: "Request would be proxied to gateway",
        method: req.method,
        path: req.path,
        timestamp: new Date().toISOString(),
    });
});
// Error handling middleware
app.use((err, req, res, next) => {
    logger.error("Unhandled error", { error: err });
    res.status(500).json({ error: "Internal server error" });
});
// Start server
app.listen(port, () => {
    logger.info(`PF Testbed Ingress service started on port ${port}`);
    logger.info(`Health check: http://localhost:${port}/health`);
    logger.info(`Metrics: http://localhost:${port}/metrics`);
});
//# sourceMappingURL=main.js.map