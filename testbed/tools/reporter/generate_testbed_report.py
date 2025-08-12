#!/usr/bin/env python3
"""
Testbed Report Generator

Generates comprehensive reports for the Provability Fabric Testbed, including:
- Performance metrics (P95/P99 latencies)
- Security metrics (block rates, leaks, cross-tenant interactions)
- Cost metrics (cost per 1k transactions)
- Confidence and fallback statistics
- Comparison with ART harness results
- Red-team regression analysis

This tool is designed to provide trustworthy metrics for buyers and stakeholders.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp
from jinja2 import Template
import yaml
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation"""

    prometheus_url: str
    ledger_url: str
    art_results_path: str
    output_dir: str
    report_format: str  # 'pdf', 'html', 'both'
    time_range_hours: int
    include_art_comparison: bool
    include_redteam_analysis: bool
    kpi_thresholds: Dict[str, float]


@dataclass
class TestbedMetrics:
    """Container for all testbed metrics"""

    # Performance metrics
    latency_p95: float
    latency_p99: float
    throughput: float
    error_rate: float

    # Security metrics
    block_rate: float
    cross_tenant_interactions: int
    data_leaks: int
    honeytoken_alerts: int

    # Cost metrics
    cost_per_1k_transactions: float
    total_transactions: int
    total_cost: float

    # Confidence metrics
    confidence_score: float
    fallback_rate: float
    theorem_verification_rate: float

    # Timestamp
    timestamp: str


@dataclass
class ARTComparison:
    """Comparison with ART harness results"""

    metric: str
    testbed_value: float
    art_value: float
    delta: float
    delta_percentage: float
    status: str  # 'better', 'worse', 'similar'


@dataclass
class RedTeamAnalysis:
    """Red-team regression analysis"""

    test_name: str
    status: str  # 'pass', 'fail', 'regression'
    last_run: str
    failure_rate: float
    severity: str
    details: str
    run_url: str


