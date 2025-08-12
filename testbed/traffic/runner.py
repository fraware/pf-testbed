#!/usr/bin/env python3
"""
Traffic Runner for Testbed
Generates realistic workloads with reproducible seeds, ramps, bursts, and diurnal patterns.
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import yaml
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    "testbed_requests_total", "Total requests made", ["scenario", "tenant", "status"]
)
REQUEST_DURATION = Histogram(
    "testbed_request_duration_seconds",
    "Request duration in seconds",
    ["scenario", "tenant"],
)
ACTIVE_USERS = Gauge("testbed_active_users", "Number of active users")
REQUEST_RATE = Gauge("testbed_request_rate_rps", "Current request rate in RPS")
ERROR_RATE = Gauge("testbed_error_rate", "Current error rate")
SECURITY_VIOLATIONS = Counter(
    "testbed_security_violations_total", "Total security violations", ["type", "tenant"]
)


@dataclass
class TrafficConfig:
    """Configuration for traffic generation"""

    base_rps: float = 10.0
    max_rps: float = 100.0
    ramp_duration_minutes: int = 5
    soak_duration_minutes: int = 30
    burst_duration_seconds: int = 30
    burst_multiplier: float = 3.0
    diurnal_enabled: bool = True
    diurnal_peak_hour: int = 14  # 2 PM
    diurnal_peak_multiplier: float = 2.0
    diurnal_valley_multiplier: float = 0.3
    random_seed: int = 42
    scenarios: List[str] = None
    tenant_distribution: Dict[str, float] = None
    failure_injection_rate: float = 0.01
    security_test_rate: float = 0.05


@dataclass
class RequestResult:
    """Result of a single request"""

    request_id: str
    scenario: str
    tenant: str
    timestamp: float
    duration: float
    status_code: int
    success: bool
    error_message: str = ""
    security_violations: List[str] = None
    response_size: int = 0
    plan_id: str = ""
    certificate_id: str = ""


@dataclass
class TestResult:
    """Overall test results"""

    test_id: str
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    security_violations: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    avg_rps: float
    max_rps: float
    scenarios_tested: List[str]
    tenants_tested: List[str]
    performance_metrics: Dict[str, Any]
    security_metrics: Dict[str, Any]


class TrafficRunner:
    """Main traffic runner class"""

    def __init__(self, config: TrafficConfig, api_base_url: str):
        self.config = config
        self.api_base_url = api_base_url
        self.results: List[RequestResult] = []
        self.test_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None

        # Set random seed for reproducibility
        random.seed(config.random_seed)
        np.random.seed(config.random_seed)

        # Load scenarios
        self.scenarios = self._load_scenarios()

        # Initialize tenant distribution
        if not config.tenant_distribution:
            self.config.tenant_distribution = self._generate_tenant_distribution()

        # Performance tracking
        self.request_timestamps = []
        self.response_times = []
        self.error_counts = 0
        self.security_violation_counts = 0

        logger.info(f"Traffic runner initialized with test ID: {self.test_id}")
        logger.info(f"Configuration: {asdict(config)}")

    def _load_scenarios(self) -> Dict[str, Any]:
        """Load user journey scenarios from YAML file"""
        try:
            with open("testbed/scenarios/user_journeys.yaml", "r") as f:
                scenarios = yaml.safe_load(f)
            logger.info(f"Loaded {len(scenarios.get('scenarios', {}))} scenarios")
            return scenarios
        except Exception as e:
            logger.error(f"Failed to load scenarios: {e}")
            return {}

    def _generate_tenant_distribution(self) -> Dict[str, float]:
        """Generate realistic tenant distribution"""
        tenants = [
            "finance-team",
            "analytics-team",
            "engineering-team",
            "legal-team",
            "security-team",
            "community-team",
            "healthcare-team",
        ]
        # Generate weights based on typical enterprise usage patterns
        weights = [0.25, 0.20, 0.15, 0.10, 0.15, 0.10, 0.05]
        return dict(zip(tenants, weights))

    def _get_current_rps(self, elapsed_seconds: float) -> float:
        """Calculate current RPS based on traffic pattern"""
        rps = self.config.base_rps

        # Ramp up phase
        if elapsed_seconds < self.config.ramp_duration_minutes * 60:
            ramp_progress = elapsed_seconds / (self.config.ramp_duration_minutes * 60)
            rps = (
                self.config.base_rps
                + (self.config.max_rps - self.config.base_rps) * ramp_progress
            )

        # Soak phase
        elif (
            elapsed_seconds
            < (self.config.ramp_duration_minutes + self.config.soak_duration_minutes)
            * 60
        ):
            rps = self.config.max_rps

        # Ramp down phase
        else:
            remaining_time = (
                self.config.ramp_duration_minutes * 2
                + self.config.soak_duration_minutes
            ) * 60 - elapsed_seconds
            if remaining_time > 0:
                ramp_progress = remaining_time / (
                    self.config.ramp_duration_minutes * 60
                )
                rps = (
                    self.config.base_rps
                    + (self.config.max_rps - self.config.base_rps) * ramp_progress
                )

        # Apply diurnal pattern if enabled
        if self.config.diurnal_enabled:
            current_hour = datetime.now().hour
            hour_diff = abs(current_hour - self.config.diurnal_peak_hour)
            if hour_diff <= 3:  # Peak hours
                rps *= self.config.diurnal_peak_multiplier
            elif hour_diff >= 8:  # Valley hours
                rps *= self.config.diurnal_valley_multiplier

        # Apply burst pattern
        burst_cycle = (
            elapsed_seconds % (self.config.burst_duration_seconds * 2)
        ) / self.config.burst_duration_seconds
        if burst_cycle < 1.0:  # Burst phase
            rps *= self.config.burst_multiplier

        return max(0.1, rps)

    def _select_scenario(self) -> Tuple[str, Dict[str, Any]]:
        """Select a random scenario based on weights"""
        if not self.scenarios.get("scenarios"):
            return "default", {}

        scenario_names = list(self.scenarios["scenarios"].keys())
        # Weight scenarios by complexity (more complex = higher weight for testing)
        weights = []
        for name in scenario_names:
            scenario = self.scenarios["scenarios"][name]
            complexity = len(scenario.get("allowed_tools", []))
            weights.append(complexity)

        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        selected = random.choices(scenario_names, weights=weights)[0]
        return selected, self.scenarios["scenarios"][selected]

    def _select_tenant(self) -> str:
        """Select a random tenant based on distribution"""
        tenants = list(self.config.tenant_distribution.keys())
        weights = list(self.config.tenant_distribution.values())
        return random.choices(tenants, weights=weights)[0]

    def _generate_request_payload(
        self, scenario: str, scenario_config: Dict[str, Any], tenant: str
    ) -> Dict[str, Any]:
        """Generate realistic request payload for the scenario"""
        # Base payload
        payload = {
            "scenario": scenario,
            "tenant": tenant,
            "timestamp": time.time(),
            "request_id": str(uuid.uuid4()),
            "context": {
                "user_agent": "testbed-traffic-runner/1.0",
                "source_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "session_id": str(uuid.uuid4()),
                "request_type": "user_query",
            },
        }

        # Add scenario-specific inputs
        if scenario_config.get("inputs"):
            payload.update(scenario_config["inputs"])

        # Add security test payloads occasionally
        if random.random() < self.config.security_test_rate:
            payload = self._inject_security_test_payload(payload)

        return payload

    def _inject_security_test_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Inject security test payloads to test injection protection"""
        security_tests = [
            # SQL injection attempts
            {"user_query": "'; DROP TABLE users; --"},
            # XSS attempts
            {"user_query": "<script>alert('xss')</script>"},
            # Command injection
            {"user_query": "test; rm -rf /"},
            # Path traversal
            {"user_query": "../../../etc/passwd"},
            # Malicious plan injection
            {
                "plan_id": "malicious_plan_123",
                "allowed_operations": ["system_exec", "file_delete"],
            },
        ]

        test_payload = random.choice(security_tests)
        payload.update(test_payload)
        payload["security_test"] = True

        return payload

    async def _make_request(
        self, session: aiohttp.ClientSession, payload: Dict[str, Any]
    ) -> RequestResult:
        """Make a single request to the API"""
        start_time = time.time()
        request_id = payload.get("request_id", str(uuid.uuid4()))
        scenario = payload.get("scenario", "unknown")
        tenant = payload.get("tenant", "unknown")

        try:
            # Determine endpoint based on scenario
            endpoint = f"{self.api_base_url}/api/v1/execute"

            async with session.post(endpoint, json=payload, timeout=30) as response:
                duration = time.time() - start_time
                response_text = await response.text()

                # Parse response
                success = response.status == 200
                security_violations = []

                if success:
                    try:
                        response_data = json.loads(response_text)
                        security_violations = response_data.get(
                            "security_violations", []
                        )
                        certificate_id = response_data.get("certificate_id", "")
                        plan_id = response_data.get("plan_id", "")
                    except json.JSONDecodeError:
                        pass

                result = RequestResult(
                    request_id=request_id,
                    scenario=scenario,
                    tenant=tenant,
                    timestamp=start_time,
                    duration=duration,
                    status_code=response.status,
                    success=success,
                    error_message="" if success else response_text,
                    security_violations=security_violations,
                    response_size=len(response_text),
                    plan_id=payload.get("plan_id", ""),
                    certificate_id=certificate_id,
                )

                # Update metrics
                REQUESTS_TOTAL.labels(
                    scenario=scenario,
                    tenant=tenant,
                    status="success" if success else "failure",
                ).inc()
                REQUEST_DURATION.labels(scenario=scenario, tenant=tenant).observe(
                    duration
                )

                if not success:
                    self.error_counts += 1

                if security_violations:
                    self.security_violation_counts += 1
                    for violation in security_violations:
                        SECURITY_VIOLATIONS.labels(type=violation, tenant=tenant).inc()

                return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed: {e}")

            result = RequestResult(
                request_id=request_id,
                scenario=scenario,
                tenant=tenant,
                timestamp=start_time,
                duration=duration,
                status_code=0,
                success=False,
                error_message=str(e),
                security_violations=[],
            )

            # Update metrics
            REQUESTS_TOTAL.labels(
                scenario=scenario, tenant=tenant, status="failure"
            ).inc()
            self.error_counts += 1

            return result

    async def _run_traffic_cycle(
        self, session: aiohttp.ClientSession, target_rps: float
    ) -> None:
        """Run a single traffic cycle"""
        # Calculate delay between requests
        delay = 1.0 / target_rps if target_rps > 0 else 1.0

        # Select scenario and tenant
        scenario, scenario_config = self._select_scenario()
        tenant = self._select_tenant()

        # Generate payload
        payload = self._generate_request_payload(scenario, scenario_config, tenant)

        # Make request
        result = await self._make_request(session, payload)
        self.results.append(result)

        # Update performance tracking
        self.request_timestamps.append(result.timestamp)
        self.response_times.append(result.duration)

        # Update Prometheus metrics
        REQUEST_RATE.set(target_rps)
        ERROR_RATE.set(self.error_counts / max(1, len(self.results)))
        ACTIVE_USERS.set(min(len(self.results), 100))  # Cap at 100 for visualization

        # Log progress
        if len(self.results) % 100 == 0:
            logger.info(
                f"Completed {len(self.results)} requests, current RPS: {target_rps:.2f}"
            )

    async def run_test(self) -> TestResult:
        """Run the complete traffic test"""
        logger.info(f"Starting traffic test {self.test_id}")
        self.start_time = datetime.now()

        # Start Prometheus metrics server
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")

        # Calculate total test duration
        total_duration = (
            self.config.ramp_duration_minutes * 2 + self.config.soak_duration_minutes
        ) * 60

        async with aiohttp.ClientSession() as session:
            start_time = time.time()

            while time.time() - start_time < total_duration:
                elapsed = time.time() - start_time
                current_rps = self._get_current_rps(elapsed)

                # Run traffic cycle
                await self._run_traffic_cycle(session, current_rps)

                # Calculate delay for next cycle
                delay = 1.0 / current_rps if current_rps > 0 else 1.0
                await asyncio.sleep(delay)

        self.end_time = datetime.now()
        logger.info(f"Traffic test completed. Total requests: {len(self.results)}")

        # Generate test results
        return self._generate_test_results()

    def _generate_test_results(self) -> TestResult:
        """Generate comprehensive test results"""
        if not self.results:
            return TestResult(
                test_id=self.test_id,
                start_time=self.start_time or datetime.now(),
                end_time=self.end_time or datetime.now(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                security_violations=0,
                avg_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                avg_rps=0.0,
                max_rps=0.0,
                scenarios_tested=[],
                tenants_tested=[],
                performance_metrics={},
                security_metrics={},
            )

        # Basic metrics
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests
        security_violations = sum(1 for r in self.results if r.security_violations)

        # Response time metrics
        response_times = [r.duration for r in self.results]
        avg_response_time = np.mean(response_times)
        p95_response_time = np.percentile(response_times, 95)
        p99_response_time = np.percentile(response_times, 99)

        # RPS metrics
        test_duration = (self.end_time - self.start_time).total_seconds()
        avg_rps = total_requests / test_duration
        max_rps = max(self._get_current_rps(t) for t in range(int(test_duration)))

        # Scenarios and tenants
        scenarios_tested = list(set(r.scenario for r in self.results))
        tenants_tested = list(set(r.tenant for r in self.results))

        # Performance metrics
        performance_metrics = {
            "response_time_distribution": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": avg_response_time,
                "std": np.std(response_times),
                "p50": np.percentile(response_times, 50),
                "p90": np.percentile(response_times, 90),
                "p95": p95_response_time,
                "p99": p99_response_time,
            },
            "throughput": {
                "total_requests": total_requests,
                "avg_rps": avg_rps,
                "max_rps": max_rps,
                "test_duration_seconds": test_duration,
            },
            "error_analysis": {
                "error_rate": failed_requests / total_requests,
                "error_distribution": self._analyze_errors(),
            },
        }

        # Security metrics
        security_metrics = {
            "total_violations": security_violations,
            "violation_rate": security_violations / total_requests,
            "violation_types": self._analyze_security_violations(),
            "injection_attempts": self._analyze_injection_attempts(),
        }

        return TestResult(
            test_id=self.test_id,
            start_time=self.start_time,
            end_time=self.end_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            security_violations=security_violations,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            avg_rps=avg_rps,
            max_rps=max_rps,
            scenarios_tested=scenarios_tested,
            tenants_tested=tenants_tested,
            performance_metrics=performance_metrics,
            security_metrics=security_metrics,
        )

    def _analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_results = [r for r in self.results if not r.success]

        if not error_results:
            return {"total_errors": 0, "error_types": {}}

        error_types = {}
        for result in error_results:
            error_type = "timeout" if result.duration > 30 else "api_error"
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(error_results),
            "error_types": error_types,
            "error_timeline": self._generate_error_timeline(error_results),
        }

    def _analyze_security_violations(self) -> Dict[str, Any]:
        """Analyze security violation patterns"""
        violation_results = [r for r in self.results if r.security_violations]

        if not violation_results:
            return {"total_violations": 0, "violation_types": {}}

        violation_types = {}
        for result in violation_results:
            for violation in result.security_violations:
                violation_types[violation] = violation_types.get(violation, 0) + 1

        return {
            "total_violations": len(violation_results),
            "violation_types": violation_types,
            "violation_timeline": self._generate_violation_timeline(violation_results),
        }

    def _analyze_injection_attempts(self) -> Dict[str, Any]:
        """Analyze injection attempt patterns"""
        injection_results = [r for r in self.results if r.scenario == "security_test"]

        if not injection_results:
            return {"total_attempts": 0, "blocked_attempts": 0, "success_rate": 0.0}

        blocked_attempts = sum(1 for r in injection_results if r.security_violations)
        success_rate = blocked_attempts / len(injection_results)

        return {
            "total_attempts": len(injection_results),
            "blocked_attempts": blocked_attempts,
            "success_rate": success_rate,
            "injection_types": self._categorize_injection_types(injection_results),
        }

    def _generate_error_timeline(
        self, error_results: List[RequestResult]
    ) -> List[Dict[str, Any]]:
        """Generate error timeline for analysis"""
        timeline = []
        for result in error_results:
            timeline.append(
                {
                    "timestamp": result.timestamp,
                    "scenario": result.scenario,
                    "tenant": result.tenant,
                    "error_type": "timeout" if result.duration > 30 else "api_error",
                }
            )
        return timeline

    def _generate_violation_timeline(
        self, violation_results: List[RequestResult]
    ) -> List[Dict[str, Any]]:
        """Generate security violation timeline for analysis"""
        timeline = []
        for result in violation_results:
            for violation in result.security_violations:
                timeline.append(
                    {
                        "timestamp": result.timestamp,
                        "scenario": result.scenario,
                        "tenant": result.tenant,
                        "violation_type": violation,
                    }
                )
        return timeline

    def _categorize_injection_types(
        self, injection_results: List[RequestResult]
    ) -> Dict[str, int]:
        """Categorize injection attempt types"""
        categories = {
            "sql_injection": 0,
            "xss": 0,
            "command_injection": 0,
            "path_traversal": 0,
            "plan_injection": 0,
        }

        for result in injection_results:
            if "DROP TABLE" in result.plan_id or "DROP TABLE" in getattr(
                result, "user_query", ""
            ):
                categories["sql_injection"] += 1
            elif "<script>" in getattr(result, "user_query", ""):
                categories["xss"] += 1
            elif "rm -rf" in getattr(result, "user_query", ""):
                categories["command_injection"] += 1
            elif "../" in getattr(result, "user_query", ""):
                categories["path_traversal"] += 1
            elif "malicious_plan" in result.plan_id:
                categories["plan_injection"] += 1

        return categories

    def save_results(
        self, results: TestResult, output_dir: str = "testbed/results"
    ) -> None:
        """Save test results to files"""
        os.makedirs(output_dir, exist_ok=True)

        # Save detailed results
        results_file = f"{output_dir}/test_results_{self.test_id}.json"
        with open(results_file, "w") as f:
            json.dump(asdict(results), f, indent=2, default=str)

        # Save raw request data
        raw_data_file = f"{output_dir}/raw_data_{self.test_id}.json"
        with open(raw_data_file, "w") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2, default=str)

        # Generate performance report
        self._generate_performance_report(results, output_dir)

        # Generate security report
        self._generate_security_report(results, output_dir)

        logger.info(f"Results saved to {output_dir}")

    def _generate_performance_report(
        self, results: TestResult, output_dir: str
    ) -> None:
        """Generate performance analysis report"""
        # Create performance plots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Response time distribution
        response_times = [r.duration for r in self.results]
        ax1.hist(response_times, bins=50, alpha=0.7, edgecolor="black")
        ax1.set_xlabel("Response Time (seconds)")
        ax1.set_ylabel("Frequency")
        ax1.set_title("Response Time Distribution")
        ax1.axvline(
            results.avg_response_time,
            color="red",
            linestyle="--",
            label=f"Mean: {results.avg_response_time:.3f}s",
        )
        ax1.axvline(
            results.p95_response_time,
            color="orange",
            linestyle="--",
            label=f"P95: {results.p95_response_time:.3f}s",
        )
        ax1.axvline(
            results.p99_response_time,
            color="yellow",
            linestyle="--",
            label=f"P99: {results.p99_response_time:.3f}s",
        )
        ax1.legend()

        # RPS over time
        timestamps = [r.timestamp for r in self.results]
        start_time = min(timestamps)
        time_series = [(t - start_time) / 60 for t in timestamps]  # Convert to minutes

        # Calculate rolling RPS
        window_size = 60  # 1 minute window
        rps_series = []
        for i in range(0, len(time_series), window_size):
            window = time_series[i : i + window_size]
            if window:
                rps = (
                    len(window) / (max(window) - min(window)) if len(window) > 1 else 0
                )
                rps_series.append(rps)

        ax2.plot(range(len(rps_series)), rps_series)
        ax2.set_xlabel("Time Window (minutes)")
        ax2.set_ylabel("Requests per Second")
        ax2.set_title("RPS Over Time")
        ax2.axhline(
            results.avg_rps,
            color="red",
            linestyle="--",
            label=f"Avg: {results.avg_rps:.2f} RPS",
        )
        ax2.legend()

        # Success rate by scenario
        scenarios = list(set(r.scenario for r in self.results))
        success_rates = []
        for scenario in scenarios:
            scenario_results = [r for r in self.results if r.scenario == scenario]
            success_rate = sum(1 for r in scenario_results if r.success) / len(
                scenario_results
            )
            success_rates.append(success_rate)

        ax3.bar(scenarios, success_rates, alpha=0.7)
        ax3.set_xlabel("Scenario")
        ax3.set_ylabel("Success Rate")
        ax3.set_title("Success Rate by Scenario")
        ax3.tick_params(axis="x", rotation=45)

        # Response time by tenant
        tenants = list(set(r.tenant for r in self.results))
        tenant_response_times = []
        for tenant in tenants:
            tenant_results = [r.duration for r in self.results if r.tenant == tenant]
            tenant_response_times.append(np.mean(tenant_results))

        ax4.bar(tenants, tenant_response_times, alpha=0.7)
        ax4.set_xlabel("Tenant")
        ax4.set_ylabel("Average Response Time (seconds)")
        ax4.set_title("Response Time by Tenant")
        ax4.tick_params(axis="x", rotation=45)

        plt.tight_layout()
        plt.savefig(
            f"{output_dir}/performance_report_{self.test_id}.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def _generate_security_report(self, results: TestResult, output_dir: str) -> None:
        """Generate security analysis report"""
        # Create security plots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Security violations over time
        violation_results = [r for r in self.results if r.security_violations]
        if violation_results:
            violation_timestamps = [r.timestamp for r in violation_results]
            start_time = min(violation_timestamps)
            violation_times = [(t - start_time) / 60 for t in violation_timestamps]

            ax1.scatter(
                violation_times, range(len(violation_times)), alpha=0.7, color="red"
            )
            ax1.set_xlabel("Time (minutes)")
            ax1.set_ylabel("Violation Count")
            ax1.set_title("Security Violations Over Time")
        else:
            ax1.text(
                0.5,
                0.5,
                "No Security Violations",
                ha="center",
                va="center",
                transform=ax1.transAxes,
            )
            ax1.set_title("Security Violations Over Time")

        # Violation types distribution
        if violation_results:
            violation_types = {}
            for result in violation_results:
                for violation in result.security_violations:
                    violation_types[violation] = violation_types.get(violation, 0) + 1

            if violation_types:
                ax2.pie(
                    violation_types.values(),
                    labels=violation_types.keys(),
                    autopct="%1.1f%%",
                )
                ax2.set_title("Security Violation Types")
            else:
                ax2.text(
                    0.5,
                    0.5,
                    "No Violations",
                    ha="center",
                    va="center",
                    transform=ax2.transAxes,
                )
                ax2.set_title("Security Violation Types")
        else:
            ax2.text(
                0.5,
                0.5,
                "No Violations",
                ha="center",
                va="center",
                transform=ax2.transAxes,
            )
            ax2.set_title("Security Violation Types")

        # Injection attempt analysis
        injection_results = [r for r in self.results if r.scenario == "security_test"]
        if injection_results:
            injection_types = self._categorize_injection_types(injection_results)
            ax3.bar(
                injection_types.keys(),
                injection_types.values(),
                alpha=0.7,
                color="orange",
            )
            ax3.set_xlabel("Injection Type")
            ax3.set_ylabel("Attempt Count")
            ax3.set_title("Injection Attempts by Type")
            ax3.tick_params(axis="x", rotation=45)
        else:
            ax3.text(
                0.5,
                0.5,
                "No Injection Attempts",
                ha="center",
                va="center",
                transform=ax3.transAxes,
            )
            ax3.set_title("Injection Attempts by Type")

        # Security metrics summary
        security_summary = [
            f"Total Requests: {results.total_requests}",
            f"Security Violations: {results.security_violations}",
            f"Violation Rate: {results.security_violations/results.total_requests*100:.2f}%",
            f"Successful Blocks: {sum(1 for r in injection_results if r.security_violations)}",
            f"Block Rate: {sum(1 for r in injection_results if r.security_violations)/max(1, len(injection_results))*100:.1f}%",
        ]

        ax4.text(
            0.1,
            0.9,
            "\n".join(security_summary),
            transform=ax4.transAxes,
            fontsize=12,
            verticalalignment="top",
            fontfamily="monospace",
        )
        ax4.set_title("Security Metrics Summary")
        ax4.axis("off")

        plt.tight_layout()
        plt.savefig(
            f"{output_dir}/security_report_{self.test_id}.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


async def main():
    """Main function to run the traffic test"""
    # Configuration
    config = TrafficConfig(
        base_rps=10.0,
        max_rps=50.0,
        ramp_duration_minutes=2,
        soak_duration_minutes=5,
        burst_duration_seconds=15,
        burst_multiplier=2.0,
        diurnal_enabled=False,  # Disable for testing
        random_seed=42,
        failure_injection_rate=0.02,
        security_test_rate=0.10,
    )

    # API base URL
    api_base_url = "http://localhost:8080"

    # Create and run traffic runner
    runner = TrafficRunner(config, api_base_url)

    try:
        results = await runner.run_test()

        # Save results
        runner.save_results(results)

        # Print summary
        print("\n" + "=" * 80)
        print("TRAFFIC TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Test ID: {results.test_id}")
        print(f"Duration: {results.end_time - results.start_time}")
        print(f"Total Requests: {results.total_requests}")
        print(
            f"Success Rate: {results.successful_requests/results.total_requests*100:.2f}%"
        )
        print(f"Security Violations: {results.security_violations}")
        print(f"Average Response Time: {results.avg_response_time:.3f}s")
        print(f"P95 Response Time: {results.p95_response_time:.3f}s")
        print(f"P99 Response Time: {results.p99_response_time:.3f}s")
        print(f"Average RPS: {results.avg_rps:.2f}")
        print(f"Max RPS: {results.max_rps:.2f}")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Traffic test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
