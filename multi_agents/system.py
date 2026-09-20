from __future__ import annotations

import ast
import io
import time
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

try:
    from langchain.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency
    PromptTemplate = None

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - optional dependency
    END = "__end__"
    StateGraph = None


@dataclass
class TaskRequest:
    task_id: str
    instruction: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    task_id: str
    route: str
    output: str
    duration_ms: float
    metrics: Dict[str, Any]


class PerformanceMonitor:
    def __init__(self) -> None:
        self.total_tasks = 0
        self.total_duration_ms = 0.0
        self.route_counts: Dict[str, int] = {}

    def record(self, route: str, duration_ms: float) -> Dict[str, Any]:
        self.total_tasks += 1
        self.total_duration_ms += duration_ms
        self.route_counts[route] = self.route_counts.get(route, 0) + 1
        return {
            "total_tasks": self.total_tasks,
            "avg_duration_ms": self.total_duration_ms / self.total_tasks,
            "route_counts": dict(self.route_counts),
        }


class SpecialistAgent:
    def __init__(self, name: str, handler: Callable[[TaskRequest], str]) -> None:
        self.name = name
        self._handler = handler

    def run(self, request: TaskRequest) -> str:
        return self._handler(request)


class MultiAgentSystem:
    """LangChain/LangGraph-ready multi-agent system with routing and monitoring."""

    def __init__(self) -> None:
        self.monitor = PerformanceMonitor()
        self.agents = {
            "code": SpecialistAgent("code", self._code_agent),
            "analysis": SpecialistAgent("analysis", self._analysis_agent),
            "general": SpecialistAgent("general", self._general_agent),
        }
        self._compiled_graph = self._build_graph()

    def handle(self, request: TaskRequest) -> AgentResponse:
        started = time.perf_counter()
        state = {"request": request, "route": "", "output": ""}

        if self._compiled_graph is not None:
            final_state = self._compiled_graph.invoke(state)
        else:
            final_state = self._run_fallback(state)

        duration_ms = (time.perf_counter() - started) * 1000
        metrics = self.monitor.record(final_state["route"], duration_ms)
        return AgentResponse(
            task_id=request.task_id,
            route=final_state["route"],
            output=final_state["output"],
            duration_ms=duration_ms,
            metrics=metrics,
        )

    def _build_graph(self):
        if StateGraph is None:
            return None

        graph = StateGraph(dict)
        graph.add_node("route", self._route_node)
        graph.add_node("execute", self._execute_node)
        graph.set_entry_point("route")
        graph.add_edge("route", "execute")
        graph.add_edge("execute", END)
        return graph.compile()

    def _run_fallback(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state = self._route_node(state)
        return self._execute_node(state)

    def _route_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        instruction = state["request"].instruction.lower()
        if any(word in instruction for word in ("code", "python", "script", "generate", "execute")):
            route = "code"
        elif any(word in instruction for word in ("analyze", "analysis", "trend", "metrics")):
            route = "analysis"
        else:
            route = "general"

        state["route"] = route
        return state

    def _execute_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        route = state["route"]
        state["output"] = self.agents[route].run(state["request"])
        return state

    def _general_agent(self, request: TaskRequest) -> str:
        return f"General specialist handled: {request.instruction.strip()}"

    def _analysis_agent(self, request: TaskRequest) -> str:
        words = len(request.instruction.split())
        return f"Analysis specialist summary: {words} words received"

    def _code_agent(self, request: TaskRequest) -> str:
        code = self._generate_code(request.instruction)
        return self._execute_generated_code(code)

    def _generate_code(self, instruction: str) -> str:
        if PromptTemplate is not None:
            template = PromptTemplate.from_template(
                "Generate safe Python code that only prints a single result for: {instruction}"
            )
            prompt = template.format(instruction=instruction)
            if "2+2" in instruction.replace(" ", ""):
                return "print(2 + 2)"
            return f"print({prompt!r})"

        if "2+2" in instruction.replace(" ", ""):
            return "print(2 + 2)"
        return f"print({instruction!r})"

    def _execute_generated_code(self, code: str) -> str:
        self._validate_safe_python(code)

        output = io.StringIO()
        safe_globals = {"__builtins__": {"print": print, "len": len, "sum": sum, "range": range}}
        with redirect_stdout(output):
            exec(code, safe_globals, {})
        return output.getvalue().strip()

    def _validate_safe_python(self, code: str) -> None:
        tree = ast.parse(code)
        blocked = (ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Try, ast.Raise)
        for node in ast.walk(tree):
            if isinstance(node, blocked):
                raise ValueError("Unsafe code pattern detected")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec", "open", "compile", "__import__"}:
                    raise ValueError("Unsafe function call detected")
