#!/usr/bin/env python3
"""
Chaos Testing Runner for Testbed
Integrates with k6 load testing to inject faults while monitoring SLO gates.
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import yaml
import aiohttp
import numpy as np
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import subprocess
import threading
import signal
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics for chaos testing
CHAOS_FAULTS_INJECTED = Counter(
    "chaos_faults_injected_total",
    "Total chaos faults injected",
    ["fault_type", "severity"],
)
SLO_VIOLATIONS = Counter(
    "slo_violations_total",
    "Total SLO violations during chaos",
    ["slo_name", "severity"],
)
BACKPRESSURE_ACTIVATIONS = Counter(
    "backpressure_activations_total",
    "Total backpressure activations",
    ["trigger", "action"],
)
SYSTEM_HEALTH = Gauge("system_health_score", "Overall system health score")
FAULT_ACTIVE = Gauge("fault_active", "Whether a fault is currently active", ["type"])


@dataclass
class ChaosFault:
    """Configuration for a chaos fault"""

    name: str
    fault_type: str
    severity: str  # low, medium, high, critical
    duration_seconds: int
    probability: float  # 0.0 to 1.0
    parameters: Dict[str, Any]
    slo_impact: List[str]  # Which SLOs this fault affects


@dataclass
class SLOGate:
    """Service Level Objective gate configuration"""

    name: str
    metric: str
    threshold: float
    operator: str  # >, <, >=, <=, ==
    window_seconds: int
    severity: str  # warning, critical
    backpressure_trigger: bool


@dataclass
class ChaosTest:
    """Complete chaos test configuration"""

    test_id: str
    name: str
    description: str
    duration_minutes: int
    load_profile: str
    faults: List[ChaosFault]
    slo_gates: List[SLOGate]
    backpressure_config: Dict[str, Any]
    k6_config: Dict[str, Any]


@dataclass
class TestResult:
    """Results from a chaos test"""

    test_id: str
    start_time: datetime
    end_time: datetime
    total_faults_injected: int
    slo_violations: int
    backpressure_activations: int
    system_health_score: float
    fault_results: List[Dict[str, Any]]
    slo_results: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class ChaosRunner:
    """Main chaos testing runner"""

    def __init__(self, config: ChaosTest):
        self.config = config
        self.active_faults: Dict[str, ChaosFault] = {}
        self.slo_violations: List[Dict[str, Any]] = []
        self.backpressure_active = False
        self.health_score = 100.0
        self.test_start_time = None
        self.test_end_time = None
        self.k6_process = None
        self.metrics_collector = None

        # Initialize Prometheus metrics
        start_http_server(8001)
        logger.info("Chaos testing metrics server started on port 8001")

    async def run_chaos_test(self) -> TestResult:
        """Run the complete chaos test"""
        logger.info(f"Starting chaos test: {self.config.name}")
        self.test_start_time = datetime.now()

        try:
            # Start k6 load testing
            await self._start_k6_load()

            # Start metrics collection
            await self._start_metrics_collection()

            # Run chaos injection loop
            await self._run_chaos_loop()

            # Wait for test completion
            await self._wait_for_completion()

        except Exception as e:
            logger.error(f"Chaos test failed: {e}")
            raise
        finally:
            # Cleanup
            await self._cleanup()

        self.test_end_time = datetime.now()
        return self._generate_test_results()

    async def _start_k6_load(self):
        """Start k6 load testing process"""
        k6_script = self._generate_k6_script()

        # Write k6 script to file
        script_path = f"testbed/chaos/k6_script_{self.config.test_id}.js"
        os.makedirs(os.path.dirname(script_path), exist_ok=True)

        with open(script_path, "w") as f:
            f.write(k6_script)

        # Start k6 process
        cmd = [
            "k6",
            "run",
            "--out",
            "prometheus=localhost:9090",
            "--tag",
            f"test_id={self.config.test_id}",
            script_path,
        ]

        self.k6_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        logger.info(f"Started k6 load testing with PID: {self.k6_process.pid}")

    def _generate_k6_script(self) -> str:
        """Generate k6 load testing script"""
        load_profile = self.config.k6_config.get("load_profile", "ramp")

        if load_profile == "ramp":
            return self._generate_ramp_script()
        elif load_profile == "constant":
            return self._generate_constant_script()
        elif load_profile == "spike":
            return self._generate_spike_script()
        else:
            return self._generate_ramp_script()

    def _generate_ramp_script(self) -> str:
        """Generate k6 script with ramp-up pattern"""
        return f"""
