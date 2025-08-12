#!/usr/bin/env python3
"""
Honeytoken Generator for TB-DATA
Creates unique trap secrets for each tenant to detect unauthorized access
"""

import json
import uuid
import hashlib
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Honeytoken:
    """Represents a single honeytoken"""

    id: str
    type: str  # email, url, api_key, database, file_path
    value: str
    tenant: str
    classification: str  # pii_masked, pii_raw, secret, internal
    created_at: str
    expires_at: Optional[str]
    metadata: Dict[str, Any]
    trip_count: int = 0
    last_tripped: Optional[str] = None


@dataclass
class TenantData:
    """Represents tenant-specific data configuration"""

    tenant_id: str
    name: str
    data_classifications: List[str]
    honeytoken_types: List[str]
    pii_fields: List[str]
    secret_fields: List[str]
    internal_fields: List[str]


class HoneytokenGenerator:
    """Generates and manages honeytokens for tenant data"""

    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.honeytokens: Dict[str, Honeytoken] = {}
        self.tenant_configs: Dict[str, TenantData] = {}
        self.trip_alerts: List[Dict[str, Any]] = []

    def _generate_encryption_key(self) -> str:
        """Generate a random encryption key"""
        return base64.b64encode(secrets.token_bytes(32)).decode("utf-8")

    def register_tenant(self, tenant_data: TenantData) -> None:
        """Register a new tenant with their data configuration"""
        self.tenant_configs[tenant_data.tenant_id] = tenant_data
        logger.info(f"Registered tenant: {tenant_data.name} ({tenant_data.tenant_id})")

    def generate_honeytokens_for_tenant(
        self, tenant_id: str, count: int = 10
    ) -> List[Honeytoken]:
        """Generate honeytokens for a specific tenant"""
        if tenant_id not in self.tenant_configs:
            raise ValueError(f"Tenant {tenant_id} not registered")

        tenant_config = self.tenant_configs[tenant_id]
        honeytokens = []

        for i in range(count):
            # Determine token type and classification
            token_type = secrets.choice(tenant_config.honeytoken_types)
            classification = secrets.choice(tenant_config.data_classifications)

            # Generate appropriate value based on type
            value = self._generate_token_value(token_type, tenant_id, i)

            # Create honeytoken
            honeytoken = Honeytoken(
                id=f"ht_{tenant_id}_{token_type}_{uuid.uuid4().hex[:8]}",
                type=token_type,
                value=value,
                tenant=tenant_id,
                classification=classification,
                created_at=datetime.utcnow().isoformat(),
                expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat(),
                metadata={
                    "generator_version": "1.0.0",
                    "tenant_name": tenant_config.name,
                    "generation_batch": i,
                    "encrypted": True,
                },
            )

            self.honeytokens[honeytoken.id] = honeytoken
            honeytokens.append(honeytoken)

        logger.info(f"Generated {count} honeytokens for tenant {tenant_id}")
        return honeytokens

    def _generate_token_value(self, token_type: str, tenant_id: str, index: int) -> str:
        """Generate appropriate value for different token types"""
        tenant_hash = hashlib.sha256(tenant_id.encode()).hexdigest()[:8]

        if token_type == "email":
            return f"honeypot_{tenant_hash}_{index}@honeytrap.{tenant_id}.test"

        elif token_type == "url":
            return f"https://honeytrap.{tenant_id}.test/api/{tenant_hash}/{index}"

        elif token_type == "api_key":
            return f"ht_{tenant_hash}_{secrets.token_hex(16)}"

        elif token_type == "database":
            return f"honeytrap_{tenant_id}_{tenant_hash}_{index}"

        elif token_type == "file_path":
            return f"/var/honeytrap/{tenant_id}/{tenant_hash}/{index}.txt"

        else:
            return f"honeytrap_{tenant_id}_{token_type}_{index}"

    def check_honeytoken_trip(
        self, value: str, context: Dict[str, Any]
    ) -> Optional[Honeytoken]:
        """Check if a value is a honeytoken and record the trip"""
        for honeytoken in self.honeytokens.values():
            if honeytoken.value == value:
                # Record the trip
                honeytoken.trip_count += 1
                honeytoken.last_tripped = datetime.utcnow().isoformat()

                # Create trip alert
                alert = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "honeytoken_id": honeytoken.id,
                    "tenant": honeytoken.tenant,
                    "type": honeytoken.type,
                    "classification": honeytoken.classification,
                    "context": context,
                    "severity": (
                        "HIGH" if honeytoken.classification == "secret" else "MEDIUM"
                    ),
                }

                self.trip_alerts.append(alert)

                logger.warning(
                    f"HONEYTOKEN TRIP DETECTED: {honeytoken.id} for tenant {honeytoken.tenant}"
                )

                # Trigger immediate blocking and alerting
                self._trigger_security_response(honeytoken, alert)

                return honeytoken

        return None

    def _trigger_security_response(
        self, honeytoken: Honeytoken, alert: Dict[str, Any]
    ) -> None:
        """Trigger immediate security response for honeytoken trip"""
        # This would integrate with your security infrastructure
        # For now, we'll log and simulate blocking

        logger.critical(f"SECURITY RESPONSE TRIGGERED for honeytoken {honeytoken.id}")
        logger.critical(f"Tenant: {honeytoken.tenant}")
        logger.critical(f"Classification: {honeytoken.classification}")
        logger.critical(f"Context: {alert['context']}")

        # Simulate immediate blocking
        # In production, this would:
        # 1. Block the source IP/user
        # 2. Notify security team
        # 3. Freeze affected accounts
        # 4. Initiate incident response

        if honeytoken.classification == "secret":
            logger.critical(
                "CRITICAL: Secret honeytoken tripped - initiating emergency response"
            )

    def get_honeytoken_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about honeytokens"""
        stats = {
            "total_honeytokens": len(self.honeytokens),
            "total_trips": sum(ht.trip_count for ht in self.honeytokens.values()),
            "active_honeytokens": len(
                [ht for ht in self.honeytokens.values() if ht.trip_count == 0]
            ),
            "tripped_honeytokens": len(
                [ht for ht in self.honeytokens.values() if ht.trip_count > 0]
            ),
            "by_type": {},
            "by_classification": {},
            "by_tenant": {},
        }

        # Count by type
        for honeytoken in self.honeytokens.values():
            stats["by_type"][honeytoken.type] = (
                stats["by_type"].get(honeytoken.type, 0) + 1
            )
            stats["by_classification"][honeytoken.classification] = (
                stats["by_classification"].get(honeytoken.classification, 0) + 1
            )
            stats["by_tenant"][honeytoken.tenant] = (
                stats["by_tenant"].get(honeytoken.tenant, 0) + 1
            )

        if tenant_id:
            tenant_stats = {
                "tenant_id": tenant_id,
                "honeytokens": len(
                    [ht for ht in self.honeytokens.values() if ht.tenant == tenant_id]
                ),
                "trips": sum(
                    ht.trip_count
                    for ht in self.honeytokens.values()
                    if ht.tenant == tenant_id
                ),
                "active": len(
                    [
                        ht
                        for ht in self.honeytokens.values()
                        if ht.tenant == tenant_id and ht.trip_count == 0
                    ]
                ),
            }
            return tenant_stats

        return stats

    def export_honeytokens(
        self, tenant_id: Optional[str] = None, encrypted: bool = True
    ) -> str:
        """Export honeytokens to JSON format"""
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "generator_version": "1.0.0",
            "honeytokens": [],
        }

        for honeytoken in self.honeytokens.values():
            if tenant_id is None or honeytoken.tenant == tenant_id:
                honeytoken_dict = asdict(honeytoken)
                if encrypted:
                    # Simple encryption for demo - use proper encryption in production
                    honeytoken_dict["value"] = self._encrypt_value(
                        honeytoken_dict["value"]
                    )
                export_data["honeytokens"].append(honeytoken_dict)

        return json.dumps(export_data, indent=2)

    def _encrypt_value(self, value: str) -> str:
        """Simple encryption for honeytoken values"""
        # This is a basic encryption for demonstration
        # In production, use proper encryption libraries
        encoded = value.encode("utf-8")
        encrypted = base64.b64encode(encoded).decode("utf-8")
        return f"encrypted_{encrypted}"

    def import_honeytokens(self, json_data: str) -> None:
        """Import honeytokens from JSON format"""
        try:
            data = json.loads(json_data)
            imported_count = 0

            for honeytoken_data in data.get("honeytokens", []):
                # Convert back to Honeytoken object
                honeytoken = Honeytoken(**honeytoken_data)
                self.honeytokens[honeytoken.id] = honeytoken
                imported_count += 1

            logger.info(f"Imported {imported_count} honeytokens")

        except Exception as e:
            logger.error(f"Failed to import honeytokens: {e}")
            raise

    def cleanup_expired_honeytokens(self) -> int:
        """Remove expired honeytokens"""
        now = datetime.utcnow()
        expired = []

        for honeytoken_id, honeytoken in self.honeytokens.items():
            if (
                honeytoken.expires_at
                and datetime.fromisoformat(honeytoken.expires_at) < now
            ):
                expired.append(honeytoken_id)

        for honeytoken_id in expired:
            del self.honeytokens[honeytoken_id]

        logger.info(f"Cleaned up {len(expired)} expired honeytokens")
        return len(expired)

    def get_trip_alerts(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get trip alerts with optional filtering"""
        alerts = self.trip_alerts

        if tenant_id:
            alerts = [alert for alert in alerts if alert["tenant"] == tenant_id]

        if start_time:
            alerts = [
                alert
                for alert in alerts
                if datetime.fromisoformat(alert["timestamp"]) >= start_time
            ]

        if end_time:
            alerts = [
                alert
                for alert in alerts
                if datetime.fromisoformat(alert["timestamp"]) <= end_time
            ]

        return alerts


