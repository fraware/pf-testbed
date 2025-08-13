# BYO-Agent Quickstart Guide

**Goal: Partners onboard fast (2-hour path)**

This guide will help you integrate your own AI agent with the Provability Fabric Testbed in under 2 hours, without requiring assistance from our team.

## Quick Start Overview

1. **Environment Setup** (15 min)
2. **Tenant Provisioning** (15 min)
3. **Agent Integration** (45 min)
4. **First Journey** (30 min)
5. **Testing & Validation** (15 min)

**Total Time: ~2 hours**

## Prerequisites

- Node.js 18+ or Python 3.8+
- Git
- Basic understanding of REST APIs
- Your AI agent (any framework: LangChain, LangGraph, DSPy, OpenAI Assistants, etc.)

## Step 1: Environment Setup (15 min)

### 1.1 Clone the Repository

```bash
git clone https://github.com/provability-fabric/pf-testbed.git
cd pf-testbed
```

### 1.2 Install Dependencies

**Node.js:**
```bash
npm install
```

**Python:**
```bash
pip install -r requirements.txt
```

### 1.3 Start the Testbed

```bash
# Start all services
make up

# Wait for services to be ready (check with)
make status
```

**Expected Output:**
```
✅ All services are running
- Gateway: http://localhost:3003 ✅
- Ingress: http://localhost:3001 ✅
- Grafana: http://localhost:3100 ✅
- Prometheus: http://localhost:9090 ✅
```

## Step 2: Tenant Provisioning (15 min)

### 2.1 Create Your Tenant

The testbed supports multi-tenancy. You'll be assigned a unique tenant ID and credentials.

**Option A: Self-Service (Recommended)**
```bash
curl -X POST http://localhost:3001/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Company",
    "contact_email": "your-email@company.com",
    "plan": "developer"
  }'
```

**Option B: Use Existing Tenant**
```bash
# ACME Corp (for testing)
TENANT_ID="acme"
API_KEY="acme_dev_key_123"

# Globex Corp (for testing)  
TENANT_ID="globex"
API_KEY="globex_dev_key_456"
```

### 2.2 Get Your Credentials

```bash
curl -X GET http://localhost:3001/tenants/your-tenant-id \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "tenant_id": "your-tenant-id",
  "api_key": "your_api_key_here",
  "capabilities": ["slack", "email", "calendar", "notion", "stripe", "github", "search", "fetch"],
  "rate_limits": {
    "requests_per_minute": 100,
    "concurrent_requests": 10
  }
}
```

## Step 3: Agent Integration (45 min)

### 3.1 Choose Your Integration Method

#### Option A: Node.js/TypeScript (Recommended)

Create `your-agent.ts`:

```typescript
import { createEmulatorFactory } from './testbed/tools/emulators';

interface AgentRequest {
  message: string;
  context?: any;
}

interface AgentResponse {
  response: string;
  actions: any[];
  metadata: {
    tenant: string;
    capabilities_used: string[];
    processing_time_ms: number;
  };
}

export class YourAgent {
  private emulators: any;
  private tenant: string;
  private apiKey: string;

  constructor(tenant: string, apiKey: string) {
    this.tenant = tenant;
    this.apiKey = apiKey;
    
    // Initialize tool emulators
    this.emulators = createEmulatorFactory({
      seed: 'your-seed',
      enforceMode: true,
      capabilityToken: apiKey,
      tenant: tenant
    }).createAllEmulators();
  }

  async processRequest(request: AgentRequest): Promise<AgentResponse> {
    const startTime = Date.now();

    try {
      // Your agent logic here
      const response = await this.analyzeAndRespond(request);
      
      // Use tools through emulators
      const actions = await this.executeActions(response.actions);

      return {
        response: response.text,
        actions: actions,
        metadata: {
          tenant: this.tenant,
          capabilities_used: response.capabilities_used,
          processing_time_ms: Date.now() - startTime
        }
      };

    } catch (error) {
      throw new Error(`Agent processing failed: ${error.message}`);
    }
  }

  private async analyzeAndRespond(request: AgentRequest) {
    // Implement your agent's core logic here
    // This is where you'd integrate with your AI model
    
    if (request.message.includes('send email')) {
      return {
        text: 'I\'ll send an email for you.',
        actions: [{ type: 'send_email', to: 'user@example.com', subject: 'Test' }],
        capabilities_used: ['email']
      };
    }

    if (request.message.includes('schedule meeting')) {
      return {
        text: 'I\'ll schedule a meeting.',
        actions: [{ type: 'create_calendar_event', title: 'Team Meeting' }],
        capabilities_used: ['calendar']
      };
    }

    return {
      text: 'I understand your request. How can I help?',
      actions: [],
      capabilities_used: []
    };
  }

  private async executeActions(actions: any[]) {
    const results = [];

    for (const action of actions) {
      try {
        switch (action.type) {
          case 'send_email':
            const emailResult = await this.emulators.email.sendEmail({
              to: [action.to],
              subject: action.subject,
              body: action.body || 'Message from your agent',
              from: 'agent@yourcompany.com',
              tenant: this.tenant,
              capability_token: this.apiKey,
              enforce: true
            });
            results.push({ action: 'send_email', success: emailResult.success });

          case 'create_calendar_event':
            const calendarResult = await this.emulators.calendar.createEvent({
              title: action.title,
              start_time: action.start_time || new Date(Date.now() + 3600000).toISOString(),
              end_time: action.end_time || new Date(Date.now() + 7200000).toISOString(),
              tenant: this.tenant,
              capability_token: this.apiKey,
              enforce: true
            });
            results.push({ action: 'create_calendar_event', success: calendarResult.success });

          default:
            results.push({ action: action.type, success: false, error: 'Unknown action type' });
        }
      } catch (error) {
        results.push({ action: action.type, success: false, error: error.message });
      }
    }

    return results;
  }
}
```

