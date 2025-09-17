"""
AI-Driven Python Code Analysis

Modern AI agent that makes intelligent decisions about code analysis
using LangGraph workflow and specialized Python analysis tools.
"""

from typing import Dict, Any, List
from app.agents.ai_workflow import PythonCodeAnalysisWorkflow
from app.utils.logger import logger


class LangGraphAnalyzer:
    """
    AI-driven analyzer for Python code.

    Uses LangGraph workflow where AI agents make decisions about:
    - Which files to analyze
    - What types of analysis to perform
    - How to prioritize and present findings
    """

    def __init__(self):
        """Initialize the AI-driven analyzer."""
        self.workflow = PythonCodeAnalysisWorkflow()
        logger.info("AI-driven Python analyzer initialized")

    async def analyze_pr(
        self, pr_data: Dict[str, Any], files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a pull request using AI-driven workflow.

        Args:
            pr_data: Pull request metadata from GitHub
            files_data: List of changed files with content and metadata

        Returns:
            Analysis results in the expected format
        """
        logger.info(f"Starting AI analysis for PR: {pr_data.get('title', 'Unknown')}")

        try:
            # Filter to Python files only
            python_files = [
                f for f in files_data if f.get("filename", "").endswith(".py")
            ]

            if not python_files:
                return self._create_empty_analysis(pr_data, "No Python files found")

            # Run AI workflow
            results = await self.workflow.analyze_pr(pr_data, python_files)

            logger.info(f"AI analysis completed for {len(python_files)} Python files")
            return results

        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            return self._create_error_analysis(pr_data, str(e))

    def _create_empty_analysis(
        self, pr_data: Dict[str, Any], reason: str
    ) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            "analysis_type": "ai_driven_empty",
            "status": "completed",
            "results": {
                "files": [],
                "summary": {
                    "total_files": 0,
                    "total_issues": 0,
                    "critical_issues": 0,
                    "reason": reason,
                },
            },
        }

    def _create_error_analysis(
        self, pr_data: Dict[str, Any], error: str
    ) -> Dict[str, Any]:
        """Create error analysis result."""
        return {
            "analysis_type": "ai_driven_error",
            "status": "failed",
            "error": error,
            "results": {
                "files": [],
                "summary": {"total_files": 0, "total_issues": 0, "critical_issues": 0},
            },
        }
