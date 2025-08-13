"use strict";
// Canonical adapter interface for Provability Fabric Testbed
// This defines the standard interface that all agent runners must implement
Object.defineProperty(exports, "__esModule", { value: true });
exports.RISK_LEVELS =
  exports.CAPABILITY_SCOPES =
  exports.SUPPORTED_TOOLS =
  exports.SUPPORTED_JOURNEYS =
  exports.ToolExecutionError =
  exports.ReceiptError =
  exports.CapabilityError =
  exports.PlanValidationError =
    void 0;
// Error types
class PlanValidationError extends Error {
  constructor(message, errors) {
    super(message);
    this.errors = errors;
    this.name = "PlanValidationError";
  }
}
exports.PlanValidationError = PlanValidationError;
class CapabilityError extends Error {
  constructor(message, capability) {
    super(message);
    this.capability = capability;
    this.name = "CapabilityError";
  }
}
exports.CapabilityError = CapabilityError;
class ReceiptError extends Error {
  constructor(message, receipt_id) {
    super(message);
    this.receipt_id = receipt_id;
    this.name = "ReceiptError";
  }
}
exports.ReceiptError = ReceiptError;
class ToolExecutionError extends Error {
  constructor(message, tool, parameters) {
    super(message);
    this.tool = tool;
    this.parameters = parameters;
    this.name = "ToolExecutionError";
  }
}
exports.ToolExecutionError = ToolExecutionError;
// Constants
exports.SUPPORTED_JOURNEYS = [
  "support_triage",
  "expense_approval",
  "sales_outreach",
  "hr_onboarding",
  "dev_triage",
];
exports.SUPPORTED_TOOLS = [
  "slack",
  "email",
  "calendar",
  "notion",
  "stripe",
  "github",
  "search",
  "fetch",
];
exports.CAPABILITY_SCOPES = ["read", "write", "delete", "admin"];
exports.RISK_LEVELS = ["low", "medium", "high", "critical"];
//# sourceMappingURL=types.js.map
