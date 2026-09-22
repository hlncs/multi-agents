import asyncio
import os
from multi_agent_system import MultiAgentOrchestrator, AgentType

# Test data
MOCK_SALES_DATA = {
    "Q1": {"revenue": 125000, "units": 4500, "growth": 0.08},
    "Q2": {"revenue": 142000, "units": 5100, "growth": 0.136},
    "Q3": {"revenue": 156500, "units": 5800, "growth": 0.102},
    "Q4": {"revenue": 189000, "units": 7200, "growth": 0.207}
}


async def test_code_generation():
    """Test code generation with actual file creation"""
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    orchestrator = MultiAgentOrchestrator(provider_type=provider_type)
    
    task = """Write a Python function that:
1. Creates a CSV file with sample data (name, age, city)
2. Reads it back and prints the data
3. Handles errors gracefully"""
    
    print(f"\n{'='*70}")
    print(f"TEST 1: Code Generation")
    print('='*70)
    print(f"Task: {task}\n")
    
    result = await orchestrator.process_task(task)
    
    print(f"🤖 Agent: {result.selected_agent.value}")
    print(f"📊 Complexity: {result.complexity_score:.2f}")
    print(f"💭 Reason: {result.routing_reason}\n")
    
    # Execute the generated code
    if result.selected_agent == AgentType.CODE_GENERATOR:
        exec_result = orchestrator.execute_generated_code(result)
        print(f"Execution Status: {exec_result['status']}")
        if exec_result['status'] == 'success':
            print(f"✅ Output:\n{exec_result['output']}")
            return True
        else:
            print(f"❌ Error: {exec_result['message']}")
            return False
    return False


async def test_data_analysis():
    """Test data analysis task routing"""
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    orchestrator = MultiAgentOrchestrator(provider_type=provider_type)
    
    task = f"""Analyze these sales trends: Sales data: {MOCK_SALES_DATA}
    
Provide insights on:
1. Revenue growth patterns
2. Unit sales trends
3. Growth rate analysis
4. Recommendations"""
    
    print(f"\n{'='*70}")
    print(f"TEST 2: Data Analysis")
    print('='*70)
    print(f"Task: Analyze sales trends\n")
    
    result = await orchestrator.process_task(task)
    
    print(f"🤖 Agent: {result.selected_agent.value}")
    print(f"📊 Complexity: {result.complexity_score:.2f}")
    print(f"💭 Reason: {result.routing_reason}\n")
    print(f"📝 Analysis Result:\n{result.result[:500]}...\n")
    
    return result.selected_agent == AgentType.DATA_ANALYST


async def test_planning():
    """Test planning/decomposition task routing"""
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    orchestrator = MultiAgentOrchestrator(provider_type=provider_type)
    
    task = """Create a detailed plan for implementing a microservices architecture.
    
Include:
1. Phase breakdown with timelines
2. Resource requirements
3. Risk assessment
4. Success criteria"""
    
    print(f"\n{'='*70}")
    print(f"TEST 3: Project Planning")
    print('='*70)
    print(f"Task: Create microservices implementation plan\n")
    
    result = await orchestrator.process_task(task)
    
    print(f"🤖 Agent: {result.selected_agent.value}")
    print(f"📊 Complexity: {result.complexity_score:.2f}")
    print(f"💭 Reason: {result.routing_reason}\n")
    print(f"📝 Plan Result:\n{result.result[:500]}...\n")
    
    return result.selected_agent == AgentType.PLANNER


async def test_routing_accuracy():
    """Test that routing is accurate for different task types"""
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    orchestrator = MultiAgentOrchestrator(provider_type=provider_type)
    
    test_cases = [
        {
            "task": "Write a function to sort a list",
            "expected_agent": AgentType.CODE_GENERATOR,
            "description": "Code generation"
        },
        {
            "task": "What are the key statistics in this dataset?",
            "expected_agent": AgentType.DATA_ANALYST,
            "description": "Data analysis"
        },
        {
            "task": "Break down the steps to launch a new product",
            "expected_agent": AgentType.PLANNER,
            "description": "Planning"
        },
    ]
    
    print(f"\n{'='*70}")
    print(f"TEST 4: Routing Accuracy")
    print('='*70)
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}] {test_case['description']}")
        print(f"Task: {test_case['task']}")
        
        result = await orchestrator.process_task(test_case['task'])
        is_correct = result.selected_agent == test_case['expected_agent']
        
        status = "✅ PASS" if is_correct else "❌ FAIL"
        print(f"Expected: {test_case['expected_agent'].value}")
        print(f"Got: {result.selected_agent.value}")
        print(f"Status: {status}")
        
        results.append(is_correct)
    
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*70}")
    print(f"Routing Accuracy: {passed}/{total} ({100*passed/total:.0f}%)")
    print('='*70)
    
    return all(results)


async def test_performance():
    """Test system performance and measure latencies"""
    import time
    provider_type = os.getenv("LLM_PROVIDER", "ollama").lower()
    orchestrator = MultiAgentOrchestrator(provider_type=provider_type)
    
    task = "Write a Python function to calculate factorial"
    
    print(f"\n{'='*70}")
    print(f"TEST 5: Performance Metrics")
    print('='*70)
    
    start_time = time.time()
    result = await orchestrator.process_task(task)
    end_time = time.time()
    
    total_time = end_time - start_time
    
    print(f"\nTask: {task}")
    print(f"Selected Agent: {result.selected_agent.value}")
    print(f"Total Execution Time: {total_time:.2f}s")
    print(f"Message Count: {len(result.messages)}")
    print(f"Result Length: {len(result.result)} characters")
    
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 MULTI-AGENT SYSTEM TEST SUITE")
    print("="*70)
    
    tests = [
        ("Code Generation", test_code_generation),
        ("Data Analysis", test_data_analysis),
        ("Planning", test_planning),
        ("Routing Accuracy", test_routing_accuracy),
        ("Performance", test_performance),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = "✅ PASS" if passed else "❌ FAIL"
        except Exception as e:
            results[test_name] = f"❌ ERROR: {str(e)[:50]}"
            print(f"\n❌ Error in {test_name}: {e}")
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📊 TEST SUMMARY")
    print('='*70)
    for test_name, result in results.items():
        print(f"{test_name:<30} {result}")
    
    passed_count = sum(1 for r in results.values() if "PASS" in r)
    total_count = len(results)
    
    print(f"\n{'='*70}")
    print(f"Total: {passed_count}/{total_count} tests passed ({100*passed_count/total_count:.0f}%)")
    print('='*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())