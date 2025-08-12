#!/usr/bin/env python3
"""
Security Gates Runner for Provability Fabric Testbed

This script validates the security gates for:
- TB-RETRIEVE: Retrieval Gateway + Receipts
- TB-PLAN: Plan-DSL + Policy Kernel
- TB-EGRESS: Content Egress Firewall + Certificates

Usage:
    python run_security_gates.py [--component COMPONENT] [--verbose]
"""

import asyncio
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


class SecurityGateRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {}
        self.testbed_root = Path(__file__).parent.parent.parent

    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def run_command(
        self, command: List[str], cwd: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Run a command and return results"""
        if self.verbose:
            self.log(f"Running: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.testbed_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out after 5 minutes",
                "returncode": -1,
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    async def run_tb_retrieve_gates(self) -> Dict[str, Any]:
        """Run TB-RETRIEVE security gates"""
        self.log("Running TB-RETRIEVE security gates...")

        results = {
            "cross_tenant_isolation": False,
            "receipt_validation": False,
            "honeytoken_detection": False,
            "ed25519_signatures": False,
            "sharded_indices": False,
        }

        # Test cross-tenant isolation (0 cross-tenant reads in 100k fuzzed queries)
        self.log("Testing cross-tenant isolation with fuzzed queries...")
        fuzz_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=fuzzing.test.ts",
                '--testNamePattern="should maintain zero cross-tenant reads in 100,000 fuzzed queries"',  # noqa: E501
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if fuzz_result["success"]:
            results["cross_tenant_isolation"] = True
            self.log("✓ Cross-tenant isolation test passed")
        else:
            self.log(f"✗ Cross-tenant isolation test failed: {fuzz_result['stderr']}")

        # Test Ed25519 signature verification
        self.log("Testing Ed25519 signature verification...")
        ed25519_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=ed25519.test.ts",
                '--testNamePattern="should generate valid Ed25519 signatures for access receipts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if ed25519_result["success"]:
            results["ed25519_signatures"] = True
            self.log("✓ Ed25519 signature test passed")
        else:
            self.log(f"✗ Ed25519 signature test failed: {ed25519_result['stderr']}")

        # Test honeytoken detection
        self.log("Testing honeytoken detection...")
        honeytoken_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=ed25519.test.ts",
                '--testNamePattern="should detect honeytoken access and trigger alerts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if honeytoken_result["success"]:
            results["honeytoken_detection"] = True
            self.log("✓ Honeytoken detection test passed")
        else:
            self.log(
                f"✗ Honeytoken detection test failed: {honeytoken_result['stderr']}"
            )

        # Test receipt validation
        self.log("Testing receipt validation...")
        receipt_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=ed25519.test.ts",
                '--testNamePattern="should reject expired receipts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if receipt_result["success"]:
            results["receipt_validation"] = True
            self.log("✓ Receipt validation test passed")
        else:
            self.log(f"✗ Receipt validation test failed: {receipt_result['stderr']}")

        # Test sharded indices
        self.log("Testing sharded indices...")
        shard_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=gateway.test.ts",
                '--testNamePattern="should maintain complete tenant isolation"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if shard_result["success"]:
            results["sharded_indices"] = True
            self.log("✓ Sharded indices test passed")
        else:
            self.log(f"✗ Sharded indices test failed: {shard_result['stderr']}")

        return results

    async def run_tb_plan_gates(self) -> Dict[str, Any]:
        """Run TB-PLAN security gates"""
        self.log("Running TB-PLAN security gates...")

        results = {
            "injection_blocking": False,
            "capability_matching": False,
            "receipt_validation": False,
            "label_flow": False,
            "numeric_refinements": False,
        }

        # Test injection blocking (≥95% blocked)
        self.log("Testing injection blocking...")
        injection_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should block SQL injection attempts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if injection_result["success"]:
            results["injection_blocking"] = True
            self.log("✓ Injection blocking test passed")
        else:
            self.log(f"✗ Injection blocking test failed: {injection_result['stderr']}")

        # Test capability matching
        self.log("Testing capability matching...")
        capability_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should validate capability matching"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if capability_result["success"]:
            results["capability_matching"] = True
            self.log("✓ Capability matching test passed")
        else:
            self.log(
                f"✗ Capability matching test failed: {capability_result['stderr']}"
            )

        # Test receipt validation
        self.log("Testing receipt validation...")
        receipt_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should validate valid receipts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if receipt_result["success"]:
            results["receipt_validation"] = True
            self.log("✓ Receipt validation test passed")
        else:
            self.log(f"✗ Receipt validation test failed: {receipt_result['stderr']}")

        # Test label flow
        self.log("Testing label flow...")
        label_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should reject steps with missing input labels"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if label_result["success"]:
            results["label_flow"] = True
            self.log("✓ Label flow test passed")
        else:
            self.log(f"✗ Label flow test failed: {label_result['stderr']}")

        # Test numeric refinements
        self.log("Testing numeric refinements...")
        numeric_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should validate budget constraints"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if numeric_result["success"]:
            results["numeric_refinements"] = True
            self.log("✓ Numeric refinements test passed")
        else:
            self.log(f"✗ Numeric refinements test failed: {numeric_result['stderr']}")

        return results

    async def run_tb_egress_gates(self) -> Dict[str, Any]:
        """Run TB-EGRESS security gates"""
        self.log("Running TB-EGRESS security gates...")

        results = {
            "pii_detection": False,
            "secret_detection": False,
            "injection_blocking": False,
            "performance_400ms": False,
            "ed25519_certificates": False,
        }

        # Test PII detection
        self.log("Testing PII detection...")
        pii_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should detect credit card numbers"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if pii_result["success"]:
            results["pii_detection"] = True
            self.log("✓ PII detection test passed")
        else:
            self.log(f"✗ PII detection test failed: {pii_result['stderr']}")

        # Test secret detection
        self.log("Testing secret detection...")
        secret_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should detect API keys"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if secret_result["success"]:
            results["secret_detection"] = True
            self.log("✓ Secret detection test passed")
        else:
            self.log(f"✗ Secret detection test failed: {secret_result['stderr']}")

        # Test injection blocking
        self.log("Testing injection blocking...")
        injection_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should detect suspicious injection patterns"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if injection_result["success"]:
            results["injection_blocking"] = True
            self.log("✓ Injection blocking test passed")
        else:
            self.log(f"✗ Injection blocking test failed: {injection_result['stderr']}")

        # Test performance (P95 < 400ms)
        self.log("Testing performance requirements...")
        perf_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should process content within 400ms P95 requirement"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if perf_result["success"]:
            results["performance_400ms"] = True
            self.log("✓ Performance test passed")
        else:
            self.log(f"✗ Performance test failed: {perf_result['stderr']}")

        # Test Ed25519 certificates
        self.log("Testing Ed25519 certificates...")
        cert_result = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should generate valid certificates with Ed25519 signatures"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if cert_result["success"]:
            results["ed25519_certificates"] = True
            self.log("✓ Ed25519 certificates test passed")
        else:
            self.log(f"✗ Ed25519 certificates test failed: {cert_result['stderr']}")

        return results

    async def run_adversarial_tests(self) -> Dict[str, Any]:
        """Run adversarial tests to validate security gates"""
        self.log("Running adversarial tests...")

        results = {
            "tb_retrieve_adversarial": False,
            "tb_plan_adversarial": False,
            "tb_egress_adversarial": False,
        }

        # Test TB-RETRIEVE adversarial scenarios
        self.log("Testing TB-RETRIEVE adversarial scenarios...")
        tb_retrieve_adv = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=fuzzing.test.ts",
                '--testNamePattern="should maintain tenant isolation under concurrent access"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "retrieval-gateway",
        )

        if tb_retrieve_adv["success"]:
            results["tb_retrieve_adversarial"] = True
            self.log("✓ TB-RETRIEVE adversarial test passed")
        else:
            self.log(
                f"✗ TB-RETRIEVE adversarial test failed: {tb_retrieve_adv['stderr']}"
            )

        # Test TB-PLAN adversarial scenarios
        self.log("Testing TB-PLAN adversarial scenarios...")
        tb_plan_adv = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=kernel.test.ts",
                '--testNamePattern="should reject requests with injection attempts"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "policy-kernel",
        )

        if tb_plan_adv["success"]:
            results["tb_plan_adversarial"] = True
            self.log("✓ TB-PLAN adversarial test passed")
        else:
            self.log(f"✗ TB-PLAN adversarial test failed: {tb_plan_adv['stderr']}")

        # Test TB-EGRESS adversarial scenarios
        self.log("Testing TB-EGRESS adversarial scenarios...")
        tb_egress_adv = self.run_command(
            [
                "npm",
                "test",
                "--",
                "--testPathPattern=firewall.test.ts",
                '--testNamePattern="should block 0 critical PII/secret leaks in adversarial scenarios"',
            ],
            cwd=self.testbed_root / "testbed" / "runtime" / "egress-firewall",
        )

        if tb_egress_adv["success"]:
            results["tb_egress_adversarial"] = True
            self.log("✓ TB-EGRESS adversarial test passed")
        else:
            self.log(f"✗ TB-EGRESS adversarial test failed: {tb_egress_adv['stderr']}")

        return results

    async def run_all_gates(self) -> Dict[str, Any]:
        """Run all security gates"""
        self.log("Starting comprehensive security gate validation...")

        start_time = time.time()

        # Run all component gates
        tb_retrieve_results = await self.run_tb_retrieve_gates()
        tb_plan_results = await self.run_tb_plan_gates()
        tb_egress_results = await self.run_tb_egress_gates()
        adversarial_results = await self.run_adversarial_tests()

        # Compile results
        all_results = {
            "tb_retrieve": tb_retrieve_results,
            "tb_plan": tb_plan_results,
            "tb_egress": tb_egress_results,
            "adversarial": adversarial_results,
            "summary": {},
        }

        # Calculate summary statistics
        total_tests = 0
        passed_tests = 0

        for component, results in all_results.items():
            if component == "summary":
                continue

            component_tests = len(results)
            component_passed = sum(1 for passed in results.values() if passed)

            total_tests += component_tests
            passed_tests += component_passed

            all_results["summary"][component] = {
                "total": component_tests,
                "passed": component_passed,
                "percentage": (
                    (component_passed / component_tests * 100)
                    if component_tests > 0
                    else 0
                ),
            }

        all_results["summary"]["overall"] = {
            "total": total_tests,
            "passed": passed_tests,
            "percentage": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        }

        end_time = time.time()
        all_results["execution_time"] = end_time - start_time

        return all_results

    def print_results(self, results: Dict[str, Any]):
        """Print formatted results"""
        print("\n" + "=" * 80)
        print("SECURITY GATES VALIDATION RESULTS")
        print("=" * 80)

        # Print component results
        for component, component_results in results.items():
            if component in ["summary", "execution_time"]:
                continue

            print(f"\n{component.upper().replace('_', ' ')}:")
            print("-" * 40)

            for test_name, passed in component_results.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {test_name.replace('_', ' ').title()}: {status}")

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        summary = results["summary"]
        for component, stats in summary.items():
            if component == "overall":
                continue
            print(
                f"{component.upper().replace('_', ' ')}: {stats['passed']}/{stats['total']} ({stats['percentage']:.1f}%)"
            )

        overall = summary["overall"]
        print(
            f"\nOVERALL: {overall['passed']}/{overall['total']} ({overall['percentage']:.1f}%)"
        )

        # Print execution time
        execution_time = results.get("execution_time", 0)
        print(f"\nExecution time: {execution_time:.2f} seconds")

        # Print final status
        if overall["percentage"] >= 95:
            print("\n🎉 SECURITY GATES VALIDATION PASSED! 🎉")
            print("All critical security requirements have been met.")
        else:
            print("\n❌ SECURITY GATES VALIDATION FAILED! ❌")
            print("Some critical security requirements have not been met.")
            print("Please review the failed tests above.")

        print("=" * 80)

    def save_results(
        self, results: Dict[str, Any], output_file: str = "security_gates_results.json"
    ):
        """Save results to JSON file"""
        output_path = self.testbed_root / output_file

        # Convert Path objects to strings for JSON serialization
        serializable_results = json.loads(json.dumps(results, default=str))

        with open(output_path, "w") as f:
            json.dump(serializable_results, f, indent=2)

        self.log(f"Results saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Run Provability Fabric Security Gates"
    )
    parser.add_argument(
        "--component",
        choices=["tb-retrieve", "tb-plan", "tb-egress", "all"],
        default="all",
        help="Component to test",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--output",
        "-o",
        default="security_gates_results.json",
        help="Output file for results",
    )

    args = parser.parse_args()

    runner = SecurityGateRunner(verbose=args.verbose)

    try:
        if args.component == "all":
            results = await runner.run_all_gates()
        elif args.component == "tb-retrieve":
            results = {"tb_retrieve": await runner.run_tb_retrieve_gates()}
        elif args.component == "tb-plan":
            results = {"tb_plan": await runner.run_tb_plan_gates()}
        elif args.component == "tb-egress":
            results = {"tb_egress": await runner.run_tb_egress_gates()}

        runner.print_results(results)
        runner.save_results(results, args.output)

        # Exit with appropriate code
        summary = results.get("summary", {})
        overall = summary.get("overall", {})
        if overall.get("percentage", 0) >= 95:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        runner.log("Security gates validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        runner.log(f"Security gates validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
