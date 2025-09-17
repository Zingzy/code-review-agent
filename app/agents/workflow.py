"""
Analysis Workflow Stub

Minimal placeholder for future AI agent implementation.
Ready for new agent architecture.
"""

from typing import Dict, Any, List
from app.utils.logger import logger


class CodeAnalysisWorkflow:
    """
    Placeholder workflow class.

    Ready for future AI agent implementation.
    """

    def __init__(self):
        """Initialize workflow stub."""
        logger.info("Workflow stub initialized")

    async def analyze_pr(
        self, pr_data: Dict[str, Any], files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Placeholder workflow method.

        Returns empty results maintaining the expected schema.
        """
        logger.info("Workflow stub executed")
        return {
            "analysis_type": "workflow_stub",
            "file_analyses": [],
            "summary": {},
            "context": {
                "patterns_found": [],
                "global_issues": [],
                "architecture_notes": [],
            },
        }
