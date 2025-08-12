#!/usr/bin/env python3
"""
Cost & Performance Accounting System for Testbed
Tracks per-component timers, costs, and publishes performance per dollar metrics.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml
import aiohttp
import numpy as np
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import sqlite3
import os
import csv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics for cost accounting
COST_TOTAL = Counter(
    "cost_total_usd", "Total cost in USD", ["tenant", "component", "operation"]
)
PERFORMANCE_COST_RATIO = Gauge(
    "performance_cost_ratio",
    "Performance per dollar ratio",
    ["tenant", "component", "metric"],
)
COMPONENT_TIMING = Histogram(
    "component_timing_seconds",
    "Component execution time in seconds",
    ["tenant", "component", "operation"],
)
WEEKLY_DELTA = Gauge(
    "weekly_delta_percent",
    "Weekly performance delta percentage",
    ["tenant", "component", "metric"],
)


@dataclass
class ComponentTimer:
    """Timer for a specific component operation"""

    component_id: str
    component_name: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = None


@dataclass
class CostRecord:
    """Record of cost for a specific operation"""

    record_id: str
    tenant: str
    component: str
    operation: str
    cost_usd: float
    duration_ms: float
    timestamp: datetime
    performance_metric: str
    performance_value: float
    cost_performance_ratio: float
    metadata: Dict[str, Any] = None


@dataclass
class PerformanceMetric:
    """Performance metric with cost context"""

    metric_name: str
    value: float
    unit: str
    cost_usd: float
    cost_performance_ratio: float
    timestamp: datetime
    component: str
    tenant: str


@dataclass
class WeeklyDelta:
    """Weekly performance delta tracking"""

    week_start: datetime
    week_end: datetime
    tenant: str
    component: str
    metric: str
    previous_week_value: float
    current_week_value: float
    delta_percent: float
    trend: str  # "improving", "stable", "declining"


class CostAccountingSystem:
    """Main cost accounting system"""

    def __init__(self, config_path: str = "testbed/cost_perf/config.yaml"):
        self.config = self._load_config(config_path)
        self.db_path = "testbed/cost_perf/cost_accounting.db"
        self._init_database()

        # Initialize Prometheus metrics
        start_http_server(8003)
        logger.info("Cost accounting metrics server started on port 8003")

        # Component cost rates (USD per second)
        self.component_rates = self._load_component_rates()

        # Active timers
        self.active_timers: Dict[str, ComponentTimer] = {}

        # Weekly delta tracking
        self.weekly_deltas: Dict[str, WeeklyDelta] = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "component_rates": {
                "llm_inference": 0.001,  # $0.001 per second
                "data_retrieval": 0.0001,  # $0.0001 per second
                "computation": 0.0005,  # $0.0005 per second
                "storage": 0.00001,  # $0.00001 per second
                "network": 0.00005,  # $0.00005 per second
            },
            "performance_metrics": {
                "response_time": "seconds",
                "throughput": "requests_per_second",
                "accuracy": "percentage",
                "availability": "percentage",
            },
            "reporting": {
                "dashboard_update_interval": 60,  # seconds
                "weekly_delta_calculation": True,
                "cost_alert_thresholds": {
                    "high": 0.10,  # $0.10
                    "critical": 1.00,  # $1.00
                },
            },
        }

    def _init_database(self):
        """Initialize SQLite database for cost accounting"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS component_timers (
                timer_id TEXT PRIMARY KEY,
                component_id TEXT NOT NULL,
                component_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                duration_ms REAL,
                cost_usd REAL,
                metadata TEXT,
                timestamp TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_records (
                record_id TEXT PRIMARY KEY,
                tenant TEXT NOT NULL,
                component TEXT NOT NULL,
                operation TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                duration_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                performance_metric TEXT NOT NULL,
                performance_value REAL NOT NULL,
                cost_performance_ratio REAL NOT NULL,
                metadata TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                cost_performance_ratio REAL NOT NULL,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                tenant TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_deltas (
                delta_id TEXT PRIMARY KEY,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                tenant TEXT NOT NULL,
                component TEXT NOT NULL,
                metric TEXT NOT NULL,
                previous_week_value REAL NOT NULL,
                current_week_value REAL NOT NULL,
                delta_percent REAL NOT NULL,
                trend TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

        logger.info("Cost accounting database initialized")

    def _load_component_rates(self) -> Dict[str, float]:
        """Load component cost rates from configuration"""
        return self.config.get("component_rates", {})

    def start_component_timer(
        self,
        component_name: str,
        operation: str,
        tenant: str = "default",
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Start timing a component operation"""
        timer_id = str(uuid.uuid4())

        timer = ComponentTimer(
            component_id=timer_id,
            component_name=component_name,
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {},
        )

        self.active_timers[timer_id] = timer

        logger.debug(f"Started timer for {component_name}.{operation}")
        return timer_id

    def stop_component_timer(
        self,
        timer_id: str,
        performance_metric: str = None,
        performance_value: float = None,
    ) -> Optional[CostRecord]:
        """Stop timing a component operation and calculate cost"""
        if timer_id not in self.active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return None

        timer = self.active_timers[timer_id]
        timer.end_time = time.time()
        timer.duration_ms = (timer.end_time - timer.start_time) * 1000

        # Calculate cost based on component rate
        component_rate = self.component_rates.get(timer.component_name, 0.0)
        timer.cost_usd = (timer.duration_ms / 1000.0) * component_rate

        # Create cost record
        cost_record = CostRecord(
            record_id=str(uuid.uuid4()),
            tenant=timer.metadata.get("tenant", "default"),
            component=timer.component_name,
            operation=timer.operation,
            cost_usd=timer.cost_usd,
            duration_ms=timer.duration_ms,
            timestamp=datetime.now(),
            performance_metric=performance_metric or "duration",
            performance_value=performance_value or timer.duration_ms,
            cost_performance_ratio=(
                performance_value / timer.cost_usd if timer.cost_usd > 0 else 0.0
            ),
            metadata=timer.metadata,
        )

        # Save to database
        self._save_cost_record(cost_record)
        self._save_component_timer(timer)

        # Update Prometheus metrics
        self._update_metrics(cost_record)

        # Remove from active timers
        del self.active_timers[timer_id]

        logger.debug(
            f"Stopped timer for {timer.component_name}.{timer.operation}: "
            f"duration={timer.duration_ms:.2f}ms, cost=${timer.cost_usd:.6f}"
        )

        return cost_record

    def _save_cost_record(self, record: CostRecord):
        """Save cost record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cost_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.record_id,
                record.tenant,
                record.component,
                record.operation,
                record.cost_usd,
                record.duration_ms,
                record.timestamp.isoformat(),
                record.performance_metric,
                record.performance_value,
                record.cost_performance_ratio,
                json.dumps(record.metadata) if record.metadata else None,
            ),
        )

        conn.commit()
        conn.close()

    def _save_component_timer(self, timer: ComponentTimer):
        """Save component timer to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO component_timers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                timer.component_id,
                timer.component_id,
                timer.component_name,
                timer.operation,
                timer.start_time,
                timer.end_time,
                timer.duration_ms,
                timer.cost_usd,
                json.dumps(timer.metadata) if timer.metadata else None,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def _update_metrics(self, record: CostRecord):
        """Update Prometheus metrics"""
        # Update cost counter
        COST_TOTAL.labels(
            tenant=record.tenant, component=record.component, operation=record.operation
        ).inc(record.cost_usd)

        # Update component timing histogram
        COMPONENT_TIMING.labels(
            tenant=record.tenant, component=record.component, operation=record.operation
        ).observe(record.duration_ms / 1000.0)

        # Update performance-cost ratio gauge
        PERFORMANCE_COST_RATIO.labels(
            tenant=record.tenant,
            component=record.component,
            metric=record.performance_metric,
        ).set(record.cost_performance_ratio)

    async def record_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        cost_usd: float,
        component: str,
        tenant: str = "default",
        metadata: Dict[str, Any] = None,
    ):
        """Record a performance metric with cost context"""
        cost_performance_ratio = value / cost_usd if cost_usd > 0 else 0.0

        metric = PerformanceMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            cost_usd=cost_usd,
            cost_performance_ratio=cost_performance_ratio,
            timestamp=datetime.now(),
            component=component,
            tenant=tenant,
        )

        # Save to database
        self._save_performance_metric(metric)

        # Update weekly deltas
        await self._update_weekly_deltas(metric)

        logger.debug(
            f"Recorded performance metric: {metric_name}={value}{unit}, "
            f"cost=${cost_usd:.6f}, ratio={cost_performance_ratio:.2f}"
        )

    def _save_performance_metric(self, metric: PerformanceMetric):
        """Save performance metric to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO performance_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(uuid.uuid4()),
                metric.metric_name,
                metric.value,
                metric.unit,
                metric.cost_usd,
                metric.cost_performance_ratio,
                metric.timestamp.isoformat(),
                metric.component,
                metric.tenant,
            ),
        )

        conn.commit()
        conn.close()

    async def _update_weekly_deltas(self, metric: PerformanceMetric):
        """Update weekly delta tracking"""
        if not self.config.get("reporting", {}).get("weekly_delta_calculation", True):
            return

        # Calculate week boundaries
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        delta_key = f"{metric.tenant}_{metric.component}_{metric.metric_name}"

        if delta_key not in self.weekly_deltas:
            # Initialize delta tracking
            self.weekly_deltas[delta_key] = WeeklyDelta(
                week_start=week_start,
                week_end=week_end,
                tenant=metric.tenant,
                component=metric.component,
                metric=metric.metric_name,
                previous_week_value=metric.value,
                current_week_value=metric.value,
                delta_percent=0.0,
                trend="stable",
            )
        else:
            delta = self.weekly_deltas[delta_key]

            # Check if we've moved to a new week
            if now >= delta.week_end:
                # Move to new week
                delta.previous_week_value = delta.current_week_value
                delta.current_week_value = metric.value
                delta.week_start = week_start
                delta.week_end = week_end

                # Calculate delta percentage
                if delta.previous_week_value != 0:
                    delta.delta_percent = (
                        (delta.current_week_value - delta.previous_week_value)
                        / delta.previous_week_value
                        * 100
                    )
                else:
                    delta.delta_percent = 0.0

                # Determine trend
                if delta.delta_percent > 5.0:
                    delta.trend = "improving"
                elif delta.delta_percent < -5.0:
                    delta.trend = "declining"
                else:
                    delta.trend = "stable"

                # Save to database
                self._save_weekly_delta(delta)

                # Update Prometheus metrics
                WEEKLY_DELTA.labels(
                    tenant=delta.tenant, component=delta.component, metric=delta.metric
                ).set(delta.delta_percent)

                logger.info(
                    f"Weekly delta for {delta.component}.{delta.metric}: "
                    f"{delta.delta_percent:+.1f}% ({delta.trend})"
                )
            else:
                # Update current week value (running average)
                delta.current_week_value = (delta.current_week_value + metric.value) / 2

    def _save_weekly_delta(self, delta: WeeklyDelta):
        """Save weekly delta to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO weekly_deltas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f"{delta.tenant}_{delta.component}_{delta.metric}_{delta.week_start.isoformat()}",
                delta.week_start.isoformat(),
                delta.week_end.isoformat(),
                delta.tenant,
                delta.component,
                delta.metric,
                delta.previous_week_value,
                delta.current_week_value,
                delta.delta_percent,
                delta.trend,
            ),
        )

        conn.commit()
        conn.close()

    async def generate_cost_dashboard(
        self, tenant: str = None, time_range: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Generate cost dashboard data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query with filters
            query = "SELECT * FROM cost_records WHERE 1=1"
            params = []

            if tenant:
                query += " AND tenant = ?"
                params.append(tenant)

            if time_range:
                cutoff_time = datetime.now() - time_range
                query += " AND timestamp > ?"
                params.append(cutoff_time.isoformat())

            cursor.execute(query, params)
            records = cursor.fetchall()

            # Process results
            dashboard = {
                "total_cost": 0.0,
                "total_operations": len(records),
                "cost_by_component": {},
                "cost_by_operation": {},
                "performance_cost_ratios": {},
                "cost_trends": [],
                "top_cost_components": [],
                "cost_alerts": [],
            }

            if records:
                # Calculate totals
                costs = [row[4] for row in records]
                dashboard["total_cost"] = sum(costs)

                # Cost by component
                for row in records:
                    component = row[2]
                    cost = row[4]
                    dashboard["cost_by_component"][component] = (
                        dashboard["cost_by_component"].get(component, 0.0) + cost
                    )

                # Cost by operation
                for row in records:
                    operation = row[3]
                    cost = row[4]
                    dashboard["cost_by_operation"][operation] = (
                        dashboard["cost_by_operation"].get(operation, 0.0) + cost
                    )

                # Performance-cost ratios
                for row in records:
                    metric = row[7]
                    ratio = row[9]
                    if metric not in dashboard["performance_cost_ratios"]:
                        dashboard["performance_cost_ratios"][metric] = []
                    dashboard["performance_cost_ratios"][metric].append(ratio)

                # Calculate averages for ratios
                for metric, ratios in dashboard["performance_cost_ratios"].items():
                    dashboard["performance_cost_ratios"][metric] = {
                        "average": sum(ratios) / len(ratios),
                        "min": min(ratios),
                        "max": max(ratios),
                        "count": len(ratios),
                    }

                # Top cost components
                component_costs = list(dashboard["cost_by_component"].items())
                component_costs.sort(key=lambda x: x[1], reverse=True)
                dashboard["top_cost_components"] = component_costs[:5]

                # Cost alerts
                alert_thresholds = self.config.get("reporting", {}).get(
                    "cost_alert_thresholds", {}
                )
                for component, cost in dashboard["cost_by_component"].items():
                    if cost > alert_thresholds.get("critical", 1.0):
                        dashboard["cost_alerts"].append(
                            {
                                "level": "critical",
                                "component": component,
                                "cost": cost,
                                "threshold": alert_thresholds.get("critical", 1.0),
                            }
                        )
                    elif cost > alert_thresholds.get("high", 0.1):
                        dashboard["cost_alerts"].append(
                            {
                                "level": "high",
                                "component": component,
                                "cost": cost,
                                "threshold": alert_thresholds.get("high", 0.1),
                            }
                        )

            conn.close()
            return dashboard

        except Exception as e:
            logger.error(f"Failed to generate cost dashboard: {e}")
            return {}

    async def export_cost_data(
        self,
        format: str = "json",
        tenant: str = None,
        time_range: timedelta = timedelta(days=7),
    ) -> str:
        """Export cost data in specified format"""
        try:
            dashboard = await self.generate_cost_dashboard(tenant, time_range)

            if format == "json":
                return json.dumps(dashboard, indent=2, default=str)
            elif format == "csv":
                return self._convert_dashboard_to_csv(dashboard)
            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Failed to export cost data: {e}")
            return ""

    def _convert_dashboard_to_csv(self, dashboard: Dict[str, Any]) -> str:
        """Convert dashboard data to CSV format"""
        csv_lines = []

        # Summary metrics
        csv_lines.append("Metric,Value")
        csv_lines.append(f"Total Cost (USD),{dashboard.get('total_cost', 0.0):.6f}")
        csv_lines.append(f"Total Operations,{dashboard.get('total_operations', 0)}")

        # Cost by component
        csv_lines.append("")
        csv_lines.append("Component,Cost (USD)")
        for component, cost in dashboard.get("cost_by_component", {}).items():
            csv_lines.append(f"{component},{cost:.6f}")

        # Cost by operation
        csv_lines.append("")
        csv_lines.append("Operation,Cost (USD)")
        for operation, cost in dashboard.get("cost_by_operation", {}).items():
            csv_lines.append(f"{operation},{cost:.6f}")

        # Performance-cost ratios
        csv_lines.append("")
        csv_lines.append("Metric,Average,Min,Max,Count")
        for metric, data in dashboard.get("performance_cost_ratios", {}).items():
            csv_lines.append(
                f"{metric},"
                f"{data['average']:.2f},"
                f"{data['min']:.2f},"
                f"{data['max']:.2f},"
                f"{data['count']}"
            )

        # Cost alerts
        csv_lines.append("")
        csv_lines.append("Alert Level,Component,Cost (USD),Threshold")
        for alert in dashboard.get("cost_alerts", []):
            csv_lines.append(
                f"{alert['level']},"
                f"{alert['component']},"
                f"{alert['cost']:.6f},"
                f"{alert['threshold']:.6f}"
            )

        return "\n".join(csv_lines)

    def get_component_headers(self, tenant: str = "default") -> Dict[str, str]:
        """Get component timing headers for HTTP responses"""
        headers = {}

        # Add active timer information
        for timer_id, timer in self.active_timers.items():
            if timer.metadata.get("tenant") == tenant:
                elapsed_ms = (time.time() - timer.start_time) * 1000
                headers[f"X-{timer.component_name}-{timer.operation}-Elapsed"] = (
                    f"{elapsed_ms:.2f}ms"
                )

        # Add cost information
        total_cost = sum(
            t.cost_usd
            for t in self.active_timers.values()
            if t.metadata.get("tenant") == tenant
        )
        if total_cost > 0:
            headers["X-Total-Cost-USD"] = f"{total_cost:.6f}"

        return headers


async def main():
    """Main function to demonstrate cost accounting"""
    # Create cost accounting system
    cost_system = CostAccountingSystem()

    # Simulate component operations
    print("Simulating component operations for cost accounting...")

    # Simulate LLM inference
    llm_timer = cost_system.start_component_timer(
        component_name="llm_inference",
        operation="text_generation",
        tenant="test-tenant",
        metadata={"model": "gpt-4", "tokens": 150},
    )

    await asyncio.sleep(2)  # Simulate processing time

    llm_record = cost_system.stop_component_timer(
        llm_timer, performance_metric="tokens_per_second", performance_value=75.0
    )

    # Simulate data retrieval
    retrieval_timer = cost_system.start_component_timer(
        component_name="data_retrieval",
        operation="vector_search",
        tenant="test-tenant",
        metadata={"index": "documents", "query_type": "semantic"},
    )

    await asyncio.sleep(0.5)  # Simulate processing time

    retrieval_record = cost_system.stop_component_timer(
        retrieval_timer,
        performance_metric="results_per_second",
        performance_value=200.0,
    )

    # Simulate computation
    comp_timer = cost_system.start_component_timer(
        component_name="computation",
        operation="matrix_multiplication",
        tenant="test-tenant",
        metadata={"matrix_size": "1000x1000", "precision": "float64"},
    )

    await asyncio.sleep(1)  # Simulate processing time

    comp_record = cost_system.stop_component_timer(
        comp_timer,
        performance_metric="operations_per_second",
        performance_value=1000000.0,
    )

    # Record performance metrics
    await cost_system.record_performance_metric(
        metric_name="response_time",
        value=3.5,
        unit="seconds",
        cost_usd=llm_record.cost_usd + retrieval_record.cost_usd + comp_record.cost_usd,
        component="pipeline",
        tenant="test-tenant",
    )

    # Generate and display dashboard
    print("\nGenerating cost dashboard...")
    dashboard = await cost_system.generate_cost_dashboard()

    print("\n" + "=" * 80)
    print("COST DASHBOARD")
    print("=" * 80)
    print(f"Total Cost: ${dashboard.get('total_cost', 0.0):.6f}")
    print(f"Total Operations: {dashboard.get('total_operations', 0)}")

    print("\nCost by Component:")
    for component, cost in dashboard.get("cost_by_component", {}).items():
        print(f"  {component}: ${cost:.6f}")

    print("\nPerformance-Cost Ratios:")
    for metric, data in dashboard.get("performance_cost_ratios", {}).items():
        print(f"  {metric}: {data['average']:.2f} (avg)")

    # Export data
    print("\nExporting cost data...")
    csv_data = await cost_system.export_cost_data(format="csv")

    # Save to file
    os.makedirs("testbed/results", exist_ok=True)
    with open("testbed/results/cost_dashboard.csv", "w") as f:
        f.write(csv_data)

    print("Cost dashboard saved to testbed/results/cost_dashboard.csv")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
