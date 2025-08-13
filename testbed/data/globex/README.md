# Globex Corporation Data

Tenant data structure for Globex Corporation, a fictional manufacturing company.

## Structure

- `kb/` - Knowledge base articles and documentation
- `seeds/` - Seed data for testing and development

## Knowledge Base

The knowledge base contains:

- Manufacturing procedures
- Safety guidelines
- Quality control documentation
- Equipment manuals
- Training materials

## Seed Data

Seed data includes:

- Sample employee records
- Test safety incidents
- Mock quality reports
- Example maintenance requests
- Onboarding scenarios

## Data Isolation

- **Physical Partitioning**: Separate storage for Globex data
- **Access Control**: Tenant-specific access policies
- **Audit Logging**: Complete access audit trail
- **Receipt Generation**: Signed receipts for all data access

## Usage

```typescript
import { GlobexDataStore } from "./globex-store";

const store = new GlobexDataStore({
  tenant: "globex",
  isolation: "strict",
  audit: true,
});

// Access is automatically logged and receipted
const data = await store.query({
  table: "safety_incidents",
  filters: { status: "investigating" },
});
```
