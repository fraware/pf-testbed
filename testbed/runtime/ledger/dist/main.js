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
const safety_case_1 = require("./safety_case");
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
prom_client_1.register.setDefaultLabels({ app: "pf-testbed-ledger" });
// Initialize Express app
const app = (0, express_1.default)();
const port = process.env.LEDGER_PORT || 3002;
// Initialize safety case manager
const safetyCaseManager = new safety_case_1.SafetyCaseManager();
// Middleware
app.use((0, helmet_1.default)());
app.use((0, cors_1.default)());
app.use((0, compression_1.default)());
app.use(express_1.default.json());
// Health check endpoint
app.get("/health", (req, res) => {
    res.json({
        status: "healthy",
        timestamp: new Date().toISOString(),
        service: "pf-testbed-ledger",
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
// Safety case endpoints
app.post("/api/safety-case", (req, res) => {
    try {
        const { session_id, tenant, journey, plan, receipts, traces, theorems } = req.body;
        if (!session_id || !tenant || !journey || !plan) {
            return res.status(400).json({
                error: "Missing required fields: session_id, tenant, journey, plan",
            });
        }
        const bundle = safetyCaseManager.createBundle(session_id, tenant, journey, plan, receipts || [], traces || [], theorems || []);
        logger.info("Safety case bundle created", {
            bundle_id: bundle.id,
            session_id,
            tenant,
        });
        res.status(201).json(bundle);
    }
    catch (error) {
        logger.error("Error creating safety case bundle", { error });
        res.status(500).json({ error: "Internal server error" });
    }
});
app.get("/api/safety-case/:id", (req, res) => {
    try {
        const { id } = req.params;
        const bundle = safetyCaseManager.getBundle(id);
        if (!bundle) {
            return res.status(404).json({ error: "Safety case bundle not found" });
        }
        res.json(bundle);
    }
    catch (error) {
        logger.error("Error retrieving safety case bundle", { error });
        res.status(500).json({ error: "Internal server error" });
    }
});
app.get("/api/safety-case/tenant/:tenant", (req, res) => {
    try {
        const { tenant } = req.params;
        const bundles = safetyCaseManager.getBundlesByTenant(tenant);
        res.json(bundles);
    }
    catch (error) {
        logger.error("Error retrieving safety case bundles by tenant", { error });
        res.status(500).json({ error: "Internal server error" });
    }
});
// Error handling middleware
app.use((err, req, res, next) => {
    logger.error("Unhandled error", { error: err });
    res.status(500).json({ error: "Internal server error" });
});
// Start server
app.listen(port, () => {
    logger.info(`PF Testbed Ledger service started on port ${port}`);
    logger.info(`Health check: http://localhost:${port}/health`);
    logger.info(`Metrics: http://localhost:${port}/metrics`);
});
//# sourceMappingURL=main.js.map