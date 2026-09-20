import asyncio
import os
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, TypedDict
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class AgentType(Enum):
    CODE_GENERATOR = "code_generator"
    DATA_ANALYST = "data_analyst"
    PLANNER = "planner"
    SUMMERIZER = "summarizer"

@dataclass
class AgentState:
    task: str
    task_id: str
    messages: List[BaseMessage] = field(default_factory=list)
    selected_agent: Optional[AgentType] = None
    result: Optional[str] = None
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

class MultiAgentOrchestrator:
    def __init__(self):
        self.llm = OllamaLLM(
            model=os.getenv("MODEL_NAME"),
            base_url=os.getenv("MODEL_PATH"),
            temperature=0.7
        )
        self.graph = self._build_graph()
        logger.info(f"✓ Initialized Ollama: {os.getenv('MODEL_NAME')}")
    

    def _build_graph(self):
        """Build LangGraph workflow with conditional routing"""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("route", self._route_node)
        graph.add_node("code_generator", self._code_generator_node)
        graph.add_node("data_analyst", self._data_analyst_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("summarize", self._summarize_node)  # Add summarizer
        
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
        
        # Route all agents to summarizer before END
        graph.add_edge("code_generator", "summarize")
        graph.add_edge("data_analyst", "summarize")
        graph.add_edge("planner", "summarize")
        
        # Summarizer goes to END
        graph.add_edge("summarize", END)

        print(f"✓ Compiled LangGraph workflow: {graph.compile()}")
        return graph.compile()

    
    def _route_node(self, state: AgentState) -> AgentState:
        """Route task synchronously"""
        routing_prompt = f"""Analyze this task and select the best agent.

Task: {state.task}

Available agents:
- code_generator: For software development, debugging, code optimization
- data_analyst: For data analysis, statistics, insights
- planner: For task decomposition, planning, risk assessment

Respond with exactly this format:
AGENT: [agent_name]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]"""

        try:
            response = self.llm.invoke(routing_prompt)
            
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
            
        except Exception as e:
            logger.error(f"Routing error: {e}")
            state.selected_agent = AgentType.PLANNER
            state.error = str(e)
        
        return state
    

    def _code_generator_node(self, state: AgentState) -> AgentState:
        """Code generator node"""
        prompt = f"""You are an expert software developer.

Task: {state.task}

Provide complete, working code with documentation."""
        
        response = self.llm.invoke(prompt)
        state.result = response
        state.messages.append(AIMessage(content=response))
        return state
    

    def _data_analyst_node(self, state: AgentState) -> AgentState:
        """Data analyst node"""
        prompt = f"""You are an expert data analyst.

Task: {state.task}

Provide key findings and insights."""
        
        response = self.llm.invoke(prompt)
        state.result = response
        state.messages.append(AIMessage(content=response))
        return state
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Planner node"""
        prompt = f"""You are an expert project planner.

Task: {state.task}

Provide step-by-step breakdown and timeline."""
        
        response = self.llm.invoke(prompt)
        state.result = response
        state.messages.append(AIMessage(content=response))
        return state

    
    def _summarize_node(self, state: AgentState) -> AgentState:
        """Summarize the result"""
        prompt = f"""You are an expert summarizer.

Task: {state.task}

Summarize the key points and findings and provide actionable recommendations in an executive summary."""
        response = self.llm.invoke(prompt)
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
        
        # Execute graph - returns dict
        result_dict = self.graph.invoke(state)
        
        # Convert back to AgentState if needed
        if isinstance(result_dict, dict):
            result = AgentState(**result_dict)
        else:
            result = result_dict
        
        return result


    def execute_generated_code(self, result: AgentState) -> dict:
        """Execute generated code and capture output"""
        if not result.result:
            return {"status": "error", "message": "No result to execute"}
        
        # Extract Python code blocks
        code_blocks = re.findall(r'```python\n(.*?)\n```', result.result, re.DOTALL)
        
        if not code_blocks:
            return {"status": "error", "message": "No code blocks found"}
        
        code = code_blocks[0]
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Execute with timeout
        try:
            proc_result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "status": "success",
                "output": proc_result.stdout,
                "errors": proc_result.stderr if proc_result.stderr else None,
                "return_code": proc_result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Execution timeout (>10s)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Add mock data
MOCK_SALES_DATA = {
    "Q1": {"revenue": 125000, "units": 4500, "growth": 0.08},
    "Q2": {"revenue": 142000, "units": 5100, "growth": 0.136},
    "Q3": {"revenue": 156500, "units": 5800, "growth": 0.102},
    "Q4": {"revenue": 189000, "units": 7200, "growth": 0.207}
}

async def main():
    """Demo the multi-agent system"""
    orchestrator = MultiAgentOrchestrator()
    
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