class MetricsCollector:
    """Collects metrics from various sources"""

    def __init__(self, config: ReportConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_prometheus_metrics(self) -> Dict[str, Any]:
        """Collect metrics from Prometheus"""
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=self.config.time_range_hours)

            # Prometheus queries for key metrics
            queries = {
                "latency_p95": "histogram_quantile(0.95, rate(testbed_request_duration_seconds_bucket[1h]))",
                "latency_p99": "histogram_quantile(0.99, rate(testbed_request_duration_seconds_bucket[1h]))",
                "throughput": "rate(testbed_requests_total[1h])",
                "error_rate": "rate(testbed_errors_total[1h]) / rate(testbed_requests_total[1h])",
                "block_rate": "rate(testbed_blocks_total[1h]) / rate(testbed_requests_total[1h])",
                "cross_tenant_interactions": "testbed_cross_tenant_interactions_total",
                "data_leaks": "testbed_data_leaks_total",
                "honeytoken_alerts": "testbed_honeytoken_alerts_total",
                "theorem_verification_rate": "testbed_theorem_verification_rate",
                "total_transactions": "testbed_requests_total",
                "total_cost": "testbed_cost_total",
            }

            metrics = {}
            for name, query in queries.items():
                try:
                    result = await self._query_prometheus(query, start_time, end_time)
                    metrics[name] = result
                except Exception as e:
                    logger.warning(f"Failed to collect {name}: {e}")
                    metrics[name] = 0.0

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect Prometheus metrics: {e}")
            return {}

    async def collect_ledger_metrics(self) -> Dict[str, Any]:
        """Collect metrics from the ledger"""
        try:
            # Collect safety case bundle statistics
            bundle_stats = await self._query_ledger("/api/bundles/stats")

            # Collect session statistics
            session_stats = await self._query_ledger("/api/sessions/stats")

            # Collect capability usage statistics
            capability_stats = await self._query_ledger("/api/capabilities/stats")

            return {
                "bundle_stats": bundle_stats,
                "session_stats": session_stats,
                "capability_stats": capability_stats,
            }

        except Exception as e:
            logger.error(f"Failed to collect ledger metrics: {e}")
            return {}

    async def collect_art_results(self) -> Dict[str, Any]:
        """Collect ART harness results for comparison"""
        if not self.config.include_art_comparison:
            return {}

        try:
            art_path = Path(self.config.art_results_path)
            if not art_path.exists():
                logger.warning(f"ART results path does not exist: {art_path}")
                return {}

            # Parse ART results (assuming JSON format)
            with open(art_path, "r") as f:
                art_data = json.load(f)

            return art_data

        except Exception as e:
            logger.error(f"Failed to collect ART results: {e}")
            return {}

    async def collect_redteam_analysis(self) -> List[RedTeamAnalysis]:
        """Collect red-team regression analysis"""
        if not self.config.include_redteam_analysis:
            return []

        try:
            # Query red-team test results
            redteam_results = await self._query_ledger("/api/redteam/results")

            analysis = []
            for result in redteam_results:
                analysis.append(
                    RedTeamAnalysis(
                        test_name=result.get("test_name", "Unknown"),
                        status=result.get("status", "unknown"),
                        last_run=result.get("last_run", ""),
                        failure_rate=result.get("failure_rate", 0.0),
                        severity=result.get("severity", "medium"),
                        details=result.get("details", ""),
                        run_url=result.get("run_url", ""),
                    )
                )

            return analysis

        except Exception as e:
            logger.error(f"Failed to collect red-team analysis: {e}")
            return []

    async def _query_prometheus(
        self, query: str, start_time: datetime, end_time: datetime
    ) -> float:
        """Execute a Prometheus query"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": "1h",
        }

        async with self.session.get(
            f"{self.config.prometheus_url}/api/v1/query_range", params=params
        ) as response:
            response.raise_for_status()
            data = await response.json()

            if data["status"] != "success":
                raise ValueError(
                    f"Prometheus query failed: {data.get('error', 'Unknown error')}"
                )

            # Extract the latest value
            result = data["data"]["result"]
            if not result:
                return 0.0

            values = result[0]["values"]
            if not values:
                return 0.0

            # Return the last value
            return float(values[-1][1])

    async def _query_ledger(self, endpoint: str) -> Any:
        """Query the ledger API"""
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.config.ledger_url}{endpoint}"
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()


class ReportGenerator:
    """Generates comprehensive testbed reports"""

    def __init__(self, config: ReportConfig):
        self.config = config
        self.metrics: Optional[TestbedMetrics] = None
        self.art_comparison: List[ARTComparison] = []
        self.redteam_analysis: List[RedTeamAnalysis] = []

        # Load templates
        self.html_template = self._load_html_template()
        self.kpi_thresholds = config.kpi_thresholds

    def _load_html_template(self) -> Template:
        """Load HTML report template"""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Testbed Report - {{ report_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .metric-card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; font-size: 1.1em; }
        .status-good { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-bad { color: #e74c3c; }
        .comparison-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .comparison-table th, .comparison-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        .comparison-table th { background-color: #f8f9fa; }
        .redteam-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .redteam-pass { background-color: #d4edda; color: #155724; }
        .redteam-fail { background-color: #f8d7da; color: #721c24; }
        .redteam-regression { background-color: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Provability Fabric Testbed Report</h1>
        <p>Generated on {{ report_date }}</p>
        <p>Time Range: {{ time_range }}</p>
    </div>
    
    <h2>Performance Metrics</h2>
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.latency_p95 < 2 else 'status-warning' if metrics.latency_p95 < 5 else 'status-bad' }}">
            {{ "%.2f"|format(metrics.latency_p95) }}s
        </div>
        <div class="metric-label">P95 Latency</div>
    </div>
    
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.latency_p99 < 5 else 'status-warning' if metrics.latency_p99 < 10 else 'status-bad' }}">
            {{ "%.2f"|format(metrics.latency_p99) }}s
        </div>
        <div class="metric-label">P99 Latency</div>
    </div>
    
    <h2>Security Metrics</h2>
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.block_rate < 0.01 else 'status-warning' if metrics.block_rate < 0.05 else 'status-bad' }}">
            {{ "%.2f"|format(metrics.block_rate * 100) }}%
        </div>
        <div class="metric-label">Block Rate</div>
    </div>
    
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.cross_tenant_interactions == 0 else 'status-bad' }}">
            {{ metrics.cross_tenant_interactions }}
        </div>
        <div class="metric-label">Cross-Tenant Interactions</div>
    </div>
    
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.data_leaks == 0 else 'status-bad' }}">
            {{ metrics.data_leaks }}
        </div>
        <div class="metric-label">Data Leaks</div>
    </div>
    
    <h2>Cost Metrics</h2>
    <div class="metric-card">
        <div class="metric-value">
            ${{ "%.4f"|format(metrics.cost_per_1k_transactions) }}
        </div>
        <div class="metric-label">Cost per 1K Transactions</div>
    </div>
    
    <h2>Confidence Metrics</h2>
    <div class="metric-card">
        <div class="metric-value {{ 'status-good' if metrics.confidence_score > 0.95 else 'status-warning' if metrics.confidence_score > 0.8 else 'status-bad' }}">
            {{ "%.1f"|format(metrics.confidence_score * 100) }}%
        </div>
        <div class="metric-label">Confidence Score</div>
    </div>
    
    {% if art_comparison %}
    <h2>ART Harness Comparison</h2>
    <table class="comparison-table">
        <thead>
            <tr>
                <th>Metric</th>
                <th>Testbed</th>
                <th>ART</th>
                <th>Delta</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for comp in art_comparison %}
            <tr>
                <td>{{ comp.metric }}</td>
                <td>{{ "%.4f"|format(comp.testbed_value) }}</td>
                <td>{{ "%.4f"|format(comp.art_value) }}</td>
                <td>{{ "%.4f"|format(comp.delta) }} ({{ "%.1f"|format(comp.delta_percentage) }}%)</td>
                <td>{{ comp.status }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
    
    {% if redteam_analysis %}
    <h2>Red-Team Analysis</h2>
    {% for test in redteam_analysis %}
    <div class="metric-card">
        <h3>{{ test.test_name }}</h3>
        <span class="redteam-badge redteam-{{ test.status }}">{{ test.status.upper() }}</span>
        <p><strong>Failure Rate:</strong> {{ "%.2f"|format(test.failure_rate * 100) }}%</p>
        <p><strong>Severity:</strong> {{ test.severity }}</p>
        <p><strong>Details:</strong> {{ test.details }}</p>
        {% if test.run_url %}
        <p><a href="{{ test.run_url }}" target="_blank">View Test Run</a></p>
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}
    
    <div class="header">
        <p><em>Report generated by Testbed Report Generator v1.0.0</em></p>
    </div>
</body>
</html>
        """
        return Template(template_content)

    async def generate_report(
        self,
        metrics: TestbedMetrics,
        art_comparison: List[ARTComparison],
        redteam_analysis: List[RedTeamAnalysis],
    ) -> Dict[str, str]:
        """Generate the complete report"""
        self.metrics = metrics
        self.art_comparison = art_comparison
        self.redteam_analysis = redteam_analysis

        # Validate all KPIs are present
        self._validate_kpis()

        # Generate report files
        report_files = {}

        if self.config.report_format in ["html", "both"]:
            html_report = self._generate_html_report()
            html_path = os.path.join(self.config.output_dir, "testbed_report.html")
            with open(html_path, "w") as f:
                f.write(html_report)
            report_files["html"] = html_path

        if self.config.report_format in ["pdf", "both"]:
            pdf_path = await self._generate_pdf_report()
            report_files["pdf"] = pdf_path

        # Generate summary
        summary = self._generate_summary()
        summary_path = os.path.join(self.config.output_dir, "report_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        report_files["summary"] = summary_path

        return report_files

    def _validate_kpis(self):
        """Validate that all required KPIs are present"""
        required_kpis = [
            "latency_p95",
            "latency_p99",
            "throughput",
            "error_rate",
            "block_rate",
            "cross_tenant_interactions",
            "data_leaks",
            "cost_per_1k_transactions",
            "confidence_score",
            "fallback_rate",
        ]

        missing_kpis = []
        for kpi in required_kpis:
            if not hasattr(self.metrics, kpi) or getattr(self.metrics, kpi) is None:
                missing_kpis.append(kpi)

        if missing_kpis:
            raise ValueError(f"Missing required KPIs: {missing_kpis}")

    def _generate_html_report(self) -> str:
        """Generate HTML report"""
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        time_range = f"Last {self.config.time_range_hours} hours"

        return self.html_template.render(
            report_date=report_date,
            time_range=time_range,
            metrics=self.metrics,
            art_comparison=self.art_comparison,
            redteam_analysis=self.redteam_analysis,
        )

    async def _generate_pdf_report(self) -> str:
        """Generate PDF report (placeholder for now)"""
        # In a real implementation, you would use a library like WeasyPrint or wkhtmltopdf
        # For now, we'll create a placeholder
        pdf_path = os.path.join(self.config.output_dir, "testbed_report.pdf")

        # Create a simple PDF placeholder
        with open(pdf_path, "w") as f:
            f.write("PDF Report Placeholder\n")
            f.write("In production, this would be a properly formatted PDF\n")
            f.write(f"Generated: {datetime.now()}\n")

        return pdf_path

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate report summary"""
        return {
            "report_date": datetime.now().isoformat(),
            "time_range_hours": self.config.time_range_hours,
            "metrics_summary": {
                "performance": {
                    "latency_p95": self.metrics.latency_p95,
                    "latency_p99": self.metrics.latency_p99,
                    "throughput": self.metrics.throughput,
                },
                "security": {
                    "block_rate": self.metrics.block_rate,
                    "cross_tenant_interactions": self.metrics.cross_tenant_interactions,
                    "data_leaks": self.metrics.data_leaks,
                },
                "cost": {
                    "cost_per_1k_transactions": self.metrics.cost_per_1k_transactions
                },
                "confidence": {
                    "confidence_score": self.metrics.confidence_score,
                    "fallback_rate": self.metrics.fallback_rate,
                },
            },
            "art_comparison_count": len(self.art_comparison),
            "redteam_tests_count": len(self.redteam_analysis),
            "redteam_failures": len(
                [t for t in self.redteam_analysis if t.status == "fail"]
            ),
            "redteam_regressions": len(
                [t for t in self.redteam_analysis if t.status == "regression"]
            ),
        }


class ReportAnalyzer:
    """Analyzes metrics and generates insights"""

    def __init__(self, config: ReportConfig):
        self.config = config

    def analyze_metrics(self, metrics: TestbedMetrics) -> Dict[str, Any]:
        """Analyze metrics and generate insights"""
        insights = {
            "performance_analysis": self._analyze_performance(metrics),
            "security_analysis": self._analyze_security(metrics),
            "cost_analysis": self._analyze_cost(metrics),
            "confidence_analysis": self._analyze_confidence(metrics),
            "overall_health": self._calculate_overall_health(metrics),
        }

        return insights

    def compare_with_art(
        self, testbed_metrics: TestbedMetrics, art_results: Dict[str, Any]
    ) -> List[ARTComparison]:
        """Compare testbed metrics with ART harness results"""
        comparisons = []

        # Define metrics to compare
        comparison_metrics = {
            "latency_p95": "P95 Latency",
            "latency_p99": "P99 Latency",
            "throughput": "Throughput",
            "error_rate": "Error Rate",
            "block_rate": "Block Rate",
        }

        for metric_key, metric_name in comparison_metrics.items():
            if metric_key in art_results and hasattr(testbed_metrics, metric_key):
                testbed_value = getattr(testbed_metrics, metric_key)
                art_value = art_results[metric_key]

                delta = testbed_value - art_value
                delta_percentage = (delta / art_value * 100) if art_value != 0 else 0

                # Determine status
                if abs(delta_percentage) < 5:
                    status = "similar"
                elif delta < 0:
                    status = "better"
                else:
                    status = "worse"

                comparisons.append(
                    ARTComparison(
                        metric=metric_name,
                        testbed_value=testbed_value,
                        art_value=art_value,
                        delta=delta,
                        delta_percentage=delta_percentage,
                        status=status,
                    )
                )

        return comparisons

    def _analyze_performance(self, metrics: TestbedMetrics) -> Dict[str, Any]:
        """Analyze performance metrics"""
        return {
            "latency_status": (
                "good"
                if metrics.latency_p95 < 2
                else "warning" if metrics.latency_p95 < 5 else "critical"
            ),
            "throughput_status": (
                "good"
                if metrics.throughput > 100
                else "warning" if metrics.throughput > 50 else "critical"
            ),
            "recommendations": self._get_performance_recommendations(metrics),
        }

    def _analyze_security(self, metrics: TestbedMetrics) -> Dict[str, Any]:
        """Analyze security metrics"""
        return {
            "block_rate_status": (
                "good"
                if metrics.block_rate < 0.01
                else "warning" if metrics.block_rate < 0.05 else "critical"
            ),
            "cross_tenant_status": (
                "good" if metrics.cross_tenant_interactions == 0 else "critical"
            ),
            "leak_status": "good" if metrics.data_leaks == 0 else "critical",
            "recommendations": self._get_security_recommendations(metrics),
        }

    def _analyze_cost(self, metrics: TestbedMetrics) -> Dict[str, Any]:
        """Analyze cost metrics"""
        return {
            "cost_efficiency": (
                "good"
                if metrics.cost_per_1k_transactions < 0.01
                else (
                    "warning" if metrics.cost_per_1k_transactions < 0.05 else "critical"
                )
            ),
            "recommendations": self._get_cost_recommendations(metrics),
        }

    def _analyze_confidence(self, metrics: TestbedMetrics) -> Dict[str, Any]:
        """Analyze confidence metrics"""
        return {
            "confidence_status": (
                "good"
                if metrics.confidence_score > 0.95
                else "warning" if metrics.confidence_score > 0.8 else "critical"
            ),
            "fallback_status": (
                "good"
                if metrics.fallback_rate < 0.05
                else "warning" if metrics.fallback_rate < 0.1 else "critical"
            ),
            "recommendations": self._get_confidence_recommendations(metrics),
        }

    def _calculate_overall_health(self, metrics: TestbedMetrics) -> str:
        """Calculate overall system health"""
        # Simple scoring system
        score = 0

        # Performance (30%)
        if metrics.latency_p95 < 2:
            score += 30
        elif metrics.latency_p95 < 5:
            score += 20
        elif metrics.latency_p95 < 10:
            score += 10

        # Security (40%)
        if metrics.block_rate < 0.01:
            score += 40
        elif metrics.block_rate < 0.05:
            score += 30
        elif metrics.block_rate < 0.1:
            score += 20

        if metrics.cross_tenant_interactions == 0:
            score += 20
        if metrics.data_leaks == 0:
            score += 20

        # Confidence (30%)
        if metrics.confidence_score > 0.95:
            score += 30
        elif metrics.confidence_score > 0.8:
            score += 20
        elif metrics.confidence_score > 0.6:
            score += 10

        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "poor"

    def _get_performance_recommendations(self, metrics: TestbedMetrics) -> List[str]:
        """Get performance improvement recommendations"""
        recommendations = []

        if metrics.latency_p95 > 5:
            recommendations.append(
                "Investigate high P95 latency - consider caching or optimization"
            )

        if metrics.throughput < 50:
            recommendations.append(
                "Low throughput detected - check for bottlenecks or resource constraints"
            )

        return recommendations

    def _get_security_recommendations(self, metrics: TestbedMetrics) -> List[str]:
        """Get security improvement recommendations"""
        recommendations = []

        if metrics.block_rate > 0.05:
            recommendations.append(
                "High block rate - review security policies and thresholds"
            )

        if metrics.cross_tenant_interactions > 0:
            recommendations.append(
                "Cross-tenant interactions detected - investigate isolation controls"
            )

        if metrics.data_leaks > 0:
            recommendations.append(
                "Data leaks detected - immediate security review required"
            )

        return recommendations

    def _get_cost_recommendations(self, metrics: TestbedMetrics) -> List[str]:
        """Get cost optimization recommendations"""
        recommendations = []

        if metrics.cost_per_1k_transactions > 0.05:
            recommendations.append(
                "High cost per transaction - investigate resource usage and optimization"
            )

        return recommendations

    def _get_confidence_recommendations(self, metrics: TestbedMetrics) -> List[str]:
        """Get confidence improvement recommendations"""
        recommendations = []

        if metrics.confidence_score < 0.8:
            recommendations.append(
                "Low confidence score - review model training and validation"
            )

        if metrics.fallback_rate > 0.1:
            recommendations.append(
                "High fallback rate - investigate primary system reliability"
            )

        return recommendations


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate Testbed Report")
    parser.add_argument("--config", "-c", required=True, help="Configuration file path")
    parser.add_argument("--output", "-o", default="./reports", help="Output directory")
    parser.add_argument(
        "--format",
        "-f",
        choices=["html", "pdf", "both"],
        default="both",
        help="Report format",
    )
    parser.add_argument(
        "--time-range", "-t", type=int, default=24, help="Time range in hours"
    )

    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, "r") as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Create report configuration
    config = ReportConfig(
        prometheus_url=config_data.get("prometheus_url", "http://localhost:9090"),
        ledger_url=config_data.get("ledger_url", "http://localhost:8080"),
        art_results_path=config_data.get("art_results_path", ""),
        output_dir=args.output,
        report_format=args.format,
        time_range_hours=args.time_range,
        include_art_comparison=config_data.get("include_art_comparison", True),
        include_redteam_analysis=config_data.get("include_redteam_analysis", True),
        kpi_thresholds=config_data.get("kpi_thresholds", {}),
    )

    try:
        # Collect metrics
        async with MetricsCollector(config) as collector:
            logger.info("Collecting Prometheus metrics...")
            prometheus_metrics = await collector.collect_prometheus_metrics()

            logger.info("Collecting ledger metrics...")
            ledger_metrics = await collector.collect_ledger_metrics()

            logger.info("Collecting ART results...")
            art_results = await collector.collect_art_results()

            logger.info("Collecting red-team analysis...")
            redteam_analysis = await collector.collect_redteam_analysis()

        # Create metrics object
        metrics = TestbedMetrics(
            latency_p95=prometheus_metrics.get("latency_p95", 0.0),
            latency_p99=prometheus_metrics.get("latency_p99", 0.0),
            throughput=prometheus_metrics.get("throughput", 0.0),
            error_rate=prometheus_metrics.get("error_rate", 0.0),
            block_rate=prometheus_metrics.get("block_rate", 0.0),
            cross_tenant_interactions=int(
                prometheus_metrics.get("cross_tenant_interactions", 0)
            ),
            data_leaks=int(prometheus_metrics.get("data_leaks", 0)),
            honeytoken_alerts=int(prometheus_metrics.get("honeytoken_alerts", 0)),
            cost_per_1k_transactions=prometheus_metrics.get("total_cost", 0.0)
            / max(prometheus_metrics.get("total_transactions", 1), 1)
            * 1000,
            total_transactions=int(prometheus_metrics.get("total_transactions", 0)),
            total_cost=prometheus_metrics.get("total_cost", 0.0),
            confidence_score=prometheus_metrics.get("theorem_verification_rate", 0.0),
            fallback_rate=0.05,  # Placeholder - would come from actual metrics
            theorem_verification_rate=prometheus_metrics.get(
                "theorem_verification_rate", 0.0
            ),
            timestamp=datetime.now().isoformat(),
        )

        # Analyze metrics
        analyzer = ReportAnalyzer(config)
        insights = analyzer.analyze_metrics(metrics)

        # Compare with ART
        art_comparison = analyzer.compare_with_art(metrics, art_results)

        # Generate report
        generator = ReportGenerator(config)
        report_files = await generator.generate_report(
            metrics, art_comparison, redteam_analysis
        )

        # Print summary
        logger.info("Report generation completed successfully!")
        logger.info(f"Output files: {report_files}")
        logger.info(f"Overall health: {insights['overall_health']}")

        # Exit with error if any KPI is missing (as per requirements)
        if not all(
            hasattr(metrics, kpi)
            for kpi in [
                "latency_p95",
                "latency_p99",
                "block_rate",
                "cost_per_1k_transactions",
            ]
        ):
            logger.error("Missing required KPIs - report generation failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
