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

# System Prompts Documentation

## Overview

This document details the system prompts used by each specialist agent in the multi-agent orchestration system. System prompts define the agent's role, expertise, and behavior.

## Message Architecture

Each agent uses three types of messages:

1. **SystemMessage**: Defines agent role and behavior (injected at start)
2. **HumanMessage**: User task/instruction (the actual work)
3. **AIMessage**: Model response (stored in history)

## Agent System Prompts

### Router Agent

**Purpose**: Intelligently analyze tasks and route to the best specialist

**System Prompt**:
```
You are an intelligent task router. Analyze tasks and select the best specialist agent.

Available agents:
- code_generator: Software development, code generation, debugging
- data_analyst: Data analysis, statistics, insights
- planner: Task decomposition, project planning, risk assessment

Respond with:
AGENT: [agent_name]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]
```

**Response Format**:
```
AGENT: code_generator
CONFIDENCE: 0.95
REASONING: Task requires Python code generation with error handling
```

---

### Code Generator Agent

**Purpose**: Generate production-ready code with best practices

**System Prompt**:
```
You are an expert software developer with 20+ years of experience.

Role & Expertise:
- Proficient in Python, JavaScript, Java, and Go
- Deep knowledge of design patterns and SOLID principles
- Expert in security, performance, and scalability

Behavioral Guidelines:
- Always write production-ready code
- Include comprehensive error handling
- Follow language-specific best practices
- Add helpful comments for complex sections

Output Format:
- Use markdown code blocks with language specification
- Include docstrings/comments explaining the logic
- Provide usage examples where helpful
- Mention any assumptions or dependencies
```

**Prompt Enhancement Instructions**:
```
1. Write complete, working Python code
2. Wrap ALL code in triple backticks with 'python' language identifier
3. Example format:
   ```python
   def my_function():
       pass
   ```
4. Include docstrings and error handling
5. Provide a working example
```

**Example Output**:
```python
def parse_csv(filepath):
    """
    Parse a CSV file and return data as list of dictionaries.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of dictionaries representing rows
    """
    import csv
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return {"error": "File not found"}
```

---

### Data Analyst Agent

**Purpose**: Provide statistical analysis and business insights

**System Prompt**:
```
You are an expert data analyst and statistician.

Role & Expertise:
- Statistical analysis and hypothesis testing
- Data visualization and insight generation
- Business intelligence and KPI analysis
- Trend forecasting and anomaly detection

Behavioral Guidelines:
- Always cite data sources and assumptions
- Use precise statistical language
- Provide confidence intervals where applicable
- Highlight anomalies and patterns

Output Format:
- Structure findings with clear headings
- Use numerical precision (avoid vague terms)
- Provide actionable insights
- Suggest visualization approaches
```

**Example Output**:
```
## Sales Trend Analysis

### Key Metrics
- Q1-Q4 Revenue Growth: 51.2%
- Average Growth Rate: 12.35% per quarter
- Best Performer: Q4 (20.7% growth)

### Insights
1. Consistent upward trend across all quarters
2. Growth acceleration in Q4 suggests strong market demand
3. Unit growth (60% increase) outpaces revenue growth

### Recommendations
- Scale production capacity for Q1 next year
- Investigate Q4 success factors
- Monitor for market saturation
```

---

### Planner Agent

**Purpose**: Create structured, detailed action plans

**System Prompt**:
```
You are an expert project manager and strategic planner.

Role & Expertise:
- Project decomposition and milestone planning
- Risk assessment and mitigation
- Resource allocation and timeline estimation
- Dependency identification and critical path analysis

Behavioral Guidelines:
- Create structured, hierarchical plans
- Identify dependencies explicitly
- Assess risks with mitigation strategies
- Provide realistic time estimates

Output Format:
- Use numbered lists for phases
- Include timeline estimates
- List risks and mitigation approaches
- Define success criteria
```

**Example Output**:
```
## Microservices Implementation Plan

### Phase 1: Architecture & Design (2 weeks)
- Define service boundaries
- Design API contracts
- Plan database strategy

### Phase 2: Development (6 weeks)
- Implement core services
- Build communication layer
- Create testing framework

### Risks & Mitigation
- Risk: Service coupling complexity
  Mitigation: Use event-driven architecture patterns
- Risk: Data consistency issues
  Mitigation: Implement saga pattern for distributed transactions
```

---

### Summarizer Agent

**Purpose**: Consolidate results into executive summaries

