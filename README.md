# multi-agents

Minimal multi-agent AI orchestration system with:
- LangChain-aware prompt generation
- LangGraph-based task flow orchestration (with fallback execution path)
- Intelligent task routing to specialist agents (code, analysis, general)
- Performance monitoring (latency, route counts, throughput)
- Safe code generation and execution for code tasks

## Quick start

```python
from multi_agents import MultiAgentSystem, TaskRequest

system = MultiAgentSystem()
response = system.handle(TaskRequest(task_id="1", instruction="Generate and execute Python code for 2+2"))
print(response.route, response.output)
```

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
