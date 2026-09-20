import unittest

from multi_agents.system import MultiAgentSystem, TaskRequest


class MultiAgentSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.system = MultiAgentSystem()

    def test_routes_code_tasks_to_code_specialist(self):
        response = self.system.handle(TaskRequest(task_id="1", instruction="Generate and execute Python code for 2+2"))
        self.assertEqual(response.route, "code")
        self.assertEqual(response.output, "4")

    def test_routes_analysis_tasks_to_analysis_specialist(self):
        response = self.system.handle(TaskRequest(task_id="2", instruction="Analyze these metrics for trends"))
        self.assertEqual(response.route, "analysis")
        self.assertIn("words received", response.output)

    def test_records_monitoring_metrics(self):
        self.system.handle(TaskRequest(task_id="a", instruction="Hello"))
        response = self.system.handle(TaskRequest(task_id="b", instruction="Analyze this data"))
        self.assertEqual(response.metrics["total_tasks"], 2)
        self.assertIn("general", response.metrics["route_counts"])
        self.assertIn("analysis", response.metrics["route_counts"])
        self.assertGreaterEqual(response.metrics["avg_duration_ms"], 0.0)

    def test_rejects_unsafe_code(self):
        with self.assertRaises(ValueError):
            self.system._execute_generated_code("import os\nprint('bad')")


if __name__ == "__main__":
    unittest.main()
