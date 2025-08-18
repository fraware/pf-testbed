#!/usr/bin/env ts-node

import { createHash } from "crypto";
import { DecisionPathEngine, DecisionPathTrace, SafetyCase, EgressCertificate, RetrievalReceipt } from "../runtime/gateway/src/decision_path";
import { observabilityService } from "../runtime/gateway/src/observability";

// Synthetic Probe for Continuous Monitoring
// Runs every minute to verify:
// 1. Cert present
// 2. Policy hash matches
// 3. Receipts verified
// 4. Non-interference checks pass

export interface ProbeResult {
  timestamp: string;
  probe_id: string;
  checks: {
    cert_present: boolean;
    policy_hash_match: boolean;
    receipts_verified: boolean;
    non_interference_pass: boolean;
    decision_path_complete: boolean;
  };
  violations: string[];
  metrics: {
    total_checks: number;
    passed_checks: number;
    failed_checks: number;
    success_rate: number;
  };
  alerts: Array<{
    severity: "low" | "medium" | "high" | "critical";
    message: string;
    details: any;
  }>;
}

export interface ProbeConfig {
  interval_ms: number;
  timeout_ms: number;
  max_retries: number;
  alert_threshold: number; // Alert if success rate drops below this
  enabled_checks: Array<keyof ProbeResult["checks"]>;
}

export class SyntheticProbe {
  private config: ProbeConfig;
  private decisionPathEngine: DecisionPathEngine;
  private isRunning: boolean = false;
  private probeHistory: ProbeResult[] = [];
  private lastProbeTime: number = 0;

  constructor(config: ProbeConfig) {
    this.config = config;
    this.decisionPathEngine = new DecisionPathEngine();
  }

  /**
   * Start the synthetic probe
   */
  start(): void {
    if (this.isRunning) {
      console.log("Synthetic probe is already running");
      return;
    }

    this.isRunning = true;
    console.log("Starting synthetic probe with interval:", this.config.interval_ms, "ms");

    // Run initial probe
    this.runProbe();

    // Schedule periodic probes
    setInterval(() => {
      if (this.isRunning) {
        this.runProbe();
      }
    }, this.config.interval_ms);
  }

  /**
   * Stop the synthetic probe
   */
  stop(): void {
    this.isRunning = false;
    console.log("Synthetic probe stopped");
  }

  /**
   * Run a single probe cycle
   */
  private async runProbe(): Promise<void> {
    const startTime = Date.now();
    const probe_id = this.generateProbeId();

    console.log(`Running probe ${probe_id} at ${new Date().toISOString()}`);

    try {
      const result = await this.executeProbe(probe_id);
      
      // Store result
      this.probeHistory.push(result);
      this.lastProbeTime = startTime;

      // Update observability metrics
      this.updateObservabilityMetrics(result);

      // Check for violations and create alerts
      this.checkViolationsAndAlert(result);

      // Log results
      this.logProbeResults(result);

      // Clean up old history (keep last 1000 probes)
      if (this.probeHistory.length > 1000) {
        this.probeHistory = this.probeHistory.slice(-1000);
      }

    } catch (error) {
      console.error(`Probe ${probe_id} failed:`, error);
      
      // Create critical alert for probe failure
      const alert = {
        severity: "critical" as const,
        message: `Synthetic probe ${probe_id} failed to execute`,
        details: { error: error instanceof Error ? error.message : "Unknown error" }
      };

      observabilityService.createSecurityAlert({
        severity: "critical",
        type: "decision_path_failure",
        message: alert.message,
        tenant: "system",
        proof_hash: this.generateProofHash(probe_id),
      });
    }
  }