#### Option B: Python

Create `your_agent.py`:

```python
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime, timedelta

class YourAgent:
    def __init__(self, tenant: str, api_key: str):
        self.tenant = tenant
        self.api_key = api_key
        self.base_url = "http://localhost:3003"
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        start_time = datetime.now()
        
        try:
            # Your agent logic here
            response = await self.analyze_and_respond(request)
            
            # Use tools through the gateway
            actions = await self.execute_actions(response['actions'])
            
            return {
                'response': response['text'],
                'actions': actions,
                'metadata': {
                    'tenant': self.tenant,
                    'capabilities_used': response['capabilities_used'],
                    'processing_time_ms': int((datetime.now() - start_time).total_seconds() * 1000)
                }
            }
            
        except Exception as error:
            raise Exception(f"Agent processing failed: {str(error)}")
    
    async def analyze_and_respond(self, request: Dict[str, Any]) -> Dict[str, Any]:
        message = request.get('message', '').lower()
        
        if 'send email' in message:
            return {
                'text': "I'll send an email for you.",
                'actions': [{'type': 'send_email', 'to': 'user@example.com', 'subject': 'Test'}],
                'capabilities_used': ['email']
            }
        
        if 'schedule meeting' in message:
            return {
                'text': "I'll schedule a meeting.",
                'actions': [{'type': 'create_calendar_event', 'title': 'Team Meeting'}],
                'capabilities_used': ['calendar']
            }
        
        return {
            'text': "I understand your request. How can I help?",
            'actions': [],
            'capabilities_used': []
        }
    
    async def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        
        for action in actions:
            try:
                if action['type'] == 'send_email':
                    # Call email service through gateway
                    result = await self.call_gateway('email/send', {
                        'to': [action['to']],
                        'subject': action['subject'],
                        'body': action.get('body', 'Message from your agent'),
                        'from': 'agent@yourcompany.com'
                    })
                    results.append({'action': 'send_email', 'success': result.get('success', False)})
                
                elif action['type'] == 'create_calendar_event':
                    # Call calendar service through gateway
                    result = await self.call_gateway('calendar/create', {
                        'title': action['title'],
                        'start_time': action.get('start_time', (datetime.now() + timedelta(hours=1)).isoformat()),
                        'end_time': action.get('end_time', (datetime.now() + timedelta(hours=2)).isoformat())
                    })
                    results.append({'action': 'create_calendar_event', 'success': result.get('success', False)})
                
                else:
                    results.append({'action': action['type'], 'success': False, 'error': 'Unknown action type'})
                    
            except Exception as error:
                results.append({'action': action['type'], 'success': False, 'error': str(error)})
        
        return results
    
    async def call_gateway(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # This would be an actual HTTP call to the gateway
        # For now, we'll simulate success
        return {'success': True, 'data': data}

# Usage example
async def main():
    agent = YourAgent(tenant="your-tenant-id", api_key="your-api-key")
    
    result = await agent.process_request({
        'message': 'Please send an email to the team about tomorrow\'s meeting'
    })
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 Test Your Agent

```bash
# Node.js
npm run build
node dist/your-agent.js

# Python
python your_agent.py
```

## Step 4: First Journey (30 min)

### 4.1 Run a Complete User Journey

Create `test_journey.js`:

```javascript
import { YourAgent } from './your-agent.js';

