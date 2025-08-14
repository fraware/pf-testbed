"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const server_1 = require("./server");
const startServer = () => {
    try {
        server_1.app.listen(server_1.port, () => {
            console.log(`🚀 ABAC Gateway server started on port ${server_1.port}`);
            console.log(`🔍 Health check at http://localhost:${server_1.port}/health`);
            console.log(`🔐 ABAC Query endpoint at http://localhost:${server_1.port}/api/v1/query`);
            console.log(`📊 Server info at http://localhost:${server_1.port}/`);
        });
    }
    catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
};
// Handle graceful shutdown
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully');
    process.exit(0);
});
process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down gracefully');
    process.exit(0);
});
startServer();
//# sourceMappingURL=main.js.map