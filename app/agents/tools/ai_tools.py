"""
AI-Powered Analysis Tools

This module defines the tools that the intelligent AI agent can use to
perform a deep, AI-driven analysis of code files.
"""

from typing import Dict, Any, List
from langchain_core.tools import tool

from app.services.llm_service import LLMService
from app.utils.logger import logger


@tool
async def ai_code_analyzer_tool(
    file_path: str, code_content: str, analysis_type: str = "comprehensive"
) -> List[Dict[str, Any]]:
    """
    A tool that uses an AI model to analyze a code file for various issues.

    Args:
        file_path: The path of the file to analyze.
        code_content: The actual content of the file.
        analysis_type: The specific type of analysis to run (e.g., 'bug', 'performance').

    Returns:
        A list of issues found by the AI model, validated against the required schema.
    """
    logger.info(
        f"Executing AI-powered analysis for {file_path} (type: {analysis_type})"
    )
    try:
        llm_service = LLMService()
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
