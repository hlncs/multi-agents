import asyncio
import os
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, TypedDict
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ============================================================================
# LLM Provider Abstract Base Class
# ============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def invoke(self, messages: List[BaseMessage] | str) -> str:
        """Invoke the LLM with messages or a string prompt"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name for logging"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama LLM Provider"""
    
    def __init__(self, model_name: str, base_url: str, temperature: float = 0.7):
        from langchain_ollama import OllamaLLM
        self.llm = OllamaLLM(
            model=model_name,
            base_url=base_url,
            temperature=temperature
        )
        self.model_name = model_name
    
    def invoke(self, messages: List[BaseMessage] | str) -> str:
        """Invoke Ollama"""
        return self.llm.invoke(messages)
    
    def get_name(self) -> str:
        return f"Ollama ({self.model_name})"


class LlamaCppProvider(LLMProvider):
    """Llama.cpp LLM Provider using OpenAI-compatible API"""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:8080", temperature: float = 0.7):
        from langchain_openai import ChatOpenAI
        
        self.model_name = model_name
        self.base_url = base_url
        
        # Use OpenAI-compatible endpoint
        self.llm = ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key="no-key",  # llama.cpp doesn't require auth
            temperature=temperature
        )
    
    def invoke(self, messages: List[BaseMessage] | str) -> str:
        """Invoke Llama.cpp via OpenAI-compatible API"""
        if isinstance(messages, str):
            # Convert string to HumanMessage
            messages = [HumanMessage(content=messages)]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def get_name(self) -> str:
        return f"Llama.cpp ({self.model_name})"


