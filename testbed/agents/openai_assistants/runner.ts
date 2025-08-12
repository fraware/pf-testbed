import { BaseAgentRunner } from '../../runtime/gateway/src/base-runner';
import { 
  Plan, 
  PlanStep, 
  ToolCall, 
  ToolResult, 
  ToolTrace,
  AgentConfig,
  SUPPORTED_JOURNEYS,
  SUPPORTED_TOOLS
} from '../../runtime/gateway/src/types';

import OpenAI from 'openai';

/**
 * OpenAI Assistants Agent Runner
 * 
 * This runner integrates with OpenAI's Assistants API to execute plans
 * using GPT models with function calling capabilities.
 */
export class OpenAIAssistantsRunner extends BaseAgentRunner {
  private openai: OpenAI;
  private assistantId: string | null = null;
  private threadId: string | null = null;

  constructor() {
    super(
      'openai-assistants',
      '1.0.0',
      ['read', 'write', 'decision', 'retrieval']
    );
  }

  /**
   * Configure the OpenAI client and create/retrieve assistant
   */
  async configure(config: AgentConfig): Promise<void> {
    await super.configure(config);

    if (!config.api_key) {
      throw new Error('OpenAI API key is required');
    }

    this.openai = new OpenAI({
      apiKey: config.api_key,
      timeout: config.timeout * 1000,
      maxRetries: config.max_retries
    });

    // Create or retrieve assistant
    await this.setupAssistant();
  }

