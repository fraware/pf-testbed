#!/usr/bin/env python3
"""
Traffic Runner for TB-SCEN
Simulates various traffic patterns for reproducible workload testing
"""

import json
import time
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrafficPattern:
    """Defines a traffic pattern configuration"""

    name: str
    pattern_type: str  # ramp, burst, diurnal, constant, random
    duration_minutes: int
    target_rps: float  # requests per second
    ramp_up_minutes: Optional[int] = None
    ramp_down_minutes: Optional[int] = None
    burst_size: Optional[int] = None
    burst_interval_seconds: Optional[float] = None
    diurnal_peak_hour: Optional[int] = None
    diurnal_peak_multiplier: Optional[float] = None


@dataclass
class JourneyConfig:
    """Configuration for a user journey"""

    name: str
    inputs: Dict[str, Any]
    allowed_tools: List[str]
    sla_seconds: float
    hazard_tags: List[str]
    weight: float = 1.0  # Relative frequency


@dataclass
class TrafficRun:
    """Represents a complete traffic run"""

    run_id: str
    start_time: datetime
    end_time: Optional[datetime]
    patterns: List[TrafficPattern]
    journeys: List[JourneyConfig]
    total_requests: int
    successful_requests: int
    failed_requests: int
    performance_metrics: Dict[str, Any]
    seed: str


