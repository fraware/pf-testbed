import { app, port } from './server';

const startServer = () => {
  try {
    app.listen(port, () => {
      console.log(`🚀 ABAC Gateway server started on port ${port}`);
      console.log(`🔍 Health check at http://localhost:${port}/health`);
      console.log(`🔐 ABAC Query endpoint at http://localhost:${port}/api/v1/query`);
      console.log(`📊 Server info at http://localhost:${port}/`);
    });
  } catch (error) {
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