class LLMProviderFactory:
    """Factory to create LLM providers based on configuration"""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> LLMProvider:
        """
        Create an LLM provider based on type
        
        Args:
            provider_type: "ollama" or "llamacpp"
            **kwargs: Provider-specific arguments
        
        Returns:
            LLMProvider instance
        """
        if provider_type.lower() == "ollama":
            return OllamaProvider(
                model_name=kwargs.get("model_name", os.getenv("MODEL_NAME")),
                base_url=kwargs.get("base_url", os.getenv("MODEL_PATH")),
                temperature=kwargs.get("temperature", 0.7)
            )
        elif provider_type.lower() == "llamacpp":
            return LlamaCppProvider(
                model_name=kwargs.get("model_name", os.getenv("LLAMACPP_MODEL")),
                base_url=kwargs.get("base_url", os.getenv("LLAMACPP_URL", "http://localhost:8080")),
                temperature=kwargs.get("temperature", 0.7)
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


# ============================================================================
# Agent Types and State
# ============================================================================

class AgentType(Enum):
    CODE_GENERATOR = "code_generator"
    DATA_ANALYST = "data_analyst"
    PLANNER = "planner"
    SUMMARIZER = "summarizer"

@dataclass
class AgentState:
    task: str
    task_id: str
    messages: List[BaseMessage] = field(default_factory=list)
    selected_agent: Optional[AgentType] = None
    result: Optional[str] = None
    original_result: Optional[str] = None  # Add this to preserve original
    complexity_score: float = 0.5
    routing_reason: str = ""
    error: Optional[str] = None


class AgentStateDict(TypedDict):
    task: str
    task_id: str
    messages: List[BaseMessage]
    selected_agent: Optional[AgentType]
    result: Optional[str]
    complexity_score: float
    routing_reason: str
    error: Optional[str]


# ============================================================================
# Multi-Agent Orchestrator
# ============================================================================

class MultiAgentOrchestrator:
    # Define system prompts as class constants
    SYSTEM_PROMPTS = {
        AgentType.CODE_GENERATOR: """You are an expert software developer with 20+ years of experience.

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
- Mention any assumptions or dependencies""",

        AgentType.DATA_ANALYST: """You are an expert data analyst and statistician.

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
- Suggest visualization approaches""",

        AgentType.PLANNER: """You are an expert project manager and strategic planner.

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
- Define success criteria""",
    }
    
    def __init__(self, provider_type: str = "ollama", **provider_kwargs):
        """
        Initialize the Multi-Agent Orchestrator
        
        Args:
            provider_type: "ollama" or "llamacpp"
            **provider_kwargs: Provider-specific configuration
        """
        # Create LLM provider
        self.llm_provider = LLMProviderFactory.create_provider(provider_type, **provider_kwargs)
        self.graph = self._build_graph()
        logger.info(f"✓ Initialized Multi-Agent Orchestrator with {self.llm_provider.get_name()}")

    def _build_graph(self):
        """Build LangGraph workflow with conditional routing"""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("route", self._route_node)
        graph.add_node("code_generator", self._code_generator_node)
        graph.add_node("data_analyst", self._data_analyst_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("summarize", self._summarize_node)
        
        # Set entry point
        graph.set_entry_point("route")
        
        # Conditional routing based on selected_agent
        def route_decision(state: AgentState):
            if state.selected_agent == AgentType.CODE_GENERATOR:
                return "code_generator"
            elif state.selected_agent == AgentType.DATA_ANALYST:
                return "data_analyst"
            else:
                return "planner"
        
        # Add conditional edges
        graph.add_conditional_edges("route", route_decision)
        
        # Route all agents to summarizer
        graph.add_edge("code_generator", "summarize")
        graph.add_edge("data_analyst", "summarize")
        graph.add_edge("planner", "summarize")
        
        # Summarizer goes to END
        graph.add_edge("summarize", END)

        logger.info(f"✓ Compiled LangGraph workflow")
        return graph.compile()

    def _route_node(self, state: AgentState) -> AgentState:
        """Route task synchronously"""
        system_msg = SystemMessage(
            content="""You are an intelligent task router. Analyze tasks and select the best specialist agent.

Available agents:
- code_generator: Software development, code generation, debugging
- data_analyst: Data analysis, statistics, insights
- planner: Task decomposition, project planning, risk assessment

Respond with:
AGENT: [agent_name]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]"""
        )
        
        user_msg = HumanMessage(
            content=f"Route this task to the best agent:\n\n{state.task}"
        )
        
        all_messages = [system_msg, user_msg]
        response = self.llm_provider.invoke(all_messages)
        
        lines = response.strip().split('\n')
        agent = "planner"
        confidence = 0.5
        reasoning = ""
        
        for line in lines:
            if line.startswith("AGENT:"):
                agent_name = line.replace("AGENT:", "").strip().lower()
                if agent_name in [a.value for a in AgentType]:
                    agent = agent_name
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
        
        state.selected_agent = AgentType(agent)
        state.complexity_score = confidence
        state.routing_reason = reasoning
        
        logger.info(f"[{state.task_id}] Routed to {state.selected_agent.value}")
        
        return state

    def _code_generator_node(self, state: AgentState) -> AgentState:
        """Code generator node with proper role-based messages"""
        system_msg = SystemMessage(
            content=self.SYSTEM_PROMPTS[AgentType.CODE_GENERATOR]
        )
        
        user_msg = HumanMessage(
            content=f"""Task: {state.task}

IMPORTANT INSTRUCTIONS:
1. Write complete, working Python code
2. Wrap ALL code in triple backticks with 'python' language identifier
3. Example format:
   ```python
   def my_function():
       pass
   ```
4. Include docstrings and error handling
5. Provide a working example

Generate the code now:"""
        )
        
        all_messages = [system_msg, user_msg]
        response = self.llm_provider.invoke(all_messages)
        
        state.result = response
        state.original_result = response  # Save original before summarization
        state.messages.append(AIMessage(content=response))
        
        return state

    def _data_analyst_node(self, state: AgentState) -> AgentState:
        """Data analyst node with proper role-based messages"""
        system_msg = SystemMessage(
            content=self.SYSTEM_PROMPTS[AgentType.DATA_ANALYST]
        )
        
        user_msg = HumanMessage(
            content=f"Analyze the following: {state.task}\n\nProvide detailed statistical insights."
        )
        
        all_messages = [system_msg, user_msg]
        response = self.llm_provider.invoke(all_messages)
        
        state.result = response
        state.messages.append(AIMessage(content=response))
        
        return state
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Planner node with proper role-based messages"""
        system_msg = SystemMessage(
            content=self.SYSTEM_PROMPTS[AgentType.PLANNER]
        )
        
        user_msg = HumanMessage(
            content=f"Create a detailed plan for: {state.task}\n\nInclude phases, timeline, and risks."
        )
        
        all_messages = [system_msg, user_msg]
        response = self.llm_provider.invoke(all_messages)
        
        state.result = response
        state.messages.append(AIMessage(content=response))
        return state

    def _summarize_node(self, state: AgentState) -> AgentState:
        """Summarize the result - but preserve code for code generator"""
        
        # Skip summarization for code generator (preserve original code)
        if state.selected_agent == AgentType.CODE_GENERATOR:
            logger.info(f"[{state.task_id}] Skipping summarization for code generator")
            return state
        
        system_msg = SystemMessage(
            content="""You are an expert executive summarizer.

Provide a concise executive summary with:
1. Key points
2. Main findings
3. Actionable recommendations"""
        )
        
        user_msg = HumanMessage(
            content=f"Task: {state.task}\n\nResult: {state.result}"
        )
        
        all_messages = [system_msg, user_msg]
        response = self.llm_provider.invoke(all_messages)
        state.result = response
        state.messages.append(AIMessage(content=response))
        return state

    async def process_task(self, task: str):
        """Process task using LangGraph"""
        import uuid
        state = AgentState(
            task=task,
            task_id=str(uuid.uuid4())[:8]
        )
        state.messages.append(HumanMessage(content=task))
        
        # Execute graph
        result_dict = self.graph.invoke(state)
        
        # Convert back to AgentState if needed
        if isinstance(result_dict, dict):
            result = AgentState(**result_dict)
        else:
            result = result_dict
        
        return result

    def execute_generated_code(self, result: AgentState) -> dict:
        """Execute generated code and capture output"""
        # Use original result if available (before summarization)
        code_source = result.original_result or result.result
        
        if not code_source:
            return {"status": "error", "message": "No result to execute"}
        
        logger.info(f"Attempting to extract code from result (length: {len(code_source)})")
        
        # Try multiple patterns to extract code
        code_blocks = []
        
        # Pattern 1: ```python ... ```
        code_blocks = re.findall(r'```python\n(.*?)\n```', code_source, re.DOTALL)
        if code_blocks:
            logger.info(f"✓ Found code in ```python format")
        
        # Pattern 2: ```\n ... ``` (no language specified)
        if not code_blocks:
            code_blocks = re.findall(r'```\n(.*?)\n```', code_source, re.DOTALL)
            if code_blocks:
                logger.info(f"✓ Found code in ``` format (no language)")
        
        # Pattern 3: ```python (without newline)
        if not code_blocks:
            code_blocks = re.findall(r'```python(.*?)```', code_source, re.DOTALL)
            if code_blocks:
                logger.info(f"✓ Found code in ```python (no newline) format")
                code_blocks = [code.strip() for code in code_blocks]
        
        # Pattern 4: ``` (without language, without newline)
        if not code_blocks:
            code_blocks = re.findall(r'```(.*?)```', code_source, re.DOTALL)
            if code_blocks:
                logger.info(f"✓ Found code in ``` (no newline) format")
                code_blocks = [code.strip() for code in code_blocks]
        
        # Pattern 5: Look for def statements (fallback)
        if not code_blocks:
            def_blocks = re.findall(r'(def\s+\w+\(.*?\):.*?)(?=\ndef|\Z)', code_source, re.DOTALL)
            if def_blocks:
                code_blocks = def_blocks
                logger.info(f"✓ Found code via def pattern matching")
    
        if not code_blocks:
            logger.warning(f"No code blocks found in result")
            logger.info(f"Result preview (first 500 chars):\n{code_source[:500]}")
            return {
                "status": "error",
                "message": "No code blocks found in response",
                "result_preview": code_source[:500]
            }
        
        code = code_blocks[0].strip()
        logger.info(f"Extracted code length: {len(code)} characters")
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
            logger.info(f"Wrote code to {temp_file}")
        
        # Execute with timeout
        try:
            logger.info(f"Executing code...")
            proc_result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc_result.returncode == 0:
                logger.info(f"✓ Code executed successfully")
            else:
                logger.error(f"✗ Code execution failed with return code {proc_result.returncode}")
            
            return {
                "status": "success",
                "output": proc_result.stdout,
                "errors": proc_result.stderr if proc_result.stderr else None,
                "return_code": proc_result.returncode
            }
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Code execution timeout")
            return {"status": "error", "message": "Execution timeout (>10s)"}
        except Exception as e:
            logger.error(f"✗ Code execution error: {e}")
            return {"status": "error", "message": str(e)}


# ============================================================================
# Demo
# ============================================================================

MOCK_SALES_DATA = {
    "Q1": {"revenue": 125000, "units": 4500, "growth": 0.08},
    "Q2": {"revenue": 142000, "units": 5100, "growth": 0.136},
    "Q3": {"revenue": 156500, "units": 5800, "growth": 0.102},
    "Q4": {"revenue": 189000, "units": 7200, "growth": 0.207}
}

async def main():
    """Demo the multi-agent system"""
    
    # Choose provider: "ollama" or "llamacpp"
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    # Initialize orchestrator with selected provider
    if provider_type == "ollama":
        orchestrator = MultiAgentOrchestrator(
            provider_type="ollama",
            model_name=os.getenv("MODEL_NAME"),
            base_url=os.getenv("MODEL_PATH"),
            temperature=0.7
        )
    elif provider_type == "llamacpp":
        orchestrator = MultiAgentOrchestrator(
            provider_type="llamacpp",
            model_name=os.getenv("LLAMACPP_MODEL", "Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"),
            base_url=os.getenv("LLAMACPP_URL", "http://localhost:8080"),
            temperature=0.7
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
    
    # Task with real data
    sales_context = f"Sales data: {MOCK_SALES_DATA}"
    
    tasks = [
        "Write a Python function to parse CSV files",
        f"Analyze these sales trends: {sales_context}",
        "Create a plan for implementing microservices"
    ]
    
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print('='*60)
        
        result = await orchestrator.process_task(task)
        
        # Access as object attributes, not dict keys
        print(f"\n🤖 Agent: {result.selected_agent.value}")
        print(f"📊 Complexity: {result.complexity_score:.2f}")
        print(f"💭 Reason: {result.routing_reason}\n")
        print(f"📝 Result:\n{result.result}")
        
        # Execute the generated code
        if result.selected_agent == AgentType.CODE_GENERATOR:
            exec_result = orchestrator.execute_generated_code(result)
            print(f"Execution Status: {exec_result['status']}")
            if exec_result['status'] == 'success':
                print(f"Output:\n{exec_result['output']}")
            else:
                print(f"Error: {exec_result['message']}")

if __name__ == "__main__":
    asyncio.run(main())