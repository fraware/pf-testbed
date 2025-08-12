# ACME Corporation Data

Tenant data structure for ACME Corporation, a fictional technology company.

## Structure

- `kb/` - Knowledge base articles and documentation
- `seeds/` - Seed data for testing and development

## Knowledge Base

The knowledge base contains:
- Product documentation
- Support articles
- Company policies
- Training materials
- FAQ entries

## Seed Data

Seed data includes:
- Sample user accounts
- Test tickets and cases
- Mock expense reports
- Example sales leads
- Onboarding scenarios

## Data Isolation

- **Physical Partitioning**: Separate storage for ACME data
- **Access Control**: Tenant-specific access policies
- **Audit Logging**: Complete access audit trail
- **Receipt Generation**: Signed receipts for all data access

## Usage

```typescript
import { ACMEDataStore } from './acme-store';

const store = new ACMEDataStore({
  tenant: 'acme',
  isolation: 'strict',
  audit: true
});

// Access is automatically logged and receipted
const data = await store.query({
  table: 'support_tickets',
  filters: { status: 'open' }
});
```
