# DSPy Agent Integration

This directory contains DSPy-based agent implementations for the Provability Fabric testbed.

## Structure

- `modules/` - DSPy module definitions
- `agents/` - DSPy agent implementations
- `optimizers/` - Prompt optimization strategies
- `config/` - Agent configuration files

## Usage

```python
from testbed.agents.dspy import create_agent

# Create a DSPy agent
agent = create_agent(
    name="sales_agent",
    modules=["lead_qualification", "proposal_generation"],
    optimizer="bootstrap"
)

# Run the agent
result = await agent.run("Qualify lead from marketing campaign")
```

## Integration with PF

- **Capability Verification**: Agents verify capabilities before execution
- **Receipt Generation**: All operations generate signed access receipts
- **Policy Enforcement**: Kernel decisions enforced through tool broker
- **Audit Trail**: Complete trace of agent decisions and actions
