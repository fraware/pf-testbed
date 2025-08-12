#!/usr/bin/env python3
"""
Accuracy Posture Monitor for Testbed
Tracks answer metadata, sources, confidence scores, and implements fallback policies.
"""

import asyncio
import json
import logging
import hashlib
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
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics for accuracy monitoring
ACCURACY_QUERIES = Counter(
    "accuracy_queries_total",
    "Total accuracy queries processed",
    ["tenant", "model", "confidence_level"],
)
CONFIDENCE_SCORES = Histogram(
    "confidence_scores",
    "Distribution of confidence scores",
    ["tenant", "model", "query_type"],
)
FALLBACK_ACTIVATIONS = Counter(
    "fallback_activations_total",
    "Total fallback policy activations",
    ["trigger", "fallback_type"],
)
SOURCE_VERIFICATION = Counter(
    "source_verification_total",
    "Source verification results",
    ["status", "source_type"],
)
ACCURACY_KPI = Gauge("accuracy_kpi_score", "Overall accuracy KPI score")


@dataclass
class AnswerMetadata:
    """Metadata for an AI-generated answer"""

    answer_id: str
    query_hash: str
    tenant: str
    model: str
    confidence_score: float
    sources: List[Dict[str, Any]]
    answer_hash: str
    timestamp: datetime
    processing_time_ms: int
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    verification_status: str = "pending"
    kpi_impact: Dict[str, float] = None


@dataclass
class Source:
    """Information source for an answer"""

    source_id: str
    source_type: str  # "document", "database", "api", "knowledge_base"
    content_hash: str
    relevance_score: float
    timestamp: datetime
    metadata: Dict[str, Any]
    verification_status: str = "pending"


@dataclass
class FallbackPolicy:
    """Configuration for fallback policies"""

    name: str
    trigger_condition: (
        str  # "low_confidence", "source_unavailable", "verification_failed"
    )
    confidence_threshold: float
    action: (
        str  # "human_review", "alternative_model", "cached_response", "error_response"
    )
    parameters: Dict[str, Any]
    priority: int  # Lower number = higher priority


@dataclass
class AccuracyKPI:
    """Key Performance Indicator for accuracy"""

    name: str
    metric: str
    target_value: float
    current_value: float
    trend: str  # "improving", "stable", "declining"
    last_updated: datetime
    weight: float  # Importance weight for overall score


