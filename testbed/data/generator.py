#!/usr/bin/env python3
"""
Data Generator for Provability Fabric Testbed

Generates synthetic PII/financial documents with honeytokens for testing
tenant isolation and data security.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import faker
from faker.providers import (
    internet,
    company,
    person,
    address,
    phone_number,
    ssn,
    credit_card,
)


@dataclass
class Honeytoken:
    """Represents a honeytoken that should trigger alerts if accessed"""

    id: str
    type: str
    value: str
    tenant: str
    created_at: str
    expires_at: str
    trigger_conditions: List[str]
    alert_severity: str


@dataclass
class DataDocument:
    """Represents a synthetic document with labels and metadata"""

    id: str
    tenant: str
    content: Dict[str, Any]
    labels: Dict[str, str]
    metadata: Dict[str, Any]
    created_at: str
    honeytokens: List[str]  # List of honeytoken IDs embedded


class DataGenerator:
    """Generates synthetic data with honeytokens for testbed"""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or random.randint(1, 1000000)
        random.seed(self.seed)

        # Initialize Faker with seed
        self.fake = faker.Faker()
        self.fake.seed_instance(self.seed)

        # Add providers
        self.fake.add_provider(internet)
        self.fake.add_provider(company)
        self.fake.add_provider(person)
        self.fake.add_provider(address)
        self.fake.add_provider(phone_number)
        self.fake.add_provider(ssn)
        self.fake.add_provider(credit_card)

        # Honeytoken registry
        self.honeytokens: Dict[str, Honeytoken] = {}

        # Tenant configurations
        self.tenants = {
            "acme": {
                "company_name": "ACME Corporation",
                "domain": "acme.com",
                "industry": "Software",
                "employee_count": 500,
                "locations": ["San Francisco", "New York", "London"],
            },
            "globex": {
                "company_name": "Globex Industries",
                "domain": "globex.com",
                "industry": "Manufacturing",
                "employee_count": 1200,
                "locations": ["Detroit", "Shanghai", "Berlin"],
            },
        }

    def generate_honeytokens(self, tenant: str, count: int = 10) -> List[Honeytoken]:
        """Generate honeytokens for a specific tenant"""
        honeytokens = []

        for i in range(count):
            token_type = random.choice(
                ["email", "url", "api_key", "credit_card", "ssn", "phone", "address"]
            )

            if token_type == "email":
                value = f"honeypot-{uuid.uuid4().hex[:8]}@{tenant}.com"
            elif token_type == "url":
                value = f"https://{tenant}.com/honeypot/{uuid.uuid4().hex[:8]}"
            elif token_type == "api_key":
                value = f"pk_live_{uuid.uuid4().hex[:24]}"
            elif token_type == "credit_card":
                value = self.fake.credit_card_number()
            elif token_type == "ssn":
                value = self.fake.ssn()
            elif token_type == "phone":
                value = self.fake.phone_number()
            elif token_type == "address":
                value = self.fake.address()
            else:
                value = f"honeypot-{uuid.uuid4().hex[:8]}"

            honeytoken = Honeytoken(
                id=f"ht_{tenant}_{token_type}_{i}",
                type=token_type,
                value=value,
                tenant=tenant,
                created_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(days=90)).isoformat(),
                trigger_conditions=[
                    "cross_tenant_access",
                    "unauthorized_export",
                    "bulk_download",
                ],
                alert_severity="high",
            )

            self.honeytokens[honeytoken.id] = honeytoken
            honeytokens.append(honeytoken)

        return honeytokens

    def generate_employee_data(
        self, tenant: str, count: int = 50
    ) -> List[DataDocument]:
        """Generate synthetic employee data with honeytokens"""
        documents = []

        # Generate honeytokens for this batch
        honeytokens = self.generate_honeytokens(tenant, count // 10)

        for i in range(count):
            # Determine if this document should contain honeytokens
            has_honeytokens = random.random() < 0.1  # 10% chance

            # Generate employee data
            employee = {
                "employee_id": f"{tenant.upper()}{i:04d}",
                "first_name": self.fake.first_name(),
                "last_name": self.fake.last_name(),
                "email": f"{self.fake.user_name()}@{self.tenants[tenant]['domain']}",
                "phone": self.fake.phone_number(),
                "ssn": self.fake.ssn(),
                "address": {
                    "street": self.fake.street_address(),
                    "city": random.choice(self.tenants[tenant]["locations"]),
                    "state": self.fake.state(),
                    "zip": self.fake.zipcode(),
                    "country": "USA",
                },
                "department": random.choice(
                    ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]
                ),
                "title": self.fake.job(),
                "salary": random.randint(50000, 200000),
                "hire_date": self.fake.date_between(
                    start_date="-5y", end_date="today"
                ).isoformat(),
                "manager_id": (
                    f"{tenant.upper()}{random.randint(0, i):04d}" if i > 0 else None
                ),
            }

            # Add honeytokens if needed
            document_honeytokens = []
            if has_honeytokens and honeytokens:
                token = random.choice(honeytokens)
                document_honeytokens.append(token.id)

                # Embed honeytoken in the data
                if token.type == "email":
                    employee["honeypot_email"] = token.value
                elif token.type == "phone":
                    employee["honeypot_phone"] = token.value
                elif token.type == "ssn":
                    employee["honeypot_ssn"] = token.value

            # Create document with labels
            document = DataDocument(
                id=f"emp_{tenant}_{i}",
                tenant=tenant,
                content=employee,
                labels={
                    "tenant": tenant,
                    "pii": "raw",
                    "secret": "none",
                    "internal": "true",
                    "data_type": "employee",
                    "sensitivity": "high",
                },
                metadata={
                    "generator": "testbed-data-generator",
                    "version": "1.0",
                    "seed": self.seed,
                    "batch_id": f"batch_{tenant}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                },
                created_at=datetime.now().isoformat(),
                honeytokens=document_honeytokens,
            )

            documents.append(document)

        return documents

    def generate_financial_data(
        self, tenant: str, count: int = 100
    ) -> List[DataDocument]:
        """Generate synthetic financial data with honeytokens"""
        documents = []

        # Generate honeytokens for this batch
        honeytokens = self.generate_honeytokens(tenant, count // 20)

        for i in range(count):
            # Determine if this document should contain honeytokens
            has_honeytokens = random.random() < 0.05  # 5% chance

            # Generate financial transaction
            transaction = {
                "transaction_id": f"txn_{tenant}_{uuid.uuid4().hex[:8]}",
                "date": self.fake.date_between(
                    start_date="-1y", end_date="today"
                ).isoformat(),
                "amount": round(random.uniform(10.0, 10000.0), 2),
                "currency": "USD",
                "type": random.choice(
                    ["expense", "revenue", "transfer", "refund", "fee"]
                ),
                "category": random.choice(
                    ["Travel", "Office Supplies", "Software", "Marketing", "Training"]
                ),
                "description": self.fake.sentence(),
                "employee_id": f"{tenant.upper()}{random.randint(0, 49):04d}",
                "approver_id": f"{tenant.upper()}{random.randint(0, 49):04d}",
                "status": random.choice(
                    ["pending", "approved", "rejected", "completed"]
                ),
                "receipt_url": f"https://receipts.{tenant}.com/{uuid.uuid4().hex[:8]}",
                "expense_report_id": f"exp_{tenant}_{random.randint(1000, 9999)}",
            }

            # Add honeytokens if needed
            document_honeytokens = []
            if has_honeytokens and honeytokens:
                token = random.choice(honeytokens)
                document_honeytokens.append(token.id)

                # Embed honeytoken in the data
                if token.type == "url":
                    transaction["honeypot_url"] = token.value
                elif token.type == "api_key":
                    transaction["honeypot_api_key"] = token.value

            # Create document with labels
            document = DataDocument(
                id=f"fin_{tenant}_{i}",
                tenant=tenant,
                content=transaction,
                labels={
                    "tenant": tenant,
                    "pii": "masked",
                    "secret": "none",
                    "internal": "true",
                    "data_type": "financial",
                    "sensitivity": "medium",
                },
                metadata={
                    "generator": "testbed-data-generator",
                    "version": "1.0",
                    "seed": self.seed,
                    "batch_id": f"batch_{tenant}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                },
                created_at=datetime.now().isoformat(),
                honeytokens=document_honeytokens,
            )

            documents.append(document)

        return documents

    def generate_customer_data(
        self, tenant: str, count: int = 200
    ) -> List[DataDocument]:
        """Generate synthetic customer data with honeytokens"""
        documents = []

        # Generate honeytokens for this batch
        honeytokens = self.generate_honeytokens(tenant, count // 25)

        for i in range(count):
            # Determine if this document should contain honeytokens
            has_honeytokens = random.random() < 0.08  # 8% chance

            # Generate customer data
            customer = {
                "customer_id": f"cust_{tenant}_{uuid.uuid4().hex[:8]}",
                "company_name": self.fake.company(),
                "contact_person": {
                    "first_name": self.fake.first_name(),
                    "last_name": self.fake.last_name(),
                    "email": self.fake.email(),
                    "phone": self.fake.phone_number(),
                    "title": self.fake.job(),
                },
                "address": {
                    "street": self.fake.street_address(),
                    "city": self.fake.city(),
                    "state": self.fake.state(),
                    "zip": self.fake.zipcode(),
                    "country": self.fake.country(),
                },
                "industry": random.choice(
                    ["Technology", "Healthcare", "Finance", "Manufacturing", "Retail"]
                ),
                "annual_revenue": random.choice(
                    ["Under $1M", "$1M-$10M", "$10M-$100M", "Over $100M"]
                ),
                "customer_since": self.fake.date_between(
                    start_date="-3y", end_date="today"
                ).isoformat(),
                "status": random.choice(["active", "inactive", "prospect"]),
                "last_contact": self.fake.date_between(
                    start_date="-6m", end_date="today"
                ).isoformat(),
            }

            # Add honeytokens if needed
            document_honeytokens = []
            if has_honeytokens and honeytokens:
                token = random.choice(honeytokens)
                document_honeytokens.append(token.id)

                # Embed honeytoken in the data
                if token.type == "email":
                    customer["honeypot_email"] = token.value
                elif token.type == "phone":
                    customer["honeypot_phone"] = token.value
                elif token.type == "url":
                    customer["honeypot_website"] = token.value

            # Create document with labels
            document = DataDocument(
                id=f"cust_{tenant}_{i}",
                tenant=tenant,
                content=customer,
                labels={
                    "tenant": tenant,
                    "pii": "masked",
                    "secret": "none",
                    "internal": "false",
                    "data_type": "customer",
                    "sensitivity": "medium",
                },
                metadata={
                    "generator": "testbed-data-generator",
                    "version": "1.0",
                    "seed": self.seed,
                    "batch_id": f"batch_{tenant}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                },
                created_at=datetime.now().isoformat(),
                honeytokens=document_honeytokens,
            )

            documents.append(document)

        return documents

    def generate_all_data(self) -> Dict[str, Any]:
        """Generate all data types for all tenants"""
        all_data = {}

        for tenant in self.tenants:
            print(f"Generating data for tenant: {tenant}")

            tenant_data = {
                "employees": self.generate_employee_data(tenant),
                "financial": self.generate_financial_data(tenant),
                "customers": self.generate_customer_data(tenant),
            }

            all_data[tenant] = tenant_data

        return all_data

    def save_data(self, data: Dict[str, Any], output_dir: str = "testbed/data"):
        """Save generated data to files"""
        import os

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Save honeytokens
        honeytokens_file = os.path.join(output_dir, "honeytokens.json")
        with open(honeytokens_file, "w") as f:
            json.dump([asdict(ht) for ht in self.honeytokens.values()], f, indent=2)

        print(f"Saved {len(self.honeytokens)} honeytokens to {honeytokens_file}")

        # Save tenant data
        for tenant, tenant_data in data.items():
            tenant_dir = os.path.join(output_dir, tenant)
            os.makedirs(tenant_dir, exist_ok=True)

            for data_type, documents in tenant_data.items():
                filename = os.path.join(tenant_dir, f"{data_type}.json")
                with open(filename, "w") as f:
                    json.dump([asdict(doc) for doc in documents], f, indent=2)

                print(
                    f"Saved {len(documents)} {data_type} documents for {tenant} to {filename}"
                )

        # Save labels configuration
        labels_file = os.path.join(output_dir, "labels.yaml")
        labels_config = {
            "label_schema": {
                "tenant": ["acme", "globex"],
                "pii": ["masked", "raw", "none"],
                "secret": ["none", "low", "medium", "high"],
                "internal": ["true", "false"],
                "data_type": ["employee", "financial", "customer"],
                "sensitivity": ["low", "medium", "high", "critical"],
            },
            "label_rules": {
                "cross_tenant_access": "deny",
                "pii_export": "require_approval",
                "secret_access": "require_capability",
                "bulk_download": "require_approval",
            },
        }

        import yaml

        with open(labels_file, "w") as f:
            yaml.dump(labels_config, f, default_flow_style=False)

        print(f"Saved labels configuration to {labels_file}")

    def get_honeytoken_alerts(self, accessed_tokens: List[str]) -> List[Dict[str, Any]]:
        """Generate alerts for accessed honeytokens"""
        alerts = []

        for token_id in accessed_tokens:
            if token_id in self.honeytokens:
                token = self.honeytokens[token_id]

                alert = {
                    "id": f"alert_{uuid.uuid4().hex[:8]}",
                    "timestamp": datetime.now().isoformat(),
                    "severity": token.alert_severity,
                    "type": "honeytoken_accessed",
                    "honeytoken_id": token_id,
                    "honeytoken_type": token.type,
                    "tenant": token.tenant,
                    "description": f"Honeytoken {token.type} accessed: {token.value}",
                    "trigger_conditions": token.trigger_conditions,
                    "recommended_actions": [
                        "Investigate access pattern",
                        "Check for data exfiltration",
                        "Review access logs",
                        "Consider blocking source",
                    ],
                }

                alerts.append(alert)

        return alerts


def main():
    """Main function to generate test data"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate test data for Provability Fabric Testbed"
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible data")
    parser.add_argument(
        "--output-dir",
        default="testbed/data",
        help="Output directory for generated data",
    )
    parser.add_argument(
        "--tenants",
        nargs="+",
        default=["acme", "globex"],
        help="Tenants to generate data for",
    )

    args = parser.parse_args()

    # Initialize generator
    generator = DataGenerator(seed=args.seed)

    print(f"Generating test data with seed: {generator.seed}")
    print(f"Output directory: {args.output_dir}")
    print(f"Tenants: {', '.join(args.tenants)}")

    # Generate data
    data = generator.generate_all_data()

    # Save data
    generator.save_data(data, args.output_dir)

    print("\nData generation completed!")
    print(f"Total honeytokens: {len(generator.honeytokens)}")

    for tenant in args.tenants:
        if tenant in data:
            total_docs = sum(len(docs) for docs in data[tenant].values())
            print(f"{tenant}: {total_docs} documents")


if __name__ == "__main__":
    main()
