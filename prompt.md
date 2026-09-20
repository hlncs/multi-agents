You are a useful assistant and Senior AI Developer, Engineer and Architect.

Design a comprehensive example using autonomous AI agents with LangChain and Langgraph that implements intelligent agent selection and routing for multi-step workflows.

## Requirements

**Tech Stack:**
- Framework: LangChain + Langgraph
- Model: Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf via llama.cpp
- Deployment: Local inference

**Agent Routing Logic:**
- Implement a router agent that selects the most appropriate specialist agent based on:
  - Task complexity and domain requirements
  - Agent expertise and capabilities
  - Token efficiency and performance constraints
- Include fallback mechanisms for ambiguous tasks

**Agent Capabilities:**
The multi-agent system should include at least 3 specialist agents:
- Code generation and debugging agent
- Data analysis and insights agent
- Planning and decomposition agent

**Deliverables:**
- Production-ready implementation with error handling and logging
- Clear agent state management and message passing
- Example workflow demonstrating intelligent routing across 3+ task types
- Detailed inline comments explaining routing decisions
- Performance metrics (latency, token usage per agent)

**Output Format:**
- Working Python implementation
- Architecture diagram/description
- Example use cases with expected outputs
- Setup instructions for local