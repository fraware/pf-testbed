# Egress Firewall Runtime

Content egress firewall that prevents output leaks and emits Egress Certificates.

## Architecture

The egress firewall implements a multi-stage pipeline:

1. **Aho-Corasick Pattern Matching** - Fast pattern detection
2. **Format/Entropy Analysis** - Detect structured data leaks
3. **SimHash** - Near-duplicate detection
4. **MinHash** - Optional similarity analysis
5. **LLM Analysis** - Ambiguous case resolution

## Certificate Schema

```json
{
  "pii": "detected|none|masked",
  "secrets": "detected|none|masked", 
  "near_dupe": "detected|none",
  "non_interference": "passed|failed",
  "influencing_labels": ["label1", "label2"],
  "policy_hash": "sha256:...",
  "text_hash": "sha256:...",
  "attestation_ref": "ref:...",
  "sig": "ed25519:..."
}
```

## Usage

```typescript
import { EgressFirewall } from './egress-firewall';

const firewall = new EgressFirewall({
  patterns: ['ssn', 'credit_card', 'api_key'],
  policies: ['pii_protection', 'secret_handling'],
  llmProvider: 'openai'
});

const result = await firewall.process({
  content: userInput,
  tenant: 'acme',
  context: 'support_chat'
});

if (result.certificate.non_interference === 'failed') {
  throw new Error('Content blocked by egress firewall');
}
```

## Performance Targets

- **Latency**: P95 < 400ms
- **Accuracy**: 0 critical PII/secret leaks in 50k adversarial turns
- **Throughput**: 1000+ requests/second
