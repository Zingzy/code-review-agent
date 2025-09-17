"""
AI-Driven Python Code Analysis

Modern AI agent that makes intelligent decisions about code analysis
using LangGraph workflow and specialized Python analysis tools.
"""

from typing import Dict, Any, List
from app.agents.ai_workflow import AIWorkflow
from app.utils.logger import logger


class LangGraphAnalyzer:
    """
    AI-driven analyzer for Python code.

    Uses a LangGraph workflow where an AI agent makes decisions about:
    - Which files to analyze
    - What types of analysis to perform
    - How to prioritize and present findings
    """

    def __init__(self):
        """Initialize the AI-driven analyzer."""
        self.workflow = AIWorkflow()
        logger.info("AI-driven analyzer initialized")

    async def analyze_pr(
        self, pr_data: Dict[str, Any], files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a pull request using, AI-driven workflow.

        Args:
            pr_data: Pull request metadata from GitHub.
            files_data: List of changed files with content and metadata.

        Returns:
            A dictionary containing the analysis results.
        """
        logger.info(
            f"Starting AI agent analysis for PR: {pr_data.get('title', 'Unknown')}"
        )

        try:
            # The workflow will handle file filtering internally
            results = await self.workflow.run(pr_data, files_data)

            logger.info(
                f"AI analysis completed for PR: {pr_data.get('title', 'Unknown')}"
            )
            return results

        except Exception as e:
            logger.error(f"AI analysis workflow failed: {e}", exc_info=True)
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