  /**
   * Execute all probe checks
   */
  private async executeProbe(probe_id: string): Promise<ProbeResult> {
    const checks = {
      cert_present: false,
      policy_hash_match: false,
      receipts_verified: false,
      non_interference_pass: false,
      decision_path_complete: false,
    };

    const violations: string[] = [];
    const alerts: ProbeResult["alerts"] = [];

    // Check 1: Cert present
    if (this.config.enabled_checks.includes("cert_present")) {
      checks.cert_present = await this.checkCertPresent();
      if (!checks.cert_present) {
        violations.push("No valid egress certificates found");
        alerts.push({
          severity: "high",
          message: "Egress certificate missing",
          details: { probe_id, check: "cert_present" }
        });
      }
    }

    // Check 2: Policy hash matches
    if (this.config.enabled_checks.includes("policy_hash_match")) {
      checks.policy_hash_match = await this.checkPolicyHashMatch();
      if (!checks.policy_hash_match) {
        violations.push("Policy hash mismatch detected");
        alerts.push({
          severity: "critical",
          message: "Policy hash mismatch - potential tampering",
          details: { probe_id, check: "policy_hash_match" }
        });
      }
    }

    // Check 3: Receipts verified
    if (this.config.enabled_checks.includes("receipts_verified")) {
      checks.receipts_verified = await this.checkReceiptsVerified();
      if (!checks.receipts_verified) {
        violations.push("Receipt verification failed");
        alerts.push({
          severity: "high",
          message: "Receipt verification failed",
          details: { probe_id, check: "receipts_verified" }
        });
      }
    }

    // Check 4: Non-interference checks pass
    if (this.config.enabled_checks.includes("non_interference_pass")) {
      checks.non_interference_pass = await this.checkNonInterferencePass();
      if (!checks.non_interference_pass) {
        violations.push("Non-interference check failed");
        alerts.push({
          severity: "critical",
          message: "Non-interference violation detected",
          details: { probe_id, check: "non_interference_pass" }
        });
      }
    }

    // Check 5: Decision path complete
    if (this.config.enabled_checks.includes("decision_path_complete")) {
      checks.decision_path_complete = await this.checkDecisionPathComplete();
      if (!checks.decision_path_complete) {
        violations.push("Decision path incomplete");
        alerts.push({
          severity: "medium",
          message: "Decision path incomplete",
          details: { probe_id, check: "decision_path_complete" }
        });
      }
    }

    // Calculate metrics
    const total_checks = Object.values(checks).filter(Boolean).length;
    const passed_checks = Object.values(checks).filter(check => check).length;
    const failed_checks = total_checks - passed_checks;
    const success_rate = total_checks > 0 ? passed_checks / total_checks : 0;

    return {
      timestamp: new Date().toISOString(),
      probe_id,
      checks,
      violations,
      metrics: {
        total_checks,
        passed_checks,
        failed_checks,
        success_rate,
      },
      alerts,
    };
  }

  /**
   * Check 1: Verify egress certificates are present and valid
   */
  private async checkCertPresent(): Promise<boolean> {
    try {
      // Get recent traces
      const traces = this.decisionPathEngine.getAllTraces();
      if (traces.length === 0) {
        return true; // No traces to check
      }

      // Check if recent traces have certificates
      const recentTraces = traces.filter(t => 
        new Date(t.timestamp).getTime() > Date.now() - 5 * 60 * 1000 // Last 5 minutes
      );

      if (recentTraces.length === 0) {
        return true; // No recent traces
      }

      // Verify each trace has certificates
      for (const trace of recentTraces) {
        if (trace.certificates.length === 0) {
          console.warn(`Trace ${trace.trace_id} missing certificates`);
          return false;
        }

        // Verify certificate validity
        for (const certId of trace.certificates) {
          const cert = this.decisionPathEngine.getEgressCertificate(certId);
          if (!cert) {
            console.warn(`Certificate ${certId} not found`);
            return false;
          }

          // Check certificate age (should be recent)
          const certAge = Date.now() - new Date(cert.timestamp).getTime();
          if (certAge > 10 * 60 * 1000) { // Older than 10 minutes
            console.warn(`Certificate ${certId} is too old: ${certAge}ms`);
            return false;
          }
        }
      }

      return true;
    } catch (error) {
      console.error("Error checking certificates:", error);
      return false;
    }
  }

  /**
   * Check 2: Verify policy hashes match expected values
   */
  private async checkPolicyHashMatch(): Promise<boolean> {
    try {
      // Get recent traces
      const traces = this.decisionPathEngine.getAllTraces();
      if (traces.length === 0) {
        return true; // No traces to check
      }

      // Check if recent traces have consistent policy hashes
      const recentTraces = traces.filter(t => 
        new Date(t.timestamp).getTime() > Date.now() - 5 * 60 * 1000 // Last 5 minutes
      );

      if (recentTraces.length === 0) {
        return true; // No recent traces
      }

      // Extract policy hashes from safety cases
      const policyHashes = new Set<string>();
      
      for (const trace of recentTraces) {
        for (const safetyCaseId of trace.safety_cases) {
          const safetyCase = this.decisionPathEngine.getSafetyCase(safetyCaseId);
          if (safetyCase) {
            policyHashes.add(safetyCase.evidence.policy_hash);
          }
        }
      }

      // If we have multiple policy hashes, check if they're all valid
      if (policyHashes.size > 1) {
        console.warn(`Multiple policy hashes detected: ${Array.from(policyHashes).join(", ")}`);
        // This could be normal if policies are updated, but we should verify
        return this.validatePolicyHashes(Array.from(policyHashes));
      }

      return true;
    } catch (error) {
      console.error("Error checking policy hashes:", error);
      return false;
    }
  }