class AccuracyMonitor:
    """Main accuracy monitoring system"""

    def __init__(self, config_path: str = "testbed/accuracy/config.yaml"):
        self.config = self._load_config(config_path)
        self.db_path = "testbed/accuracy/accuracy.db"
        self._init_database()

        # Initialize Prometheus metrics
        start_http_server(8002)
        logger.info("Accuracy monitoring metrics server started on port 8002")

        # Load fallback policies
        self.fallback_policies = self._load_fallback_policies()

        # Initialize KPI tracking
        self.kpi_scores = {}
        self._init_kpi_tracking()

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
            "confidence_thresholds": {
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4,
                "critical": 0.2,
            },
            "fallback_policies": {
                "low_confidence": {"threshold": 0.6, "action": "human_review"},
                "source_unavailable": {"action": "alternative_model"},
            },
            "kpi_weights": {
                "confidence_score": 0.3,
                "source_verification": 0.3,
                "fallback_effectiveness": 0.2,
                "response_quality": 0.2,
            },
        }

    def _init_database(self):
        """Initialize SQLite database for accuracy tracking"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                answer_id TEXT PRIMARY KEY,
                query_hash TEXT NOT NULL,
                tenant TEXT NOT NULL,
                model TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                answer_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                processing_time_ms INTEGER NOT NULL,
                fallback_used BOOLEAN DEFAULT FALSE,
                fallback_reason TEXT,
                verification_status TEXT DEFAULT 'pending',
                kpi_impact TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                answer_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                relevance_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                verification_status TEXT DEFAULT 'pending',
                FOREIGN KEY (answer_id) REFERENCES answers (answer_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fallback_events (
                event_id TEXT PRIMARY KEY,
                answer_id TEXT NOT NULL,
                policy_name TEXT NOT NULL,
                trigger TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN,
                FOREIGN KEY (answer_id) REFERENCES answers (answer_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS kpi_scores (
                kpi_name TEXT PRIMARY KEY,
                metric TEXT NOT NULL,
                target_value REAL NOT NULL,
                current_value REAL NOT NULL,
                trend TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                weight REAL NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

        logger.info("Accuracy database initialized")

    def _load_fallback_policies(self) -> List[FallbackPolicy]:
        """Load fallback policies from configuration"""
        policies = []

        for name, config in self.config.get("fallback_policies", {}).items():
            policy = FallbackPolicy(
                name=name,
                trigger_condition=name,
                confidence_threshold=config.get("threshold", 0.5),
                action=config.get("action", "error_response"),
                parameters=config.get("parameters", {}),
                priority=config.get("priority", 10),
            )
            policies.append(policy)

        # Sort by priority
        policies.sort(key=lambda x: x.priority)
        return policies

    def _init_kpi_tracking(self):
        """Initialize KPI tracking"""
        kpi_configs = [
            ("confidence_score", "Average confidence score", 0.8, 0.0, 0.3),
            ("source_verification", "Source verification rate", 0.95, 0.0, 0.3),
            ("fallback_effectiveness", "Fallback success rate", 0.9, 0.0, 0.2),
            ("response_quality", "Response quality score", 0.85, 0.0, 0.2),
        ]

        for name, metric, target, current, weight in kpi_configs:
            kpi = AccuracyKPI(
                name=name,
                metric=metric,
                target_value=target,
                current_value=current,
                trend="stable",
                last_updated=datetime.now(),
                weight=weight,
            )
            self.kpi_scores[name] = kpi
            self._save_kpi(kpi)

    async def process_answer(
        self,
        query: str,
        answer: str,
        tenant: str,
        model: str,
        confidence_score: float,
        sources: List[Dict[str, Any]] = None,
        processing_time_ms: int = 0,
    ) -> AnswerMetadata:
        """Process and track an AI-generated answer"""
        answer_id = str(uuid.uuid4())
        query_hash = self._hash_content(query)
        answer_hash = self._hash_content(answer)

        # Create answer metadata
        metadata = AnswerMetadata(
            answer_id=answer_id,
            query_hash=query_hash,
            tenant=tenant,
            model=model,
            confidence_score=confidence_score,
            sources=sources or [],
            answer_hash=answer_hash,
            timestamp=datetime.now(),
            processing_time_ms=processing_time_ms,
        )

        # Check if fallback is needed
        fallback_needed, fallback_policy = self._check_fallback_needed(metadata)
        if fallback_needed:
            metadata.fallback_used = True
            metadata.fallback_reason = (
                f"Triggered by {fallback_policy.trigger_condition}"
            )
            await self._apply_fallback(metadata, fallback_policy)

        # Process sources
        if sources:
            await self._process_sources(metadata, sources)

        # Save to database
        self._save_answer(metadata)

        # Update metrics
        self._update_metrics(metadata)

        # Update KPI scores
        await self._update_kpi_scores()

        return metadata

    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash of content"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _check_fallback_needed(
        self, metadata: AnswerMetadata
    ) -> Tuple[bool, Optional[FallbackPolicy]]:
        """Check if fallback policy should be triggered"""
        for policy in self.fallback_policies:
            if policy.trigger_condition == "low_confidence":
                if metadata.confidence_score < policy.confidence_threshold:
                    return True, policy
            elif policy.trigger_condition == "source_unavailable":
                if not metadata.sources:
                    return True, policy

        return False, None

    async def _apply_fallback(self, metadata: AnswerMetadata, policy: FallbackPolicy):
        """Apply fallback policy"""
        try:
            logger.info(f"Applying fallback policy: {policy.name}")

            if policy.action == "human_review":
                await self._human_review_fallback(metadata)
            elif policy.action == "alternative_model":
                await self._alternative_model_fallback(metadata)
            elif policy.action == "cached_response":
                await self._cached_response_fallback(metadata)
            elif policy.action == "error_response":
                await self._error_response_fallback(metadata)

            # Record fallback event
            self._record_fallback_event(metadata.answer_id, policy, True)

            FALLBACK_ACTIVATIONS.labels(
                trigger=policy.trigger_condition, fallback_type=policy.action
            ).inc()

        except Exception as e:
            logger.error(f"Fallback application failed: {e}")
            self._record_fallback_event(metadata.answer_id, policy, False)

    async def _human_review_fallback(self, metadata: AnswerMetadata):
        """Human review fallback"""
        # In a real implementation, this would queue the answer for human review
        logger.info(f"Queued answer {metadata.answer_id} for human review")

        # Simulate human review process
        await asyncio.sleep(1)
        metadata.verification_status = "human_review_pending"

    async def _alternative_model_fallback(self, metadata: AnswerMetadata):
        """Alternative model fallback"""
        # In a real implementation, this would retry with a different model
        logger.info(f"Retrying answer {metadata.answer_id} with alternative model")

        # Simulate alternative model processing
        await asyncio.sleep(2)
        metadata.confidence_score = min(metadata.confidence_score + 0.1, 1.0)

    async def _cached_response_fallback(self, metadata: AnswerMetadata):
        """Cached response fallback"""
        # In a real implementation, this would return a cached response
        logger.info(f"Using cached response for answer {metadata.answer_id}")

        # Simulate cache lookup
        await asyncio.sleep(0.5)
        metadata.verification_status = "cached_response"

    async def _error_response_fallback(self, metadata: AnswerMetadata):
        """Error response fallback"""
        # In a real implementation, this would return an error response
        logger.info(f"Returning error response for answer {metadata.answer_id}")

        metadata.verification_status = "error_response"

    async def _process_sources(
        self, metadata: AnswerMetadata, sources: List[Dict[str, Any]]
    ):
        """Process and verify sources"""
        for source_data in sources:
            source = Source(
                source_id=str(uuid.uuid4()),
                source_type=source_data.get("type", "unknown"),
                content_hash=self._hash_content(str(source_data.get("content", ""))),
                relevance_score=source_data.get("relevance", 0.0),
                timestamp=datetime.now(),
                metadata=source_data.get("metadata", {}),
                verification_status="pending",
            )

            # Verify source
            verification_result = await self._verify_source(source)
            source.verification_status = verification_result

            # Save source
            self._save_source(metadata.answer_id, source)

            # Update metrics
            SOURCE_VERIFICATION.labels(
                status=verification_result, source_type=source.source_type
            ).inc()

    async def _verify_source(self, source: Source) -> str:
        """Verify a source's authenticity and relevance"""
        try:
            # Simulate source verification process
            await asyncio.sleep(0.1)

            # Check content hash validity
            if len(source.content_hash) != 64:  # SHA-256 length
                return "invalid_hash"

            # Check relevance score
            if source.relevance_score < 0.1:
                return "low_relevance"

            # Check source type validity
            valid_types = ["document", "database", "api", "knowledge_base"]
            if source.source_type not in valid_types:
                return "invalid_type"

            return "verified"

        except Exception as e:
            logger.error(f"Source verification failed: {e}")
            return "verification_failed"

    def _save_answer(self, metadata: AnswerMetadata):
        """Save answer metadata to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO answers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metadata.answer_id,
                metadata.query_hash,
                metadata.tenant,
                metadata.model,
                metadata.confidence_score,
                metadata.answer_hash,
                metadata.timestamp.isoformat(),
                metadata.processing_time_ms,
                metadata.fallback_used,
                metadata.fallback_reason,
                metadata.verification_status,
                json.dumps(metadata.kpi_impact) if metadata.kpi_impact else None,
            ),
        )

        conn.commit()
        conn.close()

    def _save_source(self, answer_id: str, source: Source):
        """Save source information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                source.source_id,
                answer_id,
                source.source_type,
                source.content_hash,
                source.relevance_score,
                source.timestamp.isoformat(),
                json.dumps(source.metadata),
                source.verification_status,
            ),
        )

        conn.commit()
        conn.close()

    def _record_fallback_event(
        self, answer_id: str, policy: FallbackPolicy, success: bool
    ):
        """Record a fallback event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO fallback_events VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                str(uuid.uuid4()),
                answer_id,
                policy.name,
                policy.trigger_condition,
                policy.action,
                datetime.now().isoformat(),
                success,
            ),
        )

        conn.commit()
        conn.close()

    def _update_metrics(self, metadata: AnswerMetadata):
        """Update Prometheus metrics"""
        # Update query counter
        confidence_level = self._get_confidence_level(metadata.confidence_score)
        ACCURACY_QUERIES.labels(
            tenant=metadata.tenant,
            model=metadata.model,
            confidence_level=confidence_level,
        ).inc()

        # Update confidence score histogram
        CONFIDENCE_SCORES.labels(
            tenant=metadata.tenant, model=metadata.model, query_type="general"
        ).observe(metadata.confidence_score)

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level category"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "critical"

    async def _update_kpi_scores(self):
        """Update KPI scores based on recent data"""
        try:
            # Calculate confidence score KPI
            avg_confidence = await self._calculate_average_confidence()
            self._update_kpi("confidence_score", avg_confidence)

            # Calculate source verification KPI
            verification_rate = await self._calculate_verification_rate()
            self._update_kpi("source_verification", verification_rate)

            # Calculate fallback effectiveness KPI
            fallback_success_rate = await self._calculate_fallback_success_rate()
            self._update_kpi("fallback_effectiveness", fallback_success_rate)

            # Calculate response quality KPI
            quality_score = await self._calculate_quality_score()
            self._update_kpi("response_quality", quality_score)

            # Calculate overall KPI score
            overall_score = self._calculate_overall_kpi_score()
            ACCURACY_KPI.set(overall_score)

        except Exception as e:
            logger.error(f"Failed to update KPI scores: {e}")

    async def _calculate_average_confidence(self) -> float:
        """Calculate average confidence score"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT AVG(confidence_score) FROM answers")
        result = cursor.fetchone()

        conn.close()
        return result[0] if result[0] else 0.0

    async def _calculate_verification_rate(self) -> float:
        """Calculate source verification rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN verification_status = 'verified' THEN 1 END) * 1.0 / COUNT(*)
            FROM sources
        """
        )
        result = cursor.fetchone()

        conn.close()
        return result[0] if result[0] else 0.0

    async def _calculate_fallback_success_rate(self) -> float:
        """Calculate fallback success rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                COUNT(CASE WHEN success = 1 THEN 1 END) * 1.0 / COUNT(*)
            FROM fallback_events
        """
        )
        result = cursor.fetchone()

        conn.close()
        return result[0] if result[0] else 0.0

    async def _calculate_quality_score(self) -> float:
        """Calculate response quality score"""
        # This is a simplified quality score calculation
        # In practice, this could involve more sophisticated metrics

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate based on confidence and processing time
        cursor.execute(
            """
            SELECT 
                AVG(confidence_score * (1 - processing_time_ms / 10000.0))
            FROM answers
        """
        )
        result = cursor.fetchone()

        conn.close()
        return max(0.0, min(1.0, result[0] if result[0] else 0.0))

    def _update_kpi(self, kpi_name: str, new_value: float):
        """Update a specific KPI score"""
        if kpi_name in self.kpi_scores:
            kpi = self.kpi_scores[kpi_name]
            old_value = kpi.current_value

            # Update value
            kpi.current_value = new_value
            kpi.last_updated = datetime.now()

            # Determine trend
            if new_value > old_value + 0.01:
                kpi.trend = "improving"
            elif new_value < old_value - 0.01:
                kpi.trend = "declining"
            else:
                kpi.trend = "stable"

            # Save to database
            self._save_kpi(kpi)

    def _save_kpi(self, kpi: AccuracyKPI):
        """Save KPI score to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO kpi_scores VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                kpi.name,
                kpi.metric,
                kpi.target_value,
                kpi.current_value,
                kpi.trend,
                kpi.last_updated.isoformat(),
                kpi.weight,
            ),
        )

        conn.commit()
        conn.close()

    def _calculate_overall_kpi_score(self) -> float:
        """Calculate overall KPI score"""
        total_score = 0.0
        total_weight = 0.0

        for kpi in self.kpi_scores.values():
            # Normalize score to 0-1 range
            normalized_score = min(1.0, kpi.current_value / kpi.target_value)
            total_score += normalized_score * kpi.weight
            total_weight += kpi.weight

        return total_score / total_weight if total_weight > 0 else 0.0

    async def get_accuracy_report(
        self, tenant: str = None, time_range: timedelta = None
    ) -> Dict[str, Any]:
        """Generate accuracy report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build query with filters
            query = "SELECT * FROM answers WHERE 1=1"
            params = []

            if tenant:
                query += " AND tenant = ?"
                params.append(tenant)

            if time_range:
                cutoff_time = datetime.now() - time_range
                query += " AND timestamp > ?"
                params.append(cutoff_time.isoformat())

            cursor.execute(query, params)
            answers = cursor.fetchall()

            # Process results
            report = {
                "total_answers": len(answers),
                "average_confidence": 0.0,
                "fallback_usage_rate": 0.0,
                "verification_status_distribution": {},
                "kpi_scores": {},
                "trends": {},
            }

            if answers:
                # Calculate averages
                confidence_scores = [row[4] for row in answers]
                report["average_confidence"] = sum(confidence_scores) / len(
                    confidence_scores
                )

                fallback_used = sum(1 for row in answers if row[8])
                report["fallback_usage_rate"] = fallback_used / len(answers)

                # Status distribution
                for row in answers:
                    status = row[11]
                    report["verification_status_distribution"][status] = (
                        report["verification_status_distribution"].get(status, 0) + 1
                    )

            # Add KPI scores
            for kpi_name, kpi in self.kpi_scores.items():
                report["kpi_scores"][kpi_name] = {
                    "current_value": kpi.current_value,
                    "target_value": kpi.target_value,
                    "trend": kpi.trend,
                    "weight": kpi.weight,
                }

            conn.close()
            return report

        except Exception as e:
            logger.error(f"Failed to generate accuracy report: {e}")
            return {}

    async def export_accuracy_data(
        self, format: str = "json", tenant: str = None, time_range: timedelta = None
    ) -> str:
        """Export accuracy data in specified format"""
        try:
            report = await self.get_accuracy_report(tenant, time_range)

            if format == "json":
                return json.dumps(report, indent=2, default=str)
            elif format == "csv":
                return self._convert_to_csv(report)
            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Failed to export accuracy data: {e}")
            return ""

    def _convert_to_csv(self, report: Dict[str, Any]) -> str:
        """Convert report to CSV format"""
        csv_lines = []

        # Add summary metrics
        csv_lines.append("Metric,Value")
        csv_lines.append(f"Total Answers,{report.get('total_answers', 0)}")
        csv_lines.append(
            f"Average Confidence,{report.get('average_confidence', 0.0):.3f}"
        )
        csv_lines.append(
            f"Fallback Usage Rate,{report.get('fallback_usage_rate', 0.0):.3f}"
        )

        # Add KPI scores
        csv_lines.append("")
        csv_lines.append("KPI,Current Value,Target Value,Trend,Weight")
        for kpi_name, kpi_data in report.get("kpi_scores", {}).items():
            csv_lines.append(
                f"{kpi_name},"
                f"{kpi_data['current_value']:.3f},"
                f"{kpi_data['target_value']:.3f},"
                f"{kpi_data['trend']},"
                f"{kpi_data['weight']:.3f}"
            )

        return "\n".join(csv_lines)