class TrafficRunner:
    """Main traffic runner for simulating workloads"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = (
            Path(config_path) if config_path else Path("testbed/scenarios")
        )
        self.journeys: List[JourneyConfig] = []
        self.patterns: List[TrafficPattern] = []
        self.current_run: Optional[TrafficRun] = None
        self.performance_history: List[Dict[str, Any]] = []
        self.seed: Optional[str] = None

        # Load configuration
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load journey and traffic pattern configurations"""
        # Load user journeys
        journeys_file = self.config_path / "user_journeys.yaml"
        if journeys_file.exists():
            with open(journeys_file, "r") as f:
                journeys_data = yaml.safe_load(f)
                self.journeys = [
                    JourneyConfig(**journey)
                    for journey in journeys_data.get("journeys", [])
                ]
                logger.info(f"Loaded {len(self.journeys)} journey configurations")

        # Load traffic patterns
        patterns_file = self.config_path / "traffic_patterns.yaml"
        if patterns_file.exists():
            with open(patterns_file, "r") as f:
                patterns_data = yaml.safe_load(f)
                self.patterns = [
                    TrafficPattern(**pattern)
                    for pattern in patterns_data.get("patterns", [])
                ]
                logger.info(f"Loaded {len(self.patterns)} traffic patterns")

    def set_seed(self, seed: str) -> None:
        """Set the random seed for reproducible runs"""
        self.seed = seed
        random.seed(seed)
        logger.info(f"Set traffic run seed to: {seed}")

    def generate_seed(self) -> str:
        """Generate a new random seed"""
        self.seed = f"traffic_{int(time.time())}_{random.randint(1000, 9999)}"
        random.seed(self.seed)
        return self.seed

    async def run_traffic_pattern(
        self, pattern: TrafficPattern, journey_executor: Callable
    ) -> Dict[str, Any]:
        """Run a single traffic pattern"""
        logger.info(f"Starting traffic pattern: {pattern.name}")

        start_time = datetime.utcnow()
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        response_times: List[float] = []

        if pattern.pattern_type == "ramp":
            await self._run_ramp_pattern(
                pattern,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )
        elif pattern.pattern_type == "burst":
            await self._run_burst_pattern(
                pattern,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )
        elif pattern.pattern_type == "diurnal":
            await self._run_diurnal_pattern(
                pattern,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )
        elif pattern.pattern_type == "constant":
            await self._run_constant_pattern(
                pattern,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )
        else:
            raise ValueError(f"Unknown pattern type: {pattern.pattern_type}")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(
            response_times, successful_requests, failed_requests, duration
        )

        return {
            "pattern_name": pattern.name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "performance_metrics": metrics,
        }

    async def _run_ramp_pattern(
        self,
        pattern: TrafficPattern,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Run a ramp-up/ramp-down pattern"""
        duration = pattern.duration_minutes * 60  # Convert to seconds
        ramp_up = (
            pattern.ramp_up_minutes * 60 if pattern.ramp_up_minutes else duration / 3
        )
        ramp_down = (
            pattern.ramp_down_minutes * 60
            if pattern.ramp_down_minutes
            else duration / 3
        )
        steady_state = duration - ramp_up - ramp_down

        # Ramp up phase
        if ramp_up > 0:
            await self._ramp_phase(
                ramp_up,
                0,
                pattern.target_rps,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

        # Steady state phase
        if steady_state > 0:
            await self._steady_phase(
                steady_state,
                pattern.target_rps,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

        # Ramp down phase
        if ramp_down > 0:
            await self._ramp_phase(
                ramp_down,
                pattern.target_rps,
                0,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

    async def _run_burst_pattern(
        self,
        pattern: TrafficPattern,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Run a burst pattern"""
        duration = pattern.duration_minutes * 60
        burst_size = pattern.burst_size or 10
        interval = pattern.burst_interval_seconds or 1.0

        start_time = time.time()
        while time.time() - start_time < duration:
            # Execute burst
            burst_tasks = []
            for _ in range(burst_size):
                task = asyncio.create_task(
                    self._execute_journey(
                        journey_executor,
                        response_times,
                        total_requests,
                        successful_requests,
                        failed_requests,
                    )
                )
                burst_tasks.append(task)

            # Wait for burst to complete
            await asyncio.gather(*burst_tasks)

            # Wait for next burst
            await asyncio.sleep(interval)

    async def _run_diurnal_pattern(
        self,
        pattern: TrafficPattern,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Run a diurnal (daily cycle) pattern"""
        duration = pattern.duration_minutes * 60
        peak_hour = pattern.diurnal_peak_hour or 14  # 2 PM
        peak_multiplier = pattern.diurnal_peak_multiplier or 3.0

        start_time = time.time()
        while time.time() - start_time < duration:
            current_time = datetime.utcnow()
            current_hour = current_time.hour

            # Calculate current RPS based on time of day
            if current_hour == peak_hour:
                current_rps = pattern.target_rps * peak_multiplier
            else:
                # Simple sine wave approximation for diurnal pattern
                hour_diff = abs(current_hour - peak_hour)
                if hour_diff > 12:
                    hour_diff = 24 - hour_diff

                # Cosine function to create smooth transitions
                multiplier = 1.0 + (peak_multiplier - 1.0) * (1 - hour_diff / 12)
                current_rps = pattern.target_rps * multiplier

            # Execute requests at current RPS
            await self._execute_at_rps(
                current_rps,
                1.0,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

    async def _run_constant_pattern(
        self,
        pattern: TrafficPattern,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Run a constant rate pattern"""
        duration = pattern.duration_minutes * 60
        await self._steady_phase(
            duration,
            pattern.target_rps,
            journey_executor,
            response_times,
            total_requests,
            successful_requests,
            failed_requests,
        )

    async def _ramp_phase(
        self,
        duration: float,
        start_rps: float,
        end_rps: float,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Execute a ramp phase"""
        start_time = time.time()
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            progress = elapsed / duration

            # Linear interpolation between start and end RPS
            current_rps = start_rps + (end_rps - start_rps) * progress

            await self._execute_at_rps(
                current_rps,
                1.0,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

    async def _steady_phase(
        self,
        duration: float,
        target_rps: float,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Execute a steady state phase"""
        start_time = time.time()
        while time.time() - start_time < duration:
            await self._execute_at_rps(
                target_rps,
                1.0,
                journey_executor,
                response_times,
                total_requests,
                successful_requests,
                failed_requests,
            )

    async def _execute_at_rps(
        self,
        target_rps: float,
        duration: float,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Execute requests at a target RPS for a duration"""
        if target_rps <= 0:
            return

        interval = 1.0 / target_rps
        start_time = time.time()

        while time.time() - start_time < duration:
            task = asyncio.create_task(
                self._execute_journey(
                    journey_executor,
                    response_times,
                    total_requests,
                    successful_requests,
                    failed_requests,
                )
            )

            # Wait for next request interval
            await asyncio.sleep(interval)

    async def _execute_journey(
        self,
        journey_executor: Callable,
        response_times: List[float],
        total_requests: int,
        successful_requests: int,
        failed_requests: int,
    ) -> None:
        """Execute a single journey and record metrics"""
        start_time = time.time()

        try:
            # Select random journey based on weights
            journey = self._select_journey()

            # Execute journey
            result = await journey_executor(journey)

            # Record metrics
            response_time = time.time() - start_time
            response_times.append(response_time)
            total_requests += 1

            if result.get("success", False):
                successful_requests += 1
            else:
                failed_requests += 1

        except Exception as e:
            logger.error(f"Journey execution failed: {e}")
            failed_requests += 1
            total_requests += 1

    def _select_journey(self) -> JourneyConfig:
        """Select a journey based on weights"""
        if not self.journeys:
            raise ValueError("No journeys configured")

        # Calculate total weight
        total_weight = sum(journey.weight for journey in self.journeys)

        # Random selection based on weights
        rand_val = random.uniform(0, total_weight)
        current_weight = 0

        for journey in self.journeys:
            current_weight += journey.weight
            if rand_val <= current_weight:
                return journey

        return self.journeys[-1]  # Fallback

    def _calculate_performance_metrics(
        self,
        response_times: List[float],
        successful_requests: int,
        failed_requests: int,
        duration: float,
    ) -> Dict[str, Any]:
        """Calculate performance metrics from response times"""
        if not response_times:
            return {
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "throughput": 0,
                "error_rate": 0,
            }

        sorted_times = sorted(response_times)
        total_requests = successful_requests + failed_requests

        metrics = {
            "p50": sorted_times[int(len(sorted_times) * 0.5)],
            "p95": sorted_times[int(len(sorted_times) * 0.95)],
            "p99": sorted_times[int(len(sorted_times) * 0.99)],
            "mean": statistics.mean(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "throughput": total_requests / duration if duration > 0 else 0,
            "error_rate": failed_requests / total_requests if total_requests > 0 else 0,
        }

        return metrics

    async def run_soak_test(
        self,
        duration_minutes: int = 30,
        target_rps: float = 10.0,
        journey_executor: Callable = None,
    ) -> TrafficRun:
        """Run a soak test with performance gates"""
        logger.info(f"Starting {duration_minutes}-minute soak test at {target_rps} RPS")

        # Generate run ID and seed
        run_id = f"soak_{int(time.time())}"
        if not self.seed:
            self.generate_seed()

        # Create soak test pattern
        soak_pattern = TrafficPattern(
            name="soak_test",
            pattern_type="constant",
            duration_minutes=duration_minutes,
            target_rps=target_rps,
        )

        # Initialize run
        self.current_run = TrafficRun(
            run_id=run_id,
            start_time=datetime.utcnow(),
            end_time=None,
            patterns=[soak_pattern],
            journeys=self.journeys,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            performance_metrics={},
            seed=self.seed,
        )

        # Execute soak test
        pattern_result = await self.run_traffic_pattern(soak_pattern, journey_executor)

        # Complete run
        self.current_run.end_time = datetime.utcnow()
        self.current_run.total_requests = pattern_result["total_requests"]
        self.current_run.successful_requests = pattern_result["successful_requests"]
        self.current_run.failed_requests = pattern_result["failed_requests"]
        self.current_run.performance_metrics = pattern_result["performance_metrics"]

        # Check performance gates
        gates_passed = self._check_performance_gates(
            pattern_result["performance_metrics"]
        )

        logger.info(f"Soak test completed. Gates passed: {gates_passed}")

        # Save run results
        self._save_run_results()

        return self.current_run

    def _check_performance_gates(self, metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Check performance gates against SLOs"""
        gates = {
            "p95_latency": metrics["p95"] < 2.0,  # p95 < 2.0s
            "p99_latency": metrics["p99"] < 4.0,  # p99 < 4.0s
            "error_rate": metrics["error_rate"] < 0.01,  # < 1% errors
            "throughput": metrics["throughput"] > 0,  # Positive throughput
        }

        return gates

    def _save_run_results(self) -> None:
        """Save run results to file"""
        if not self.current_run:
            return

        results_dir = self.config_path / "results"
        results_dir.mkdir(exist_ok=True)

        results_file = results_dir / f"traffic_run_{self.current_run.run_id}.json"

        # Convert run to dict
        run_dict = asdict(self.current_run)
        run_dict["start_time"] = self.current_run.start_time.isoformat()
        if self.current_run.end_time:
            run_dict["end_time"] = self.current_run.end_time.isoformat()

        with open(results_file, "w") as f:
            json.dump(run_dict, f, indent=2)

        logger.info(f"Saved run results to {results_file}")

    def get_run_summary(self) -> Dict[str, Any]:
        """Get summary of the current run"""
        if not self.current_run:
            return {}

        return {
            "run_id": self.current_run.run_id,
            "start_time": self.current_run.start_time.isoformat(),
            "end_time": (
                self.current_run.end_time.isoformat()
                if self.current_run.end_time
                else None
            ),
            "duration_minutes": (
                (
                    self.current_run.end_time - self.current_run.start_time
                ).total_seconds()
                / 60
                if self.current_run.end_time
                else 0
            ),
            "total_requests": self.current_run.total_requests,
            "successful_requests": self.current_run.successful_requests,
            "failed_requests": self.current_run.failed_requests,
            "success_rate": (
                self.current_run.successful_requests / self.current_run.total_requests
                if self.current_run.total_requests > 0
                else 0
            ),
            "performance_metrics": self.current_run.performance_metrics,
            "seed": self.current_run.seed,
        }


# Example journey executor function
async def example_journey_executor(journey: JourneyConfig) -> Dict[str, Any]:
    """Example function to execute a journey"""
    # Simulate journey execution
    await asyncio.sleep(random.uniform(0.1, 2.0))  # Random execution time

    # Simulate occasional failures
    if random.random() < 0.05:  # 5% failure rate
        return {"success": False, "error": "Simulated failure"}

    return {"success": True, "result": "Journey completed successfully"}


def main():
    """Example usage of the TrafficRunner"""

    # Initialize traffic runner
    runner = TrafficRunner()

    # Set seed for reproducibility
    seed = runner.generate_seed()
    print(f"Generated seed: {seed}")

    # Run soak test
    async def run_example():
        try:
            run_result = await runner.run_soak_test(
                duration_minutes=5,  # 5 minutes for demo
                target_rps=5.0,  # 5 requests per second
                journey_executor=example_journey_executor,
            )

            # Get summary
            summary = runner.get_run_summary()
            print("\nTraffic Run Summary:")
            print(json.dumps(summary, indent=2))

        except Exception as e:
            logger.error(f"Traffic run failed: {e}")
            raise

    # Run the example
    asyncio.run(run_example())


if __name__ == "__main__":
    main()