  /**
   * Check 3: Verify access receipts are valid and not expired
   */
  private async checkReceiptsVerified(): Promise<boolean> {
    try {
      // Get recent traces
      const traces = this.decisionPathEngine.getAllTraces();
      if (traces.length === 0) {
        return true; // No traces to check
      }

      // Check if recent traces have valid receipts
      const recentTraces = traces.filter(t => 
        new Date(t.timestamp).getTime() > Date.now() - 5 * 60 * 1000 // Last 5 minutes
      );

      if (recentTraces.length === 0) {
        return true; // No recent traces
      }

      // Verify each receipt
      for (const trace of recentTraces) {
        for (const receiptId of trace.receipts) {
          const receipt = this.decisionPathEngine.getRetrievalReceipt(receiptId);
          if (!receipt) {
            console.warn(`Receipt ${receiptId} not found`);
            return false;
          }

          // Check if receipt is expired
          if (new Date(receipt.expires_at) < new Date()) {
            console.warn(`Receipt ${receiptId} is expired`);
            return false;
          }

          // Verify receipt signature (basic check)
          if (!receipt.signature || receipt.signature.length < 10) {
            console.warn(`Receipt ${receiptId} has invalid signature`);
            return false;
          }
        }
      }

      return true;
    } catch (error) {
      console.error("Error checking receipts:", error);
      return false;
    }
  }

  /**
   * Check 4: Verify non-interference checks are passing
   */
  private async checkNonInterferencePass(): Promise<boolean> {
    try {
      // Get recent traces
      const traces = this.decisionPathEngine.getAllTraces();
      if (traces.length === 0) {
        return true; // No traces to check
      }

      // Check if recent traces have passing non-interference
      const recentTraces = traces.filter(t => 
        new Date(t.timestamp).getTime() > Date.now() - 5 * 60 * 1000 // Last 5 minutes
      );

      if (recentTraces.length === 0) {
        return true; // No recent traces
      }

      // Check each trace's egress certificates for NI status
      for (const trace of recentTraces) {
        for (const certId of trace.certificates) {
          const cert = this.decisionPathEngine.getEgressCertificate(certId);
          if (cert && cert.non_interference.verdict !== "passed") {
            console.warn(`Certificate ${certId} has NI verdict: ${cert.non_interference.verdict}`);
            return false;
          }
        }
      }

      return true;
    } catch (error) {
      console.error("Error checking non-interference:", error);
      return false;
    }
  }

  /**
   * Check 5: Verify decision paths are complete
   */
  private async checkDecisionPathComplete(): Promise<boolean> {
    try {
      // Get recent traces
      const traces = this.decisionPathEngine.getAllTraces();
      if (traces.length === 0) {
        return true; // No traces to check
      }

      // Check if recent traces are complete
      const recentTraces = traces.filter(t => 
        new Date(t.timestamp).getTime() > Date.now() - 5 * 60 * 1000 // Last 5 minutes
      );

      if (recentTraces.length === 0) {
        return true; // No recent traces
      }

      // Verify each trace has all required phases
      for (const trace of recentTraces) {
        const requiredPhases = ["observe", "retrieve", "plan", "kernel", "tool_broker", "egress", "safety_case"];
        const completedPhases = trace.steps.map(s => s.phase);
        
        for (const requiredPhase of requiredPhases) {
          if (!completedPhases.includes(requiredPhase)) {
            console.warn(`Trace ${trace.trace_id} missing phase: ${requiredPhase}`);
            return false;
          }
        }

        // Check if trace completed successfully
        if (trace.final_status !== "completed") {
          console.warn(`Trace ${trace.trace_id} status: ${trace.final_status}`);
          return false;
        }
      }

      return true;
    } catch (error) {
      console.error("Error checking decision path completion:", error);
      return false;
    }
  }

  /**
   * Validate policy hashes against expected values
   */
  private validatePolicyHashes(hashes: string[]): boolean {
    // In a real implementation, this would check against a trusted policy store
    // For now, we'll just verify they're valid SHA256 hashes
    const validHashPattern = /^[a-fA-F0-9]{64}$/;
    
    for (const hash of hashes) {
      if (!validHashPattern.test(hash)) {
        console.warn(`Invalid policy hash format: ${hash}`);
        return false;
      }
    }

    return true;
  }