import http from 'k6/http';
import {{ check, sleep }} from 'k6';
import {{ Rate }} from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {{
    stages: [
        {{ duration: '2m', target: {self.config.k6_config.get('target_rps', 100)} }},
        {{ duration: '5m', target: {self.config.k6_config.get('target_rps', 100)} }},
        {{ duration: '2m', target: 0 }},
    ],
    thresholds: {{
        http_req_duration: ['p(95)<{self.config.k6_config.get('p95_threshold', 500)}'],
        http_req_failed: ['rate<{self.config.k6_config.get('error_threshold', 0.01)}'],
    }},
}};

export default function() {{
    const response = http.get('{self.config.k6_config.get('target_url', 'http://localhost:8080')}/api/v1/health');
    
    check(response, {{
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    }});
    
    errorRate.add(response.status !== 200);
    
    sleep(1);
}}
"""

    def _generate_constant_script(self) -> str:
        """Generate k6 script with constant load"""
        return f"""
import http from 'k6/http';
import {{ check, sleep }} from 'k6';
import {{ Rate }} from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {{
    vus: {self.config.k6_config.get('vus', 50)},
    duration: '{self.config.duration_minutes}m',
    thresholds: {{
        http_req_duration: ['p(95)<{self.config.k6_config.get('p95_threshold', 500)}'],
        http_req_failed: ['rate<{self.config.k6_config.get('error_threshold', 0.01)}'],
    }},
}};

export default function() {{
    const response = http.get('{self.config.k6_config.get('target_url', 'http://localhost:8080')}/api/v1/health');
    
    check(response, {{
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    }});
    
    errorRate.add(response.status !== 200);
    
    sleep(1);
}}
"""

    def _generate_spike_script(self) -> str:
        """Generate k6 script with spike pattern"""
        return f"""
import http from 'k6/http';
import {{ check, sleep }} from 'k6';
import {{ Rate }} from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {{
    stages: [
        {{ duration: '2m', target: {self.config.k6_config.get('target_rps', 100)} }},
        {{ duration: '1m', target: {self.config.k6_config.get('target_rps', 100) * 3} }},
        {{ duration: '2m', target: {self.config.k6_config.get('target_rps', 100)} }},
        {{ duration: '1m', target: 0 }},
    ],
    thresholds: {{
        http_req_duration: ['p(95)<{self.config.k6_config.get('p95_threshold', 500)}'],
        http_req_failed: ['rate<{self.config.k6_config.get('error_threshold', 0.01)}'],
    }},
}};

export default function() {{
    const response = http.get('{self.config.k6_config.get('target_url', 'http://localhost:8080')}/api/v1/health');
    
    check(response, {{
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    }});
    
    errorRate.add(response.status !== 200);
    
    sleep(1);
}}
"""

    async def _start_metrics_collection(self):
        """Start metrics collection from Prometheus"""
        self.metrics_collector = asyncio.create_task(self._collect_metrics_loop())

    async def _collect_metrics_loop(self):
        """Collect metrics from Prometheus in a loop"""
        while True:
            try:
                await self._collect_current_metrics()
                await asyncio.sleep(10)  # Collect every 10 seconds
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _collect_current_metrics(self):
        """Collect current metrics from Prometheus"""
        try:
            # Query Prometheus for current metrics
            async with aiohttp.ClientSession() as session:
                # Get response time metrics
                response_time_query = "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))"
                async with session.get(
                    "http://localhost:9090/api/v1/query",
                    params={"query": response_time_query},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data", {}).get("result"):
                            p95_response_time = float(
                                data["data"]["result"][0]["value"][1]
                            )
                            self._check_slo_gates(
                                "response_time_p95", p95_response_time
                            )

                # Get error rate metrics
                error_rate_query = 'rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m])'
                async with session.get(
                    "http://localhost:9090/api/v1/query",
                    params={"query": error_rate_query},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data", {}).get("result"):
                            error_rate = float(data["data"]["result"][0]["value"][1])
                            self._check_slo_gates("error_rate", error_rate)

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

    def _check_slo_gates(self, metric_name: str, current_value: float):
        """Check SLO gates and trigger backpressure if needed"""
        for slo in self.config.slo_gates:
            if slo.metric == metric_name:
                violation = self._evaluate_slo_violation(slo, current_value)
                if violation:
                    self._record_slo_violation(slo, current_value, violation)
                    if slo.backpressure_trigger:
                        self._activate_backpressure(slo, violation)

    def _evaluate_slo_violation(self, slo: SLOGate, value: float) -> Optional[str]:
        """Evaluate if an SLO is violated"""
        if slo.operator == ">":
            return "violated" if value > slo.threshold else None
        elif slo.operator == "<":
            return "violated" if value < slo.threshold else None
        elif slo.operator == ">=":
            return "violated" if value >= slo.threshold else None
        elif slo.operator == "<=":
            return "violated" if value <= slo.threshold else None
        elif slo.operator == "==":
            return "violated" if value == slo.threshold else None
        return None

    def _record_slo_violation(self, slo: SLOGate, value: float, violation: str):
        """Record an SLO violation"""
        violation_record = {
            "timestamp": datetime.now().isoformat(),
            "slo_name": slo.name,
            "metric": slo.metric,
            "threshold": slo.threshold,
            "current_value": value,
            "operator": slo.operator,
            "severity": slo.severity,
            "violation": violation,
        }

        self.slo_violations.append(violation_record)
        SLO_VIOLATIONS.labels(slo_name=slo.name, severity=slo.severity).inc()

        # Update health score
        if slo.severity == "critical":
            self.health_score = max(0, self.health_score - 20)
        else:
            self.health_score = max(0, self.health_score - 5)

        SYSTEM_HEALTH.set(self.health_score)

        logger.warning(
            f"SLO violation: {slo.name} = {value} {slo.operator} {slo.threshold}"
        )

    def _activate_backpressure(self, slo: SLOGate, violation: str):
        """Activate backpressure mechanisms"""
        if not self.backpressure_active:
            self.backpressure_active = True
            BACKPRESSURE_ACTIVATIONS.labels(trigger=slo.name, action="activated").inc()

            logger.warning(f"Backpressure activated due to SLO violation: {slo.name}")

            # Implement backpressure actions
            self._apply_backpressure_actions()

    def _apply_backpressure_actions(self):
        """Apply backpressure actions to stabilize the system"""
        try:
            # Reduce k6 load
            if self.k6_process and self.k6_process.poll() is None:
                # Send SIGUSR1 to k6 to reduce load
                self.k6_process.send_signal(signal.SIGUSR1)
                logger.info("Applied backpressure: Reduced k6 load")

            # Pause chaos fault injection
            self._pause_chaos_injection()

            # Wait for system to stabilize
            asyncio.create_task(self._wait_for_stabilization())

        except Exception as e:
            logger.error(f"Failed to apply backpressure: {e}")

    def _pause_chaos_injection(self):
        """Pause chaos fault injection temporarily"""
        logger.info("Paused chaos fault injection due to backpressure")

    async def _wait_for_stabilization(self):
        """Wait for system to stabilize before resuming"""
        await asyncio.sleep(60)  # Wait 1 minute

        # Check if SLOs are back to normal
        if self._check_slo_stabilization():
            self._deactivate_backpressure()

    def _check_slo_stabilization(self) -> bool:
        """Check if SLOs have stabilized"""
        # Check recent violations (last 5 minutes)
        recent_violations = [
            v
            for v in self.slo_violations
            if (datetime.now() - datetime.fromisoformat(v["timestamp"])).seconds < 300
        ]

        return len(recent_violations) == 0

    def _deactivate_backpressure(self):
        """Deactivate backpressure mechanisms"""
        self.backpressure_active = False
        BACKPRESSURE_ACTIVATIONS.labels(
            trigger="stabilization", action="deactivated"
        ).inc()

        logger.info("Backpressure deactivated - system stabilized")

    async def _run_chaos_loop(self):
        """Main chaos injection loop"""
        test_duration = timedelta(minutes=self.config.duration_minutes)
        start_time = datetime.now()

        while datetime.now() - start_time < test_duration:
            if not self.backpressure_active:
                await self._inject_chaos_faults()

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _inject_chaos_faults(self):
        """Inject chaos faults based on probability and configuration"""
        for fault in self.config.faults:
            if random.random() < fault.probability:
                if fault.name not in self.active_faults:
                    await self._inject_fault(fault)

    async def _inject_fault(self, fault: ChaosFault):
        """Inject a specific chaos fault"""
        try:
            logger.info(f"Injecting fault: {fault.name} ({fault.fault_type})")

            if fault.fault_type == "cpu_hog":
                await self._inject_cpu_hog(fault)
            elif fault.fault_type == "network_loss":
                await self._inject_network_loss(fault)
            elif fault.fault_type == "memory_leak":
                await self._inject_memory_leak(fault)
            elif fault.fault_type == "disk_io":
                await self._inject_disk_io(fault)

            # Mark fault as active
            self.active_faults[fault.name] = fault
            FAULT_ACTIVE.labels(type=fault.fault_type).set(1)

            # Schedule fault cleanup
            asyncio.create_task(self._cleanup_fault_after_duration(fault))

            # Record fault injection
            CHAOS_FAULTS_INJECTED.labels(
                fault_type=fault.fault_type, severity=fault.severity
            ).inc()

        except Exception as e:
            logger.error(f"Failed to inject fault {fault.name}: {e}")

    async def _inject_cpu_hog(self, fault: ChaosFault):
        """Inject CPU hog fault"""
        cpu_percent = fault.parameters.get("cpu_percent", 80)
        duration = fault.duration_seconds

        # Start CPU-intensive process
        cmd = [
            "python",
            "-c",
            f"import time; import multiprocessing as mp; "
            f"def cpu_hog(): "
            f"    while True: "
            f"        _ = sum(i*i for i in range(1000)); "
            f"p = mp.Process(target=cpu_hog); "
            f"p.start(); "
            f"time.sleep({duration}); "
            f"p.terminate()",
        ]

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Injected CPU hog: {cpu_percent}% for {duration}s")

    async def _inject_network_loss(self, fault: ChaosFault):
        """Inject network loss fault"""
        loss_percent = fault.parameters.get("loss_percent", 20)
        duration = fault.duration_seconds

        # Use tc (traffic control) to inject packet loss
        try:
            # Add qdisc
            subprocess.run(
                [
                    "tc",
                    "qdisc",
                    "add",
                    "dev",
                    "lo",
                    "root",
                    "netem",
                    "loss",
                    f"{loss_percent}%",
                ],
                check=True,
            )

            logger.info(f"Injected network loss: {loss_percent}% for {duration}s")

            # Schedule cleanup
            asyncio.create_task(self._cleanup_network_fault_after_duration(duration))

        except subprocess.CalledProcessError:
            logger.warning("Failed to inject network loss (tc not available)")

    async def _inject_memory_leak(self, fault: ChaosFault):
        """Inject memory leak fault"""
        memory_mb = fault.parameters.get("memory_mb", 100)
        duration = fault.duration_seconds

        # Start memory-consuming process
        cmd = [
            "python",
            "-c",
            f"import time; import array; "
            f"data = []; "
            f"for i in range({memory_mb}): "
            f'    data.append(array.array("B", [0] * 1024 * 1024)); '
            f"time.sleep({duration}); "
            f"del data",
        ]

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Injected memory leak: {memory_mb}MB for {duration}s")

    async def _inject_disk_io(self, fault: ChaosFault):
        """Inject disk I/O fault"""
        io_mb = fault.parameters.get("io_mb", 50)
        duration = fault.duration_seconds

        # Start disk I/O intensive process
        cmd = [
            "python",
            "-c",
            f"import time; import os; "
            f"for i in range({io_mb}): "
            f'    with open(f"temp_{{i}}.tmp", "w") as f: '
            f'        f.write("0" * 1024 * 1024); '
            f"time.sleep({duration}); "
            f"for i in range({io_mb}): "
            f'    try: os.remove(f"temp_{{i}}.tmp"); '
            f"    except: pass",
        ]

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Injected disk I/O: {io_mb}MB for {duration}s")

    async def _cleanup_fault_after_duration(self, fault: ChaosFault):
        """Clean up a fault after its duration expires"""
        await asyncio.sleep(fault.duration_seconds)

        if fault.name in self.active_faults:
            del self.active_faults[fault.name]
            FAULT_ACTIVE.labels(type=fault.fault_type).set(0)
            logger.info(f"Fault {fault.name} automatically cleaned up")

    async def _cleanup_network_fault_after_duration(self, duration: int):
        """Clean up network fault after duration"""
        await asyncio.sleep(duration)

        try:
            # Remove qdisc
            subprocess.run(["tc", "qdisc", "del", "dev", "lo", "root"], check=True)
            logger.info("Network fault cleaned up")
        except subprocess.CalledProcessError:
            logger.warning("Failed to cleanup network fault")

    async def _wait_for_completion(self):
        """Wait for test completion"""
        test_duration = timedelta(minutes=self.config.duration_minutes)
        start_time = datetime.now()

        while datetime.now() - start_time < test_duration:
            await asyncio.sleep(10)

            # Check if k6 has completed
            if self.k6_process and self.k6_process.poll() is not None:
                logger.info("k6 load testing completed")
                break

    async def _cleanup(self):
        """Clean up resources"""
        # Stop k6 process
        if self.k6_process and self.k6_process.poll() is None:
            self.k6_process.terminate()
            try:
                self.k6_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.k6_process.kill()

        # Cancel metrics collection
        if self.metrics_collector:
            self.metrics_collector.cancel()

        # Clean up active faults
        for fault_name in list(self.active_faults.keys()):
            await self._cleanup_fault_after_duration(self.active_faults[fault_name])

        # Clean up network faults
        try:
            subprocess.run(["tc", "qdisc", "del", "dev", "lo", "root"], check=False)
        except:
            pass

        logger.info("Chaos test cleanup completed")

    def _generate_test_results(self) -> TestResult:
        """Generate comprehensive test results"""
        fault_results = []
        for fault_name, fault in self.active_faults.items():
            fault_results.append(
                {
                    "name": fault_name,
                    "type": fault.fault_type,
                    "severity": fault.severity,
                    "parameters": fault.parameters,
                }
            )

        slo_results = []
        for violation in self.slo_violations:
            slo_results.append(violation)

        performance_metrics = {
            "total_faults": len(fault_results),
            "total_violations": len(slo_results),
            "backpressure_activations": BACKPRESSURE_ACTIVATIONS._value.sum(),
            "final_health_score": self.health_score,
        }

        return TestResult(
            test_id=self.config.test_id,
            start_time=self.test_start_time,
            end_time=self.test_end_time,
            total_faults_injected=len(fault_results),
            slo_violations=len(slo_results),
            backpressure_activations=performance_metrics["backpressure_activations"],
            system_health_score=self.health_score,
            fault_results=fault_results,
            slo_results=slo_results,
            performance_metrics=performance_metrics,
        )


def load_chaos_config(config_path: str) -> ChaosTest:
    """Load chaos test configuration from YAML file"""
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Parse faults
    faults = []
    for fault_data in config_data.get("faults", []):
        fault = ChaosFault(
            name=fault_data["name"],
            fault_type=fault_data["type"],
            severity=fault_data["severity"],
            duration_seconds=fault_data["duration_seconds"],
            probability=fault_data["probability"],
            parameters=fault_data.get("parameters", {}),
            slo_impact=fault_data.get("slo_impact", []),
        )
        faults.append(fault)

    # Parse SLO gates
    slo_gates = []
    for slo_data in config_data.get("slo_gates", []):
        slo = SLOGate(
            name=slo_data["name"],
            metric=slo_data["metric"],
            threshold=slo_data["threshold"],
            operator=slo_data["operator"],
            window_seconds=slo_data.get("window_seconds", 60),
            severity=slo_data["severity"],
            backpressure_trigger=slo_data.get("backpressure_trigger", False),
        )
        slo_gates.append(slo)

    return ChaosTest(
        test_id=str(uuid.uuid4()),
        name=config_data["name"],
        description=config_data.get("description", ""),
        duration_minutes=config_data["duration_minutes"],
        load_profile=config_data.get("load_profile", "ramp"),
        faults=faults,
        slo_gates=slo_gates,
        backpressure_config=config_data.get("backpressure_config", {}),
        k6_config=config_data.get("k6_config", {}),
    )


async def main():
    """Main function to run chaos testing"""
    # Load configuration
    config = load_chaos_config("testbed/chaos/chaos_config.yaml")

    # Create and run chaos runner
    runner = ChaosRunner(config)

    try:
        results = await runner.run_chaos_test()

        # Print summary
        print("\n" + "=" * 80)
        print("CHAOS TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Test ID: {results.test_id}")
        print(f"Duration: {results.end_time - results.start_time}")
        print(f"Total Faults Injected: {results.total_faults_injected}")
        print(f"SLO Violations: {results.slo_violations}")
        print(f"Backpressure Activations: {results.backpressure_activations}")
        print(f"Final Health Score: {results.system_health_score:.1f}")
        print("=" * 80)

        # Save results
        os.makedirs("testbed/results", exist_ok=True)
        with open(f"testbed/results/chaos_test_{results.test_id}.json", "w") as f:
            json.dump(asdict(results), f, indent=2, default=str)

    except Exception as e:
        logger.error(f"Chaos test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
