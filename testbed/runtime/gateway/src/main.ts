import { GatewayServer } from "./server";
import { GatewayConfig } from "./types";
import { OpenAIAssistantsRunner } from "../agents/openai_assistants/runner";
import { LangChainRunner } from "../agents/langchain/runner";
import { LangGraphRunner } from "../agents/langgraph/runner";
import { DSPyRunner } from "../agents/dspy/runner";

// Default configuration
const defaultConfig: GatewayConfig = {
  port: parseInt(process.env.GATEWAY_PORT || "3000"),
  host: process.env.GATEWAY_HOST || "0.0.0.0",
  cors_origins: process.env.CORS_ORIGINS?.split(",") || [
    "http://localhost:3000",
    "http://localhost:3001",
  ],
  rate_limit: {
    window_ms: parseInt(process.env.RATE_LIMIT_WINDOW_MS || "60000"),
    max_requests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || "100"),
  },
  auth: {
    enabled: process.env.AUTH_ENABLED === "true",
    jwt_secret: process.env.JWT_SECRET,
    api_keys: process.env.API_KEYS?.split(","),
  },
  monitoring: {
    enabled: process.env.MONITORING_ENABLED !== "false",
    metrics_port: parseInt(process.env.METRICS_PORT || "9090"),
    health_check_interval: parseInt(
      process.env.HEALTH_CHECK_INTERVAL || "30000",
    ),
  },
};

/**
 * Initialize all agent runners
 */
async function initializeAgents(gateway: any) {
  try {
    console.log("🤖 Initializing agent runners...");

    // OpenAI Assistants
    try {
      const openaiRunner = new OpenAIAssistantsRunner();
      await openaiRunner.configure({
        model: process.env.OPENAI_MODEL || "gpt-4",
        provider: "openai",
        api_key: process.env.OPENAI_API_KEY,
        timeout: parseInt(process.env.OPENAI_TIMEOUT || "30000"),
        max_retries: parseInt(process.env.OPENAI_MAX_RETRIES || "3"),
        shadow_mode: process.env.PF_ENFORCE !== "true",
        enforce_policies: process.env.PF_ENFORCE === "true",
      });
      gateway.registerAgent("openai-assistants", openaiRunner);
      console.log("✅ OpenAI Assistants runner initialized");
    } catch (error) {
      console.warn("⚠️  OpenAI Assistants runner failed to initialize:", error);
    }

    // LangChain
    try {
      const langchainRunner = new LangChainRunner();
      await langchainRunner.configure({
        model: process.env.LANGCHAIN_MODEL || "gpt-4",
        provider: "langchain",
        api_key: process.env.LANGCHAIN_API_KEY,
        timeout: parseInt(process.env.LANGCHAIN_TIMEOUT || "30000"),
        max_retries: parseInt(process.env.LANGCHAIN_MAX_RETRIES || "3"),
        shadow_mode: process.env.PF_ENFORCE !== "true",
        enforce_policies: process.env.PF_ENFORCE === "true",
      });
      gateway.registerAgent("langchain", langchainRunner);
      console.log("✅ LangChain runner initialized");
    } catch (error) {
      console.warn("⚠️  LangChain runner failed to initialize:", error);
    }

    // LangGraph
    try {
      const langgraphRunner = new LangGraphRunner();
      await langgraphRunner.configure({
        model: process.env.LANGGRAPH_MODEL || "gpt-4",
        provider: "langgraph",
        api_key: process.env.LANGGRAPH_API_KEY,
        timeout: parseInt(process.env.LANGGRAPH_TIMEOUT || "30000"),
        max_retries: parseInt(process.env.LANGGRAPH_MAX_RETRIES || "3"),
        shadow_mode: process.env.PF_ENFORCE !== "true",
        enforce_policies: process.env.PF_ENFORCE === "true",
      });
      gateway.registerAgent("langgraph", langgraphRunner);
      console.log("✅ LangGraph runner initialized");
    } catch (error) {
      console.warn("⚠️  LangGraph runner failed to initialize:", error);
    }

    // DSPy
    try {
      const dspyRunner = new DSPyRunner();
      await dspyRunner.configure({
        model: process.env.DSPY_MODEL || "gpt-4",
        provider: "dspy",
        api_key: process.env.DSPY_API_KEY,
        timeout: parseInt(process.env.DSPY_TIMEOUT || "30000"),
        max_retries: parseInt(process.env.DSPY_MAX_RETRIES || "3"),
        shadow_mode: process.env.PF_ENFORCE !== "true",
        enforce_policies: process.env.PF_ENFORCE === "true",
      });
      gateway.registerAgent("dspy", dspyRunner);
      console.log("✅ DSPy runner initialized");
    } catch (error) {
      console.warn("⚠️  DSPy runner failed to initialize:", error);
    }

    console.log("🎯 Agent initialization complete");
  } catch (error) {
    console.error("❌ Failed to initialize agents:", error);
    throw error;
  }
}

/**
 * Main function
 */
async function main() {
  try {
    console.log("🚀 Starting Provability Fabric Testbed Gateway...");
    console.log(`⚙️  Configuration:`, {
      port: defaultConfig.port,
      host: defaultConfig.host,
      enforce_mode: process.env.PF_ENFORCE === "true" ? "ENABLED" : "DISABLED",
      monitoring: defaultConfig.monitoring.enabled ? "ENABLED" : "DISABLED",
    });

    // Create and start server
    const server = new GatewayServer(defaultConfig);

    // Initialize agents
    await initializeAgents(server.getGateway());

    // Start server
    server.start();

    console.log("🎉 Gateway startup complete!");
    console.log("📚 Available endpoints:");
    console.log("   POST /execute/:stack - Execute plan on specific stack");
    console.log("   GET  /metrics       - Get metrics for all stacks");
    console.log("   GET  /health        - Health check");
    console.log("   GET  /traces/:journey/:tenant - Export traces");
    console.log("   GET  /config        - Gateway configuration");
    console.log("   GET  /observability - Observability data");
  } catch (error) {
    console.error("💥 Failed to start gateway:", error);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on("SIGTERM", () => {
  console.log("🛑 Received SIGTERM, shutting down gracefully...");
  process.exit(0);
});

process.on("SIGINT", () => {
  console.log("🛑 Received SIGINT, shutting down gracefully...");
  process.exit(0);
});

// Start the application
if (require.main === module) {
  main().catch((error) => {
    console.error("💥 Unhandled error in main:", error);
    process.exit(1);
  });
}

export { main, initializeAgents };