  /**
   * Update observability metrics with probe results
   */
  private updateObservabilityMetrics(result: ProbeResult): void {
    // Record probe success/failure
    const success = result.metrics.success_rate >= this.config.alert_threshold;
    
    // Update decision path phase metrics for the probe
    observabilityService.recordDecisionPathPhase("safety_case", 0, success, {
      cases_generated: 1,
      probe_id: result.probe_id,
    });

    // Record non-interference check
    observabilityService.recordNonInterferenceCheck(
      result.checks.non_interference_pass,
      "probe",
      this.generateProofHash(result.probe_id)
    );
  }

  /**
   * Check for violations and create alerts
   */
  private checkViolationsAndAlert(result: ProbeResult): void {
    // Create alerts for any violations
    for (const alert of result.alerts) {
      observabilityService.createSecurityAlert({
        severity: alert.severity,
        type: "decision_path_failure",
        message: alert.message,
        tenant: "system",
        proof_hash: this.generateProofHash(result.probe_id),
      });
    }

    // Check if overall success rate is below threshold
    if (result.metrics.success_rate < this.config.alert_threshold) {
      observabilityService.createSecurityAlert({
        severity: "high",
        type: "decision_path_failure",
        message: `Synthetic probe success rate ${(result.metrics.success_rate * 100).toFixed(1)}% below threshold ${(this.config.alert_threshold * 100).toFixed(1)}%`,
        tenant: "system",
        proof_hash: this.generateProofHash(result.probe_id),
      });
    }
  }

  /**
   * Log probe results
   */
  private logProbeResults(result: ProbeResult): void {
    const status = result.metrics.success_rate >= this.config.alert_threshold ? "PASS" : "FAIL";
    console.log(`[${status}] Probe ${result.probe_id}: ${result.metrics.passed_checks}/${result.metrics.total_checks} checks passed (${(result.metrics.success_rate * 100).toFixed(1)}%)`);
    
    if (result.violations.length > 0) {
      console.warn(`Violations: ${result.violations.join(", ")}`);
    }
  }

  /**
   * Get probe history
   */
  getProbeHistory(): ProbeResult[] {
    return [...this.probeHistory];
  }

  /**
   * Get latest probe result
   */
  getLatestProbeResult(): ProbeResult | null {
    return this.probeHistory.length > 0 ? this.probeHistory[this.probeHistory.length - 1] : null;
  }

  /**
   * Get probe statistics
   */
  getProbeStats(): {
    total_probes: number;
    success_rate: number;
    last_probe_time: number;
    average_success_rate: number;
  } {
    if (this.probeHistory.length === 0) {
      return {
        total_probes: 0,
        success_rate: 0,
        last_probe_time: 0,
        average_success_rate: 0,
      };
    }

    const total_probes = this.probeHistory.length;
    const last_probe = this.probeHistory[this.probeHistory.length - 1];
    const success_rate = last_probe.metrics.success_rate;
    const last_probe_time = new Date(last_probe.timestamp).getTime();
    
    const total_success_rate = this.probeHistory.reduce((sum, p) => sum + p.metrics.success_rate, 0);
    const average_success_rate = total_success_rate / total_probes;

    return {
      total_probes,
      success_rate,
      last_probe_time,
      average_success_rate,
    };
  }

  // Utility methods
  private generateProbeId(): string {
    return `probe_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateProofHash(probe_id: string): string {
    return createHash("sha256").update(probe_id + Date.now().toString()).digest("hex");
  }
}

// Default configuration
const defaultConfig: ProbeConfig = {
  interval_ms: 60 * 1000, // 1 minute
  timeout_ms: 30 * 1000,  // 30 seconds
  max_retries: 3,
  alert_threshold: 0.95,   // 95% success rate
  enabled_checks: ["cert_present", "policy_hash_match", "receipts_verified", "non_interference_pass", "decision_path_complete"],
};

// Export singleton instance
export const syntheticProbe = new SyntheticProbe(defaultConfig);

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.includes("--start")) {
    syntheticProbe.start();
    console.log("Synthetic probe started. Press Ctrl+C to stop.");
    
    process.on("SIGINT", () => {
      console.log("\nStopping synthetic probe...");
      syntheticProbe.stop();
      process.exit(0);
    });
  } else if (args.includes("--status")) {
    const stats = syntheticProbe.getProbeStats();
    console.log("Probe Statistics:", JSON.stringify(stats, null, 2));
    
    const latest = syntheticProbe.getLatestProbeResult();
    if (latest) {
      console.log("Latest Probe Result:", JSON.stringify(latest, null, 2));
    }
  } else {
    console.log("Usage:");
    console.log("  --start   Start the synthetic probe");
    console.log("  --status  Show probe status and latest results");
  }
}
