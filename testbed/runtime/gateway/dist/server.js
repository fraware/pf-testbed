"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.port = exports.app = void 0;
const express_1 = __importDefault(require("express"));
const abac_engine_1 = require("./abac-engine");
const app = (0, express_1.default)();
exports.app = app;
const port = process.env.GATEWAY_PORT || 3000;
exports.port = port;
// Initialize ABAC engine
const abacEngine = new abac_engine_1.ABACEngine();
// Middleware
app.use(express_1.default.json());
app.use(express_1.default.urlencoded({ extended: true }));
// Health check endpoint
app.get('/health', (req, res) => {
    const healthResponse = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    };
    res.json(healthResponse);
});
// ABAC Query endpoint
app.post('/api/v1/query', async (req, res) => {
    try {
        const request = req.body;
        // Validate required fields
        if (!request.tenant || !request.subject_id || !request.subject_roles || !request.query) {
            return res.status(400).json({
                error: 'Missing required fields',
                required: ['tenant', 'subject_id', 'subject_roles', 'query']
            });
        }
        // Evaluate access using ABAC engine
        const response = await abacEngine.evaluateAccess(request);
        res.status(200).json(response);
    }
    catch (error) {
        console.error('ABAC query error:', error);
        res.status(403).json({
            error: 'Access denied',
            message: error instanceof Error ? error.message : 'Unknown error',
            timestamp: new Date().toISOString()
        });
    }
});
// Root endpoint
app.get('/', (req, res) => {
    res.json({
        service: 'pf-testbed-gateway',
        version: '1.0.0',
        endpoints: {
            health: '/health',
            query: '/api/v1/query'
        },
        timestamp: new Date().toISOString()
    });
});
// 404 handler
app.use('*', (req, res) => {
    res.status(404).json({
        error: 'Endpoint not found',
        path: req.originalUrl,
        timestamp: new Date().toISOString()
    });
});
// Error handler
app.use((error, req, res, next) => {
    console.error('Unhandled error:', error);
    res.status(500).json({
        error: 'Internal server error',
        message: 'An unexpected error occurred',
        timestamp: new Date().toISOString()
    });
});
//# sourceMappingURL=server.js.map