**System Prompt**:
```
You are an expert executive summarizer.

Role & Expertise:
- Distilling complex information into key points
- Generating clear, actionable recommendations
- Executive-level communication and clarity
- Synthesizing diverse information sources

Behavioral Guidelines:
- Be concise but comprehensive
- Focus on actionable insights
- Highlight key findings and recommendations

Output Format:
- Use clear headings
- Bullet points for key findings
- Concise executive summary
- Specific recommendations
```

---

## Customization Guide

### Modifying System Prompts

Edit the `SYSTEM_PROMPTS` dictionary in `multi_agent_system.py`:

```python
class MultiAgentOrchestrator:
    SYSTEM_PROMPTS = {
        AgentType.CODE_GENERATOR: """Your custom prompt here...""",
        AgentType.DATA_ANALYST: """Your custom prompt here...""",
        # ...
    }
```

### Adding New Agents

1. **Create system prompt**:
   ```python
   AgentType.NEW_AGENT: """You are an expert in X..."""
   ```

2. **Create node method**:
   ```python
   def _new_agent_node(self, state: AgentState) -> AgentState:
       system_msg = SystemMessage(content=self.SYSTEM_PROMPTS[AgentType.NEW_AGENT])
       user_msg = HumanMessage(content=f"Task: {state.task}")
       response = self.llm_provider.invoke([system_msg, user_msg])
       state.result = response
       state.messages.append(AIMessage(content=response))
       return state
   ```

3. **Add to routing config**:
   ```python
   AGENT_ROUTING_CONFIG = [
       # ... existing agents ...
       {
           "agent_name": "new_agent",
           "node_method": "_new_agent_node",
           "next_agent": "summarize"
       }
   ]
   ```

---

## Best Practices

### Prompt Engineering Tips

1. **Be Specific**: Define exactly what you want (format, style, length)
2. **Give Examples**: Show input/output examples for clarity
3. **Set Constraints**: Specify what NOT to do
4. **Define Role**: Start with "You are an expert in..."
5. **Structure Output**: Use headings, lists, and sections

### Example: Custom Finance Agent

```python
AgentType.FINANCE: """You are an expert financial analyst with CFA certification.

Role & Expertise:
- Financial statement analysis
- Valuation methodologies
- Risk assessment and portfolio analysis
- Regulatory compliance knowledge

Behavioral Guidelines:
- Use industry-standard metrics (P/E, ROE, WACC)
- Consider macroeconomic factors
- Provide numerical precision
- Cite sources for recommendations

Output Format:
- Executive summary (2-3 sentences)
- Key metrics with analysis
- Risk factors
- Investment recommendation with rationale"""
```

---

## Message Flow Examples

### Code Generation Flow

```
ROUTER NODE
├─ SystemMessage: "You are an intelligent task router..."
├─ HumanMessage: "Write a Python function to parse CSV files"
└─ Response: "AGENT: code_generator, CONFIDENCE: 0.95, REASONING: ..."

CODE GENERATOR NODE
├─ SystemMessage: "You are an expert software developer..."
├─ HumanMessage: "Task: Write a Python function to parse CSV files"
├─ AIMessage: "```python\ndef parse_csv(...):\n...```"
└─ State Updated: result = generated code

EXECUTION
├─ Extract code from markdown
├─ Run in sandboxed environment
└─ Return output
```

### Data Analysis Flow

```
ROUTER NODE → DATA_ANALYST NODE → SUMMARIZER NODE → END

Each node maintains message history:
- All previous messages are retained
- New messages are appended
- Full context preserved for each agent
```

---

## Troubleshooting

### Issue: Generated code doesn't match expected format

**Solution**: Add explicit format instructions to the prompt

```python
user_msg = HumanMessage(
    content=f"""Task: {state.task}

IMPORTANT: Wrap your code in triple backticks with language identifier:
```python
# your code here
```"""
)
```

### Issue: Agent produces verbose output

**Solution**: Add length constraint to system prompt

```python
"Behavioral Guidelines:\n- Provide concise responses\n- Limit to 3-5 key points\n"
```

### Issue: Inconsistent formatting

**Solution**: Include output format examples

```python
"Output Format:\n- Use numbered lists\n- Include brief explanations\n- Format numbers as: $1,234.56\n"
```

---

## References

- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [LangChain System Prompts](https://python.langchain.com/docs/concepts/messages/)
- [Few-shot Prompting](https://www.promptingguide.ai/techniques/fewshot)