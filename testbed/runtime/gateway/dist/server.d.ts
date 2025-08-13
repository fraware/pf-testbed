import express from "express";
import { UnifiedGateway } from "./unified-gateway";
import { GatewayConfig } from "./types";
export declare class GatewayServer {
  private app;
  private gateway;
  private metrics;
  private observability;
  private config;
  constructor(config: GatewayConfig);
  private setupMiddleware;
  private setupRoutes;
  /**
   * Start the server
   */
  start(): void;
  /**
   * Get the Express app instance
   */
  getApp(): express.Application;
  /**
   * Get the gateway instance
   */
  getGateway(): UnifiedGateway;
}
//# sourceMappingURL=server.d.ts.map