  /**
   * Create or retrieve the OpenAI assistant
   */
  private async setupAssistant(): Promise<void> {
    try {
      // Check if we have a stored assistant ID
      if (this.assistantId) {
        try {
          await this.openai.beta.assistants.retrieve(this.assistantId);
          return;
        } catch {
          // Assistant not found, create new one
        }
      }

      // Create new assistant
      const assistant = await this.openai.beta.assistants.create({
        name: 'Provability Fabric Testbed Agent',
        instructions: this.getAssistantInstructions(),
        model: this.config.model || 'gpt-4-turbo-preview',
        tools: this.getToolDefinitions()
      });

      this.assistantId = assistant.id;
      console.log(`Created OpenAI assistant: ${this.assistantId}`);

    } catch (error) {
      throw new Error(`Failed to setup OpenAI assistant: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get the system instructions for the assistant
   */
  private getAssistantInstructions(): string {
    return `
You are a Provability Fabric Testbed agent that executes plans for various business journeys.

Supported journeys:
${SUPPORTED_JOURNEYS.map(j => `- ${j}`).join('\n')}

Supported tools:
${SUPPORTED_TOOLS.map(t => `- ${t}`).join('\n')}

Your role is to:
1. Understand the plan and break it down into executable steps
2. Execute each step using the appropriate tools
3. Maintain context and state throughout the execution
4. Handle errors gracefully and provide meaningful feedback
5. Ensure all operations comply with security and privacy requirements

Always validate capabilities before using tools and maintain proper audit trails.
    `.trim();
  }

  /**
   * Get the tool definitions for OpenAI function calling
   */
  private getToolDefinitions(): any[] {
    return [
      {
        type: 'function',
        function: {
          name: 'execute_tool',
          description: 'Execute a tool with the given parameters',
          parameters: {
            type: 'object',
            properties: {
              tool: {
                type: 'string',
                enum: SUPPORTED_TOOLS,
                description: 'The tool to execute'
              },
              parameters: {
                type: 'object',
                description: 'Parameters for the tool'
              },
              capability: {
                type: 'string',
                description: 'Required capability to execute this tool'
              }
            },
            required: ['tool', 'parameters', 'capability']
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'make_decision',
          description: 'Make a decision based on available information',
          parameters: {
            type: 'object',
            properties: {
              decision: {
                type: 'string',
                description: 'The decision to make'
              },
              reasoning: {
                type: 'string',
                description: 'Reasoning behind the decision'
              },
              confidence: {
                type: 'number',
                minimum: 0,
                maximum: 1,
                description: 'Confidence level (0-1)'
              }
            },
            required: ['decision', 'reasoning', 'confidence']
          }
        }
      }
    ];
  }

  /**
   * Create a plan from JSON input
   */
  async plan(json: any): Promise<Plan> {
    try {
      // Validate input
      if (!json.journey || !json.tenant) {
        throw new Error('Journey and tenant are required');
      }

      // Create plan structure
      const plan: Plan = {
        id: this.generateId(),
        tenant: json.tenant,
        journey: json.journey,
        steps: [],
        metadata: {
          version: '1.0',
          agent: this.name,
          model: this.config.model || 'gpt-4-turbo-preview',
          confidence: json.confidence || 0.8,
          risk_level: json.risk_level || 'medium',
          tags: json.tags || [],
          context: json.context || {}
        },
        timestamp: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours
      };

      // Create thread for this plan
      const thread = await this.openai.beta.threads.create();
      this.threadId = thread.id;

      // Add initial message
      await this.openai.beta.threads.messages.create(this.threadId, {
        role: 'user',
        content: `Execute the following plan for ${json.journey} journey in tenant ${json.tenant}:\n\n${JSON.stringify(json, null, 2)}`
      });

      // Run the assistant
      const run = await this.openai.beta.threads.runs.create(this.threadId, {
        assistant_id: this.assistantId!
      });

      // Wait for completion
      await this.waitForRunCompletion(run.id);

      // Get messages and convert to plan steps
      const messages = await this.openai.beta.threads.messages.list(this.threadId);
      plan.steps = this.convertMessagesToSteps(messages.data);

      return plan;

    } catch (error) {
      throw new Error(`Failed to create plan: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Wait for a run to complete
   */
  private async waitForRunCompletion(runId: string): Promise<void> {
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes with 5-second intervals

    while (attempts < maxAttempts) {
      const run = await this.openai.beta.threads.runs.retrieve(this.threadId!, runId);
      
      if (run.status === 'completed') {
        return;
      } else if (run.status === 'failed' || run.status === 'cancelled') {
        throw new Error(`Run failed with status: ${run.status}`);
      } else if (run.status === 'requires_action') {
        // Handle tool calls
        await this.handleToolCalls(run);
      }

      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
      attempts++;
    }

    throw new Error('Run timed out');
  }

  /**
   * Handle tool calls from the assistant
   */
  private async handleToolCalls(run: any): Promise<void> {
    if (run.required_action?.type === 'submit_tool_outputs') {
      const toolCalls = run.required_action.submit_tool_outputs.tool_calls;
      const toolOutputs = [];

      for (const toolCall of toolCalls) {
        try {
          const output = await this.executeTool({
            id: toolCall.id,
            tool: toolCall.function.name,
            parameters: JSON.parse(toolCall.function.arguments),
            capability: 'read', // Default capability
            timestamp: new Date().toISOString(),
            tenant: 'acme' // Default tenant
          });

          toolOutputs.push({
            tool_call_id: toolCall.id,
            output: JSON.stringify(output.result)
          });
        } catch (error) {
          toolOutputs.push({
            tool_call_id: toolCall.id,
            output: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
          });
        }
      }

      // Submit tool outputs
      await this.openai.beta.threads.runs.submitToolOutputs(this.threadId!, run.id, {
        tool_outputs: toolOutputs
      });
    }
  }

  /**
   * Convert OpenAI messages to plan steps
   */
  private convertMessagesToSteps(messages: any[]): PlanStep[] {
    const steps: PlanStep[] = [];
    
    for (const message of messages) {
      if (message.role === 'assistant' && message.content) {
        for (const content of message.content) {
          if (content.type === 'text') {
            steps.push({
              id: this.generateId(),
              type: 'decision',
              status: 'completed',
              timestamp: new Date(message.created_at * 1000).toISOString(),
              result: content.text.value
            });
          }
        }
      }
    }

    return steps;
  }

  /**
   * Execute a tool call
   */
  async executeTool(call: ToolCall): Promise<ToolResult> {
    try {
      // Validate capability
      this.validateCapability(call.capability, this.capabilities);

      // Create tool trace
      const trace: ToolTrace = {
        id: this.generateId(),
        tool_call_id: call.id,
        inputs: call.parameters,
        outputs: {},
        metadata: {
          tool: call.tool,
          capability: call.capability,
          tenant: call.tenant,
          timestamp: call.timestamp
        },
        replayable: true
      };

      // Execute tool based on type
      let result: any;
      switch (call.tool) {
        case 'slack':
          result = await this.executeSlackTool(call.parameters);
          break;
        case 'email':
          result = await this.executeEmailTool(call.parameters);
          break;
        case 'calendar':
          result = await this.executeCalendarTool(call.parameters);
          break;
        case 'notion':
          result = await this.executeNotionTool(call.parameters);
          break;
        case 'stripe':
          result = await this.executeStripeTool(call.parameters);
          break;
        case 'github':
          result = await this.executeGithubTool(call.parameters);
          break;
        case 'search':
          result = await this.executeSearchTool(call.parameters);
          break;
        case 'fetch':
          result = await this.executeFetchTool(call.parameters);
          break;
        default:
          throw new Error(`Unsupported tool: ${call.tool}`);
      }

      // Update trace with outputs
      trace.outputs = result;

      return {
        id: this.generateId(),
        success: true,
        result,
        capability_consumed: call.capability,
        trace,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      return {
        id: this.generateId(),
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        capability_consumed: call.capability,
        trace: {
          id: this.generateId(),
          tool_call_id: call.id,
          inputs: call.parameters,
          outputs: {},
          metadata: {
            tool: call.tool,
            capability: call.capability,
            tenant: call.tenant,
            timestamp: call.timestamp,
            error: error instanceof Error ? error.message : 'Unknown error'
          },
          replayable: false
        },
        timestamp: new Date().toISOString()
      };
    }
  }

  // Tool execution methods (implemented as stubs for now)
  private async executeSlackTool(params: any): Promise<any> {
    // TODO: Implement Slack integration
    return { message: 'Slack message sent', channel: params.channel };
  }

  private async executeEmailTool(params: any): Promise<any> {
    // TODO: Implement email integration
    return { message: 'Email sent', to: params.to };
  }

  private async executeCalendarTool(params: any): Promise<any> {
    // TODO: Implement calendar integration
    return { event: 'Calendar event created', time: params.time };
  }

  private async executeNotionTool(params: any): Promise<any> {
    // TODO: Implement Notion integration
    return { page: 'Notion page created', title: params.title };
  }

  private async executeStripeTool(params: any): Promise<any> {
    // TODO: Implement Stripe integration
    return { payment: 'Payment processed', amount: params.amount };
  }

  private async executeGithubTool(params: any): Promise<any> {
    // TODO: Implement GitHub integration
    return { issue: 'GitHub issue created', title: params.title };
  }

  private async executeSearchTool(params: any): Promise<any> {
    // TODO: Implement search integration
    return { results: 'Search results', query: params.query };
  }

  private async executeFetchTool(params: any): Promise<any> {
    // TODO: Implement fetch integration
    return { data: 'Data fetched', url: params.url };
  }
}
