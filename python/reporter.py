"""Output formatting matching TypeScript version."""
import json
import sys
from typing import List
from .types import Check, CheckResult


class Reporter:
    """Handles check output formatting."""

    # ANSI color codes
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, verbose: bool = False, json_output: bool = False):
        """Initialize reporter.

        Args:
            verbose: Show detailed output
            json_output: Output as JSON instead of text
        """
        self.verbose = verbose
        self.json_output = json_output
        self.results: List[dict] = []
        # Check if terminal supports colors
        self.use_colors = sys.stdout.isatty() and not json_output

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if self.use_colors:
            return f"{color}{text}{self.RESET}"
        return text

    def start(self):
        """Called at the start of check execution."""
        if not self.json_output:
            print("\n🔍 Drip SDK Health Check (Python)\n")
            print("=" * 50)

    def on_check_start(self, check: Check):
        """Called when a check starts.

        Args:
            check: The check that is starting
        """
        if not self.json_output:
            print(f"\n▶ {check.name}: {check.description}")

    def on_check_complete(self, result: CheckResult):
        """Called when a check completes.

        Args:
            result: The result of the completed check
        """
        if self.json_output:
            self.results.append({
                "name": result.name,
                "success": result.success,
                "duration": round(result.duration, 2),
                "message": result.message,
                "details": result.details,
                "suggestion": result.suggestion
            })
        else:
            if result.success:
                status = self._color("✓", self.GREEN)
            else:
                status = self._color("✗", self.RED)

            duration_str = f"({result.duration:.0f}ms)"
            print(f"  {status} {result.message} {duration_str}")

            if self.verbose and result.details:
                print(f"    Details: {result.details}")

            if not result.success and result.suggestion:
                print(f"    💡 {result.suggestion}")

    def finish(self, results: List[CheckResult]):
        """Called when all checks are complete.

        Args:
            results: List of all check results
        """
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        total = len(results)

        if self.json_output:
            output = {
                "results": self.results,
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed
                }
            }
            print(json.dumps(output, indent=2))
        else:
            print("\n" + "=" * 50)

            if failed > 0:
                status = self._color(f"📊 Results: {passed}/{total} passed ({failed} failed)", self.YELLOW)
            else:
                status = self._color(f"📊 Results: {passed}/{total} passed ✓", self.GREEN)

            print(f"\n{status}")
