# LangChain Agent Integration

This directory contains LangChain-based agent implementations for the Provability Fabric testbed.

## Structure

- `chains/` - LangChain chain definitions
- `agents/` - LangChain agent implementations
- `tools/` - Custom tools and functions
- `memory/` - Conversation and context memory
- `config/` - Agent configuration files

## Usage

```python
from testbed.agents.langchain import create_agent

# Create a LangChain agent
agent = create_agent(
    name="expense_agent",
    tools=["expense_system", "approval_workflow"],
    memory="conversation_buffer"
)

# Run the agent
result = await agent.run("Process expense report for travel")
```

## Integration with PF

- **Capability Verification**: Agents verify capabilities before execution
- **Receipt Generation**: All operations generate signed access receipts
- **Policy Enforcement**: Kernel decisions enforced through tool broker
- **Audit Trail**: Complete trace of agent decisions and actions
