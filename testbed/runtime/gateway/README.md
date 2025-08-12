# Provability Fabric Testbed - Agent-Zoo Gateway

## Overview

The Agent-Zoo Gateway is a unified interface that routes requests to different AI agent stacks (OpenAI Assistants, LangChain, LangGraph, DSPy) while providing normalized trace export and comparable metrics across all platforms.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTTP Client   │───▶│  UnifiedGateway  │───▶│  Agent Runners  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Normalized      │
                       │  Trace Export    │
                       └──────────────────┘
```

### Components

- **UnifiedGateway**: Central routing and orchestration
- **Agent Runners**: Platform-specific implementations
- **Normalized Traces**: Consistent schema across all stacks
- **Metrics Collection**: Comparable performance data
- **Capability Management**: Security and access control

## Supported Agent Stacks

1. **OpenAI Assistants** - GPT-4 with function calling
2. **LangChain** - Modular AI application framework
3. **LangGraph** - Stateful, multi-actor applications
4. **DSPy** - Declarative, modular AI systems

## Supported Journeys

- `support_triage` - Customer support workflow
- `expense_approval` - Financial approval process
- `sales_outreach` - Sales and marketing automation
- `hr_onboarding` - Human resources workflow
- `dev_triage` - Development issue management

## Supported Tools

- `slack` - Team communication
- `email` - Email management
- `calendar` - Event scheduling
- `notion` - Document management
- `stripe` - Payment processing
- `github` - Code repository management
- `search` - Web search capabilities
- `fetch` - API data retrieval

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn
- OpenAI API key (for OpenAI Assistants)
- Environment configuration

### Installation

```bash
cd testbed/runtime/gateway
npm install
```

### Environment Configuration

Copy `env.example` to `.env` and configure:

```bash
# Gateway Configuration
GATEWAY_PORT=3000
GATEWAY_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Provability Fabric Mode
PF_ENFORCE=false  # Set to 'true' for enforcement mode

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4

# LangChain Configuration
LANGCHAIN_API_KEY=your-langchain-api-key
LANGCHAIN_MODEL=gpt-4

# LangGraph Configuration
LANGGRAPH_API_KEY=your-langgraph-api-key
LANGGRAPH_MODEL=gpt-4

# DSPy Configuration
DSPY_API_KEY=your-dspy-api-key
DSPY_MODEL=gpt-4
```

### Build and Run

```bash
# Build TypeScript
npm run build

# Start in development mode
npm run dev

# Start in production mode
npm start
```

## Usage

### Starting the Gateway

```bash
npm run dev
```

The gateway will start on the configured port with all agent stacks initialized.

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Execute Plan
```bash
POST /execute/:stack
Content-Type: application/json

{
  "plan": {
    "id": "plan-123",
    "tenant": "acme",
    "journey": "support_triage",
    "steps": [...],
    "metadata": {...}
  },
  "context": {
    "tenant": "acme",
    "session_id": "session-123",
    "request_id": "req-123"
  }
}
```

#### Get Metrics
```bash
GET /metrics          # All stacks
GET /metrics/:stack   # Specific stack
```

#### Export Traces
```bash
GET /traces/:journey/:tenant
```

#### Configuration
```bash
GET /config
```

#### Observability
```bash
GET /observability
```

### Example Plan Execution

```typescript
import { UnifiedGateway } from './src/unified-gateway';

const gateway = new UnifiedGateway(config);

const plan = {
  id: 'support-plan-1',
  tenant: 'acme',
  journey: 'support_triage',
  steps: [
    {
      id: 'step-1',
      type: 'tool_call',
      tool: 'slack',
      parameters: { channel: 'support', message: 'New ticket created' },
      capability: 'write',
      status: 'pending',
      timestamp: new Date().toISOString()
    }
  ],
  metadata: {
    version: '1.0.0',
    agent: 'openai-assistants',
    model: 'gpt-4',
    confidence: 0.9,
    risk_level: 'low',
    tags: ['support', 'automation'],
    context: { priority: 'high' }
  },
  timestamp: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
};

const context = {
  tenant: 'acme',
  session_id: 'session-123',
  request_id: 'req-456',
  timestamp: new Date().toISOString(),
  metadata: { user_id: 'user-789' }
};

const result = await gateway.executePlan('openai-assistants', plan, context);
console.log('Execution result:', result);
```

## Normalized Trace Export

All agent stacks export traces in a consistent format:

```typescript
interface NormalizedTrace {
  plan_id: string;
  agent_stack: string;
  journey: string;
  tenant: string;
  steps: NormalizedStep[];
  receipts: string[];
  cert_id: string;
  timings: {
    plan_start: string;
    plan_end: string;
    total_duration_ms: number;
    step_durations: Record<string, number>;
  };
  metadata: {
    model: string;
    confidence: number;
    risk_level: string;
    capabilities_used: string[];
    shadow_mode: boolean;
    enforce_policies: boolean;
  };
}
```

## Capability Management

The gateway enforces capability-based access control:

- **Shadow Mode** (`PF_ENFORCE=false`): Simulates execution without real side effects
- **Enforce Mode** (`PF_ENFORCE=true`): Enforces policies and executes real actions

Each tool call requires a valid capability token that matches the requested operation.

## Testing

### Run All Tests
```bash
npm test
```

### Run Specific Test Suite
```bash
npm test -- --testNamePattern="Agent-Zoo Connectors"
```

### Test Coverage
```bash
npm run test:coverage
```

### Performance Testing
```bash
npm run test:perf
```

## Performance Requirements

- **Average Execution Time**: < 10 seconds per plan
- **Total Test Suite Time**: < 60 seconds for all stacks
- **Individual Execution**: < 15 seconds per stack
- **Memory Usage**: < 512MB per agent instance
- **Concurrent Plans**: Support for 100+ active plans

## Monitoring and Observability

### Metrics Collected

- Execution time per stack and journey
- Success/failure rates
- Tool usage patterns
- Capability consumption
- Resource utilization

### Health Checks

- Agent stack availability
- API endpoint responsiveness
- Memory and CPU usage
- Error rate monitoring

### Logging

- Structured JSON logging
- Request/response tracing
- Error context preservation
- Performance timing data

## Security Features

- **Capability Validation**: All tool calls require valid capabilities
- **Tenant Isolation**: Strict separation between tenants
- **Input Validation**: Comprehensive plan and context validation
- **Rate Limiting**: Configurable request throttling
- **Audit Trails**: Complete execution history with receipts

## Troubleshooting

### Common Issues

1. **Agent Initialization Failed**
   - Check API keys and configuration
   - Verify network connectivity
   - Check environment variables

2. **Plan Execution Timeout**
   - Increase timeout configuration
   - Check agent stack health
   - Monitor resource usage

3. **Capability Errors**
   - Verify capability tokens
   - Check enforce mode setting
   - Validate tool permissions

### Debug Mode

Enable debug logging:

```bash
DEBUG=pf-gateway:* npm run dev
```

### Health Check

```bash
curl http://localhost:3000/health
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure backward compatibility
5. Follow security best practices

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting guide
- Review the test suite for examples
- Consult the API documentation
