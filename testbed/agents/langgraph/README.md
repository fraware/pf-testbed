# LangGraph Agent Integration

This directory contains LangGraph-based agent implementations for the Provability Fabric testbed.

## Structure

- `agents/` - LangGraph agent definitions
- `workflows/` - Multi-agent workflow orchestration
- `tools/` - Custom tools and functions
- `config/` - Agent configuration files

## Usage

```python
from testbed.agents.langgraph import create_agent

# Create a LangGraph agent
agent = create_agent(
    name="support_agent",
    tools=["knowledge_base", "ticket_system"],
    workflow="support_triage"
)

# Run the agent
result = await agent.run("User needs help with login issues")
```

## Integration with PF

- **Capability Verification**: Agents verify capabilities before execution
- **Receipt Generation**: All operations generate signed access receipts
- **Policy Enforcement**: Kernel decisions enforced through tool broker
- **Audit Trail**: Complete trace of agent decisions and actions