def main():
    """Example usage of the HoneytokenGenerator"""

    # Initialize generator
    generator = HoneytokenGenerator()

    # Register tenants
    acme_tenant = TenantData(
        tenant_id="acme_corp",
        name="ACME Corporation",
        data_classifications=["pii_masked", "pii_raw", "secret", "internal"],
        honeytoken_types=["email", "url", "api_key", "database", "file_path"],
        pii_fields=["email", "phone", "ssn"],
        secret_fields=["api_keys", "passwords", "tokens"],
        internal_fields=["employee_id", "department", "salary"],
    )

    globex_tenant = TenantData(
        tenant_id="globex_inc",
        name="Globex Inc",
        data_classifications=["pii_masked", "secret", "internal"],
        honeytoken_types=["email", "api_key", "database"],
        pii_fields=["email", "name"],
        secret_fields=["api_keys", "access_tokens"],
        internal_fields=["user_id", "role"],
    )

    generator.register_tenant(acme_tenant)
    generator.register_tenant(globex_tenant)

    # Generate honeytokens
    acme_tokens = generator.generate_honeytokens_for_tenant("acme_corp", 15)
    globex_tokens = generator.generate_honeytokens_for_tenant("globex_inc", 10)

    # Simulate some honeytoken trips
    print("Simulating honeytoken trips...")
    generator.check_honeytoken_trip(
        acme_tokens[0].value,
        {
            "source_ip": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "endpoint": "/api/users",
            "user_id": "attacker_123",
        },
    )

    # Get statistics
    stats = generator.get_honeytoken_stats()
    print(f"\nHoneytoken Statistics:")
    print(json.dumps(stats, indent=2))

    # Export honeytokens
    export_data = generator.export_honeytokens()
    print(f"\nExported {len(export_data)} characters of honeytoken data")

    # Get trip alerts
    alerts = generator.get_trip_alerts()
    print(f"\nTrip Alerts: {len(alerts)}")
    for alert in alerts:
        print(
            f"  - {alert['timestamp']}: {alert['honeytoken_id']} tripped by {alert['context'].get('source_ip', 'unknown')}"
        )


if __name__ == "__main__":
    main()
