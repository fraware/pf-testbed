#!/usr/bin/env python3
"""
Seed Runner for TB-DATA
Populates indices with seed data and records token mappings in encrypted reports
"""

import json
import os
import hashlib
import base64
import secrets
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from honeytoken_generator import HoneytokenGenerator, TenantData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeedRunner:
    """Manages seeding of test data and honeytoken generation"""

    def __init__(self, base_path: str = "testbed/data"):
        self.base_path = Path(base_path)
        self.reports_path = self.base_path / "reports"
        self.seeds_path = self.base_path / "seeds"
        self.honeytoken_generator = HoneytokenGenerator()

        # Ensure directories exist
        self.reports_path.mkdir(parents=True, exist_ok=True)
        self.seeds_path.mkdir(parents=True, exist_ok=True)

    def generate_seed_data(
        self, tenant_id: str, data_type: str, count: int = 100
    ) -> Dict[str, Any]:
        """Generate synthetic seed data for a specific tenant and type"""

        if data_type == "users":
            return self._generate_user_data(tenant_id, count)
        elif data_type == "documents":
            return self._generate_document_data(tenant_id, count)
        elif data_type == "transactions":
            return self._generate_transaction_data(tenant_id, count)
        elif data_type == "api_calls":
            return self._generate_api_call_data(tenant_id, count)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def _generate_user_data(self, tenant_id: str, count: int) -> Dict[str, Any]:
        """Generate synthetic user data"""
        users = []

        for i in range(count):
            user_id = f"user_{tenant_id}_{i:04d}"

            # Generate PII data
            user = {
                "id": user_id,
                "tenant": tenant_id,
                "email": f"user{i}@{tenant_id}.com",
                "name": f"User {i}",
                "phone": f"+1-555-{i:03d}-{i:04d}",
                "department": self._get_random_department(),
                "role": self._get_random_role(),
                "created_at": datetime.utcnow().isoformat(),
                "last_login": datetime.utcnow().isoformat(),
                "status": "active" if i % 10 != 0 else "inactive",
            }

            # Add honeytokens for sensitive fields
            if i % 20 == 0:  # 5% of users get honeytokens
                user["email"] = self._get_honeytoken_email(tenant_id, i)

            users.append(user)

        return {
            "type": "users",
            "tenant": tenant_id,
            "count": count,
            "generated_at": datetime.utcnow().isoformat(),
            "data": users,
        }

    def _generate_document_data(self, tenant_id: str, count: int) -> Dict[str, Any]:
        """Generate synthetic document data"""
        documents = []

        for i in range(count):
            doc_id = f"doc_{tenant_id}_{i:04d}"

            document = {
                "id": doc_id,
                "tenant": tenant_id,
                "title": f"Document {i}",
                "content": f"This is the content of document {i} for tenant {tenant_id}",
                "author": f"user_{tenant_id}_{i % 50:04d}",
                "type": self._get_random_document_type(),
                "classification": self._get_random_classification(),
                "created_at": datetime.utcnow().isoformat(),
                "modified_at": datetime.utcnow().isoformat(),
                "tags": self._get_random_tags(),
            }

            # Add honeytokens for sensitive documents
            if i % 15 == 0:  # ~7% of documents get honeytokens
                document["content"] = self._get_honeytoken_content(tenant_id, i)

            documents.append(document)

        return {
            "type": "documents",
            "tenant": tenant_id,
            "count": count,
            "generated_at": datetime.utcnow().isoformat(),
            "data": documents,
        }

    def _generate_transaction_data(self, tenant_id: str, count: int) -> Dict[str, Any]:
        """Generate synthetic transaction data"""
        transactions = []

        for i in range(count):
            tx_id = f"tx_{tenant_id}_{i:04d}"

            transaction = {
                "id": tx_id,
                "tenant": tenant_id,
                "amount": round(secrets.randbelow(10000) / 100, 2),
                "currency": "USD",
                "description": f"Transaction {i}",
                "user_id": f"user_{tenant_id}_{i % 50:04d}",
                "status": self._get_random_transaction_status(),
                "created_at": datetime.utcnow().isoformat(),
                "processed_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "source": "web",
                    "ip_address": f"192.168.1.{i % 255}",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
            }

            # Add honeytokens for high-value transactions
            if i % 25 == 0:  # 4% of transactions get honeytokens
                transaction["description"] = self._get_honeytoken_description(
                    tenant_id, i
                )

            transactions.append(transaction)

        return {
            "type": "transactions",
            "tenant": tenant_id,
            "count": count,
            "generated_at": datetime.utcnow().isoformat(),
            "data": transactions,
        }

    def _generate_api_call_data(self, tenant_id: str, count: int) -> Dict[str, Any]:
        """Generate synthetic API call data"""
        api_calls = []

        for i in range(count):
            call_id = f"api_{tenant_id}_{i:04d}"

            api_call = {
                "id": call_id,
                "tenant": tenant_id,
                "endpoint": f"/api/v1/{self._get_random_endpoint()}",
                "method": self._get_random_http_method(),
                "user_id": f"user_{tenant_id}_{i % 50:04d}",
                "status_code": self._get_random_status_code(),
                "response_time": secrets.randbelow(1000),
                "created_at": datetime.utcnow().isoformat(),
                "ip_address": f"10.0.0.{i % 255}",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "request_size": secrets.randbelow(1024),
                "response_size": secrets.randbelow(2048),
            }

            # Add honeytokens for suspicious API calls
            if i % 30 == 0:  # ~3% of API calls get honeytokens
                api_call["endpoint"] = self._get_honeytoken_endpoint(tenant_id, i)

            api_calls.append(api_call)

        return {
            "type": "api_calls",
            "tenant": tenant_id,
            "count": count,
            "generated_at": datetime.utcnow().isoformat(),
            "data": api_calls,
        }

    def _get_random_department(self) -> str:
        """Get a random department"""
        departments = [
            "Engineering",
            "Sales",
            "Marketing",
            "HR",
            "Finance",
            "Operations",
        ]
        return secrets.choice(departments)

    def _get_random_role(self) -> str:
        """Get a random role"""
        roles = ["User", "Manager", "Admin", "Viewer", "Editor"]
        return secrets.choice(roles)

    def _get_random_document_type(self) -> str:
        """Get a random document type"""
        types = ["report", "proposal", "contract", "policy", "manual"]
        return secrets.choice(types)

    def _get_random_classification(self) -> str:
        """Get a random classification"""
        classifications = ["public", "internal", "confidential", "secret"]
        return secrets.choice(classifications)

    def _get_random_tags(self) -> List[str]:
        """Get random tags"""
        all_tags = ["urgent", "review", "approved", "draft", "final"]
        return secrets.sample(all_tags, secrets.randbelow(3) + 1)

    def _get_random_transaction_status(self) -> str:
        """Get a random transaction status"""
        statuses = ["pending", "completed", "failed", "cancelled"]
        return secrets.choice(statuses)

    def _get_random_endpoint(self) -> str:
        """Get a random API endpoint"""
        endpoints = ["users", "documents", "transactions", "reports", "analytics"]
        return secrets.choice(endpoints)

    def _get_random_http_method(self) -> str:
        """Get a random HTTP method"""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        return secrets.choice(methods)

    def _get_random_status_code(self) -> int:
        """Get a random HTTP status code"""
        status_codes = [200, 201, 400, 401, 403, 404, 500]
        return secrets.choice(status_codes)

    def _get_honeytoken_email(self, tenant_id: str, index: int) -> str:
        """Get a honeytoken email"""
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:8]
        return f"honeypot_{tenant_hash}_{index}@honeytrap.{tenant_id}.test"

    def _get_honeytoken_content(self, tenant_id: str, index: int) -> str:
        """Get honeytoken content"""
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:8]
        return f"HONEYTRAP_CONTENT_{tenant_hash}_{index}_SECRET_DATA"

    def _get_honeytoken_description(self, tenant_id: str, index: int) -> str:
        """Get honeytoken description"""
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:8]
        return f"HONEYTRAP_TRANSACTION_{tenant_hash}_{index}"

    def _get_honeytoken_endpoint(self, tenant_id: str, index: int) -> str:
        """Get honeytoken endpoint"""
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:8]
        return f"/api/honeytrap/{tenant_id}/{tenant_hash}/{index}"

    def run_seeding(
        self, tenants: List[str], data_types: List[str], counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """Run the complete seeding process"""

        logger.info("Starting data seeding process...")

        # Register tenants with honeytoken generator
        for tenant_id in tenants:
            tenant_data = TenantData(
                tenant_id=tenant_id,
                name=f"{tenant_id.title()} Corporation",
                data_classifications=["pii_masked", "pii_raw", "secret", "internal"],
                honeytoken_types=["email", "url", "api_key", "database", "file_path"],
                pii_fields=["email", "phone", "ssn"],
                secret_fields=["api_keys", "passwords", "tokens"],
                internal_fields=["employee_id", "department", "salary"],
            )
            self.honeytoken_generator.register_tenant(tenant_data)

        # Generate honeytokens for each tenant
        honeytoken_mapping = {}
        for tenant_id in tenants:
            tokens = self.honeytoken_generator.generate_honeytokens_for_tenant(
                tenant_id, 20
            )
            honeytoken_mapping[tenant_id] = [token.id for token in tokens]

        # Generate seed data for each tenant and type
        seed_data = {}
        for tenant_id in tenants:
            seed_data[tenant_id] = {}
            for data_type in data_types:
                count = counts.get(data_type, 100)
                seed_data[tenant_id][data_type] = self.generate_seed_data(
                    tenant_id, data_type, count
                )

        # Save seed data to files
        self._save_seed_data(seed_data)

        # Generate and save encrypted report
        report = self._generate_seed_report(tenants, seed_data, honeytoken_mapping)
        self._save_encrypted_report(report)

        logger.info("Data seeding process completed successfully")

        return {
            "status": "success",
            "tenants": tenants,
            "data_types": data_types,
            "total_records": sum(
                len(seed_data[tenant][dt]["data"])
                for tenant in tenants
                for dt in data_types
            ),
            "honeytokens_generated": sum(
                len(tokens) for tokens in honeytoken_mapping.values()
            ),
            "report_path": str(self.reports_path / "seeds.json.encrypted"),
        }

    def _save_seed_data(self, seed_data: Dict[str, Any]) -> None:
        """Save seed data to individual files"""
        for tenant_id, tenant_data in seed_data.items():
            tenant_path = self.seeds_path / tenant_id
            tenant_path.mkdir(exist_ok=True)

            for data_type, data in tenant_data.items():
                file_path = tenant_path / f"{data_type}.json"
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)

                logger.info(f"Saved {data_type} data for tenant {tenant_id}")

    def _generate_seed_report(
        self,
        tenants: List[str],
        seed_data: Dict[str, Any],
        honeytoken_mapping: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Generate the seed report with token mappings"""

        report = {
            "report_id": f"seed_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "generator_version": "1.0.0",
            "summary": {
                "total_tenants": len(tenants),
                "total_data_types": len(seed_data.get(tenants[0], {}).keys()),
                "total_records": sum(
                    len(seed_data[tenant][dt]["data"])
                    for tenant in tenants
                    for dt in seed_data.get(tenants[0], {}).keys()
                ),
                "total_honeytokens": sum(
                    len(tokens) for tokens in honeytoken_mapping.values()
                ),
            },
            "tenant_data": {},
            "honeytoken_mapping": honeytoken_mapping,
            "data_quality_metrics": self._calculate_data_quality(seed_data),
            "honeytoken_coverage": self._calculate_honeytoken_coverage(
                seed_data, honeytoken_mapping
            ),
        }

        # Add tenant-specific summaries
        for tenant_id in tenants:
            tenant_summary = {
                "data_types": list(seed_data[tenant_id].keys()),
                "record_counts": {
                    dt: len(data["data"]) for dt, data in seed_data[tenant_id].items()
                },
                "honeytoken_count": len(honeytoken_mapping.get(tenant_id, [])),
                "data_generated_at": datetime.utcnow().isoformat(),
            }
            report["tenant_data"][tenant_id] = tenant_summary

        return report

    def _calculate_data_quality(self, seed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate data quality metrics"""
        total_records = 0
        records_with_honeytokens = 0

        for tenant_data in seed_data.values():
            for data_type, data in tenant_data.items():
                total_records += len(data["data"])
                # Count records that contain honeytokens
                for record in data["data"]:
                    if any("honeytrap" in str(v).lower() for v in record.values()):
                        records_with_honeytokens += 1

        return {
            "total_records": total_records,
            "records_with_honeytokens": records_with_honeytokens,
            "honeytoken_coverage_percentage": (
                round((records_with_honeytokens / total_records * 100), 2)
                if total_records > 0
                else 0
            ),
        }

    def _calculate_honeytoken_coverage(
        self, seed_data: Dict[str, Any], honeytoken_mapping: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Calculate honeytoken coverage metrics"""
        coverage = {}

        for tenant_id in honeytoken_mapping.keys():
            tenant_tokens = len(honeytoken_mapping[tenant_id])
            tenant_records = sum(
                len(seed_data[tenant_id][dt]["data"])
                for dt in seed_data[tenant_id].keys()
            )

            coverage[tenant_id] = {
                "honeytokens": tenant_tokens,
                "total_records": tenant_records,
                "coverage_ratio": (
                    round(tenant_tokens / tenant_records, 4)
                    if tenant_records > 0
                    else 0
                ),
            }

        return coverage

    def _save_encrypted_report(self, report: Dict[str, Any]) -> None:
        """Save the encrypted seed report"""
        report_path = self.reports_path / "seeds.json.encrypted"

        # Simple encryption for demo - use proper encryption in production
        report_json = json.dumps(report, indent=2)
        encrypted_data = base64.b64encode(report_json.encode()).decode()

        encrypted_report = {
            "encrypted_at": datetime.utcnow().isoformat(),
            "encryption_method": "base64",  # Demo only - use proper encryption
            "data": encrypted_data,
        }

        with open(report_path, "w") as f:
            json.dump(encrypted_report, f, indent=2)

        logger.info(f"Saved encrypted seed report to {report_path}")


def main():
    """Example usage of the SeedRunner"""

    # Initialize seed runner
    runner = SeedRunner()

    # Define seeding configuration
    tenants = ["acme_corp", "globex_inc", "cyberdyne_systems"]
    data_types = ["users", "documents", "transactions", "api_calls"]
    counts = {"users": 200, "documents": 150, "transactions": 300, "api_calls": 500}

    # Run seeding process
    try:
        result = runner.run_seeding(tenants, data_types, counts)
        print("Seeding completed successfully!")
        print(f"Generated {result['total_records']} records")
        print(f"Generated {result['honeytokens_generated']} honeytokens")
        print(f"Report saved to: {result['report_path']}")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise


if __name__ == "__main__":
    main()