async function testJourney() {
  const agent = new YourAgent('your-tenant-id', 'your-api-key');
  
  console.log('🚀 Starting user journey test...\n');
  
  // Test 1: Email request
  console.log('📧 Test 1: Email Request');
  const emailResult = await agent.processRequest({
    message: 'Send an email to john@company.com about the project update'
  });
  console.log('Result:', JSON.stringify(emailResult, null, 2));
  console.log('');
  
  // Test 2: Calendar request
  console.log('📅 Test 2: Calendar Request');
  const calendarResult = await agent.processRequest({
    message: 'Schedule a meeting with the development team for tomorrow at 2 PM'
  });
  console.log('Result:', JSON.stringify(calendarResult, null, 2));
  console.log('');
  
  // Test 3: Complex request
  console.log('🔄 Test 3: Complex Request');
  const complexResult = await agent.processRequest({
    message: 'Send an email to the team about the meeting I just scheduled, and create a Notion page with the agenda'
  });
  console.log('Result:', JSON.stringify(complexResult, null, 2));
  
  console.log('\n✅ Journey test completed!');
}

testJourney().catch(console.error);
```

### 4.2 Expected Output

```
🚀 Starting user journey test...

📧 Test 1: Email Request
Result: {
  "response": "I'll send an email about the project update.",
  "actions": [
    {
      "action": "send_email",
      "success": true
    }
  ],
  "metadata": {
    "tenant": "your-tenant-id",
    "capabilities_used": ["email"],
    "processing_time_ms": 245
  }
}

📅 Test 2: Calendar Request
Result: {
  "response": "I'll schedule a meeting with the development team.",
  "actions": [
    {
      "action": "create_calendar_event",
      "success": true
    }
  ],
  "metadata": {
    "tenant": "your-tenant-id",
    "capabilities_used": ["calendar"],
    "processing_time_ms": 312
  }
}

🔄 Test 3: Complex Request
Result: {
  "response": "I'll send the email and create the Notion page with the agenda.",
  "actions": [
    {
      "action": "send_email",
      "success": true
    },
    {
      "action": "create_notion_page",
      "success": true
    }
  ],
  "metadata": {
    "tenant": "your-tenant-id",
    "capabilities_used": ["email", "notion"],
    "processing_time_ms": 567
  }
}

✅ Journey test completed!
```

## Step 5: Testing & Validation (15 min)

### 5.1 Run the Test Suite

```bash
# Run all tests
npm test

# Run specific test categories
npm run test:unit
npm run test:integration
npm run test:e2e
```

### 5.2 Check Observability

Open your browser and navigate to:
- **Grafana Dashboard**: http://localhost:3100 (admin/admin123)
- **Prometheus**: http://localhost:9090

Look for:
- ✅ Your tenant's metrics
- ✅ Successful tool executions
- ✅ Response times within SLA
- ✅ No capability violations

### 5.3 Validate Security

```bash
# Test capability enforcement
curl -X POST http://localhost:3003/email/send \
  -H "Content-Type: application/json" \
  -H "X-PF-Signature: invalid-signature" \
  -d '{"to": ["test@example.com"], "subject": "Test"}'

# Should return 403 with CAP_MISS error
```

## Success Criteria

You've successfully completed the BYO-Agent onboarding if:

- ✅ Your agent can process requests and generate responses
- ✅ Tool calls work through the emulators
- ✅ Capability enforcement is working (invalid tokens rejected)
- ✅ All 3 test journeys complete successfully
- ✅ Metrics appear in Grafana dashboard
- ✅ No security violations in logs

## Next Steps

### Production Deployment

1. **Switch to Real Mode**: Update emulator configuration to use real services
2. **Add Monitoring**: Integrate with your existing observability stack
3. **Scale Up**: Increase rate limits and add more capabilities
4. **Custom Tools**: Implement your own tool emulators

### Advanced Features

1. **Multi-Agent Orchestration**: Coordinate multiple agents
2. **Custom Capabilities**: Define tenant-specific permissions
3. **Audit Logging**: Track all agent decisions and actions
4. **Performance Optimization**: Tune response times and throughput

## Troubleshooting

### Common Issues

**Service Not Starting**
```bash
# Check service status
make status

# View logs
make logs

# Restart services
make restart
```

**Capability Errors**
```bash
# Verify your API key
curl -X GET http://localhost:3001/tenants/your-tenant-id \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check capability validation
npm run test:capabilities
```

**Tool Emulator Issues**
```bash
# Reset emulator state
npm run emulator:reset

# Check emulator configuration
npm run emulator:config
```

### Getting Help

1. **Documentation**: Check the main README and API docs
2. **Issues**: Open a GitHub issue with detailed error logs
3. **Community**: Join our Discord/Slack for real-time support
4. **Support**: Email support@provability-fabric.com for urgent issues

---

**Goal Achieved: You can now run your own AI agent with the Provability Fabric Testbed!**

The testbed provides a secure, observable, and scalable foundation for your AI applications. All tool calls are validated, monitored, and secured through capability-based access control.

**Next milestone**: Complete your first production deployment and start building real-world applications!
