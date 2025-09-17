"""
AI-Powered Analysis Tools

This module defines the tools that the intelligent AI agent can use to
perform a deep, AI-driven analysis of code files.
"""

from typing import Dict, Any, List


from app.services.llm_service import LLMService
from app.utils.logger import logger


async def analyze_code_with_ai(
    llm_service: LLMService,
    file_path: str,
    code_content: str,
) -> List[Dict[str, Any]]:
    """
    A tool that uses an AI model to analyze a code file for various issues.

    Args:
        llm_service: An active instance of the LLMService.
        file_path: The path of the file to analyze.
        code_content: The actual content of the file.

    Returns:
        A list of issues found by the AI model, validated against the required schema.
    """
    analysis_type = "comprehensive"  # Defaulting to comprehensive for now
    logger.info(f"Executing AI-powered analysis for {file_path}")
    try:
        issues = await llm_service.analyze_code(file_path, code_content, analysis_type)
        logger.info(
            f"AI analysis for {file_path} completed, found {len(issues)} issues."
        )
        return issues
    except Exception as e:
        logger.error(
            f"An error occurred in the AI code analyzer tool for {file_path}: {e}"
        )
        return []