async def main():
    """Main function to demonstrate accuracy monitoring"""
    # Create accuracy monitor
    monitor = AccuracyMonitor()

    # Simulate some answers
    sample_queries = [
        "What is the capital of France?",
        "How does photosynthesis work?",
        "What are the benefits of exercise?",
        "Explain quantum computing",
        "What is machine learning?",
    ]

    sample_answers = [
        "The capital of France is Paris.",
        "Photosynthesis is the process by which plants convert light energy into chemical energy.",
        "Exercise provides numerous health benefits including improved cardiovascular health.",
        "Quantum computing uses quantum mechanical phenomena to process information.",
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
    ]

    print("Processing sample answers for accuracy monitoring...")

    for i, (query, answer) in enumerate(zip(sample_queries, sample_answers)):
        # Simulate varying confidence scores
        confidence = 0.7 + (i * 0.05) + (np.random.random() * 0.2)
        confidence = min(1.0, max(0.0, confidence))

        # Simulate sources
        sources = [
            {
                "type": "knowledge_base",
                "content": f"Source content for query {i+1}",
                "relevance": 0.8 + (np.random.random() * 0.2),
                "metadata": {"source_id": f"src_{i+1}"},
            }
        ]

        # Process answer
        metadata = await monitor.process_answer(
            query=query,
            answer=answer,
            tenant="test-tenant",
            model="gpt-4",
            confidence_score=confidence,
            sources=sources,
            processing_time_ms=int(np.random.random() * 1000 + 500),
        )

        print(
            f"Processed answer {i+1}: confidence={confidence:.3f}, "
            f"fallback={metadata.fallback_used}"
        )

        await asyncio.sleep(0.1)  # Small delay between answers

    # Generate and display report
    print("\nGenerating accuracy report...")
    report = await monitor.get_accuracy_report()

    print("\n" + "=" * 80)
    print("ACCURACY REPORT")
    print("=" * 80)
    print(f"Total Answers: {report.get('total_answers', 0)}")
    print(f"Average Confidence: {report.get('average_confidence', 0.0):.3f}")
    print(f"Fallback Usage Rate: {report.get('fallback_usage_rate', 0.0):.3f}")

    print("\nKPI Scores:")
    for kpi_name, kpi_data in report.get("kpi_scores", {}).items():
        print(
            f"  {kpi_name}: {kpi_data['current_value']:.3f} "
            f"(target: {kpi_data['target_value']:.3f}, "
            f"trend: {kpi_data['trend']})"
        )

    # Export data
    print("\nExporting accuracy data...")
    csv_data = await monitor.export_accuracy_data(format="csv")

    # Save to file
    os.makedirs("testbed/results", exist_ok=True)
    with open("testbed/results/accuracy_report.csv", "w") as f:
        f.write(csv_data)

    print("Accuracy report saved to testbed/results/accuracy_report.csv")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
