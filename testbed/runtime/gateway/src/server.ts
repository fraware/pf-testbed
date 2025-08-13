import express from "express";
import cors from "cors";
import { json } from "express";
import { UnifiedGateway } from "./unified-gateway";
import { GatewayConfig } from "./types";
import { MetricsCollector } from "./metrics";
import { ObservabilityCollector } from "./observability";

export class GatewayServer {
  private app: express.Application;
  private gateway: UnifiedGateway;
  private metrics: MetricsCollector;
  private observability: ObservabilityCollector;
  private config: GatewayConfig;

  constructor(config: GatewayConfig) {
    this.config = config;
    this.app = express();
    this.gateway = new UnifiedGateway(config);
    this.metrics = new MetricsCollector();
    this.observability = new ObservabilityCollector();

    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    // CORS
    this.app.use(
      cors({
        origin: this.config.cors_origins,
        credentials: true,
      }),
    );

    // JSON parsing
    this.app.use(json({ limit: "10mb" }));

    // Request logging
    this.app.use((req, res, next) => {
      const startTime = Date.now();
      this.observability.recordRequestStart(req.path, req.method);

      res.on("finish", () => {
        const duration = Date.now() - startTime;
        this.observability.recordRequestComplete(
          req.path,
          req.method,
          res.statusCode,
          duration,
        );
      });

      next();
    });

    // Rate limiting
    this.app.use((req, res, next) => {
      // Simple in-memory rate limiting
      // In production, use Redis or similar
      const clientId = req.ip || "unknown";
      const now = Date.now();
      const windowStart = now - this.config.rate_limit.window_ms;

      // This is a simplified implementation
      // In production, implement proper rate limiting
      next();
    });
  }

  private setupRoutes(): void {
    // Health check
    this.app.get("/health", async (req, res) => {
      try {
        const health = await this.gateway.getHealthStatus();
        const allHealthy = Object.values(health).every((h) => h);

        res.status(allHealthy ? 200 : 503).json({
          status: allHealthy ? "healthy" : "unhealthy",
          timestamp: new Date().toISOString(),
          stacks: health,
        });
      } catch (error) {
        res.status(500).json({
          status: "error",
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Execute plan on specific stack
    this.app.post("/execute/:stack", async (req, res) => {
      try {
        const { stack } = req.params;
        const { plan, context } = req.body;

        if (!plan || !context) {
          return res.status(400).json({
            error: "Missing required fields: plan and context",
            timestamp: new Date().toISOString(),
          });
        }

        // Validate context
        if (!context.tenant || !context.session_id || !context.request_id) {
          return res.status(400).json({
            error: "Invalid context: missing tenant, session_id, or request_id",
            timestamp: new Date().toISOString(),
          });
        }

        const result = await this.gateway.executePlan(stack, plan, context);

        res.status(result.success ? 200 : 500).json(result);
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Get metrics for all stacks
    this.app.get("/metrics", async (req, res) => {
      try {
        const metrics = await this.gateway.getStackMetrics();
        res.json({
          timestamp: new Date().toISOString(),
          metrics,
        });
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Get metrics for specific stack
    this.app.get("/metrics/:stack", async (req, res) => {
      try {
        const { stack } = req.params;
        const metrics = await this.gateway.getStackMetrics();

        if (!metrics[stack]) {
          return res.status(404).json({
            error: `Stack ${stack} not found`,
            timestamp: new Date().toISOString(),
          });
        }

        res.json({
          stack,
          timestamp: new Date().toISOString(),
          ...metrics[stack],
        });
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Export traces for specific journey
    this.app.get("/traces/:journey/:tenant", async (req, res) => {
      try {
        const { journey, tenant } = req.params;
        const traces = await this.gateway.exportJourneyTraces(journey, tenant);

        res.json({
          journey,
          tenant,
          count: traces.length,
          traces,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Get gateway configuration
    this.app.get("/config", (req, res) => {
      const config = this.gateway.getConfig();
      const enforceMode = this.gateway.isEnforceMode();

      res.json({
        ...config,
        enforce_mode: enforceMode,
        timestamp: new Date().toISOString(),
      });
    });

    // Get observability data
    this.app.get("/observability", (req, res) => {
      try {
        const data = this.observability.getSummary();
        res.json({
          timestamp: new Date().toISOString(),
          ...data,
        });
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : "Unknown error",
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Error handling middleware
    this.app.use(
      (
        error: Error,
        req: express.Request,
        res: express.Response,
        next: express.NextFunction,
      ) => {
        console.error("Unhandled error:", error);
        res.status(500).json({
          error: "Internal server error",
          timestamp: new Date().toISOString(),
        });
      },
    );

    // 404 handler
    this.app.use("*", (req, res) => {
      res.status(404).json({
        error: "Endpoint not found",
        path: req.originalUrl,
        timestamp: new Date().toISOString(),
      });
    });
  }

  /**
   * Start the server
   */
  start(): void {
    const port = this.config.port;
    const host = this.config.host;

    this.app.listen(port, host, () => {
      console.log(`🚀 Gateway server started on ${host}:${port}`);
      console.log(`📊 Metrics available at http://${host}:${port}/metrics`);
      console.log(`🔍 Health check at http://${host}:${port}/health`);
      console.log(
        `⚙️  Enforce mode: ${this.gateway.isEnforceMode() ? "ENABLED" : "DISABLED"}`,
      );
    });
  }

  /**
   * Get the Express app instance
   */
  getApp(): express.Application {
    return this.app;
  }

  /**
   * Get the gateway instance
   */
  getGateway(): UnifiedGateway {
    return this.gateway;
  }
}
