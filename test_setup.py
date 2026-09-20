import asyncio
import os
from dotenv import load_dotenv

try:
    from langchain_community.llms import Ollama
except ImportError:
    from langchain.llms.ollama import Ollama

load_dotenv()

async def test_routing():
    """Test the routing capability"""
    llm = Ollama(
        model=os.getenv("MODEL_NAME"),
        base_url=os.getenv("MODEL_PATH")
    )
    
    task = "Write a Python function to parse JSON files"
    
    routing_prompt = f"""Analyze this task and select the best agent.

Task: {task}

Available agents:
- code_generator: For software development, debugging, code optimization
- data_analyst: For data analysis, statistics, insights
- planner: For task decomposition, planning, risk assessment

Respond with exactly this format:
AGENT: [agent_name]
CONFIDENCE: [0.0-1.0]
REASONING: [brief explanation]"""

    print("🔄 Testing task routing...")
    print(f"Task: {task}\n")
    
    response = llm.invoke(routing_prompt)
    print("Response from Ollama:")
    print(response)
    print("\n✓ Routing test complete!")

if __name__ == "__main__":
    asyncio.run(test_routing())