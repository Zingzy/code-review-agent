"""
AI-Driven Python Code Analysis Workflow

LangGraph workflow where AI agents make decisions about what to analyze
and how to analyze it, using provided tools.
"""

from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.utils.logger import logger


class AnalysisType(str, Enum):
    """Types of analysis the AI can perform"""

    STYLE = "style"
    BUG = "bug"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"


@dataclass
class FileIssue:
    """Individual issue found in a file"""

    type: AnalysisType
    line: int
    description: str
    suggestion: str
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class FileAnalysis:
    """Analysis results for a single file"""

    name: str
    path: str
    issues: List[FileIssue]
    analyzed: bool = False
    language: str = "python"


class AnalysisState(TypedDict):
    """State passed through the workflow"""

    # Input data
    pr_data: Dict[str, Any]
    pr_files: List[Dict[str, Any]]  # Basic file info from GitHub

    # AI decisions
    selected_files: List[str]  # Files AI chose to analyze
    current_file: Optional[str]

    # File contents (fetched as needed)
    file_contents: Dict[str, str]  # path -> content

    # Analysis results
    file_analyses: List[FileAnalysis]

    # Progress tracking
    stage: str
    progress: float

    # Final output
    summary: Dict[str, Any]


class PythonCodeAnalysisWorkflow:
    """
    AI-driven workflow for Python code analysis.

    The AI agent makes decisions about:
    - Which files to analyze based on PR context
    - What types of analysis to run on each file
    - How to prioritize and present findings
    """

    def __init__(self):
        self.graph = self._build_graph()
        logger.info("AI-driven Python analysis workflow initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AnalysisState)

        # Add nodes
        workflow.add_node("pr_analysis", self.analyze_pr_context)
        workflow.add_node("file_selection", self.select_files_for_analysis)
        workflow.add_node("content_fetching", self.fetch_file_contents)
        workflow.add_node("python_analysis", self.analyze_python_code)
        workflow.add_node("synthesis", self.synthesize_results)

        # Add tool nodes for AI to use
        workflow.add_node("tools", ToolNode(self._get_analysis_tools()))

        # Define flow
        workflow.set_entry_point("pr_analysis")
        workflow.add_edge("pr_analysis", "file_selection")
        workflow.add_edge("file_selection", "content_fetching")
        workflow.add_edge("content_fetching", "python_analysis")
        workflow.add_edge("python_analysis", "synthesis")
        workflow.add_edge("synthesis", END)

        return workflow.compile()

    def _get_analysis_tools(self):
        """Get tools that the AI can use during analysis"""
        from app.agents.tools.python_tools import (
            get_file_content_tool,
            style_analysis_tool,
            bug_analysis_tool,
            performance_analysis_tool,
            best_practice_tool,
        )

        return [
            get_file_content_tool,
            style_analysis_tool,
            bug_analysis_tool,
            performance_analysis_tool,
            best_practice_tool,
        ]

    async def analyze_pr(
        self, pr_data: Dict[str, Any], files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main entry point for PR analysis.

        Args:
            pr_data: Pull request metadata
            files_data: List of changed files with basic info

        Returns:
            Analysis results in the expected format
        """
        logger.info(
            f"Starting AI-driven analysis for PR: {pr_data.get('title', 'Unknown')}"
        )

        initial_state: AnalysisState = {
            "pr_data": pr_data,
            "pr_files": files_data,
            "selected_files": [],
            "current_file": None,
            "file_contents": {},
            "file_analyses": [],
            "stage": "starting",
            "progress": 0.0,
            "summary": {},
        }

        try:
            # Run the AI workflow
            result_state = await self.graph.ainvoke(initial_state)

            # Format results for API response
            return self._format_results(result_state)

        except Exception as e:
            logger.error(f"AI workflow failed: {e}", exc_info=True)
            return self._create_error_response(pr_data, str(e))

    def analyze_pr_context(self, state: AnalysisState) -> AnalysisState:
        """
        AI analyzes PR context to understand what kind of analysis is needed.

        The AI examines:
        - PR title and description
        - List of changed files
        - File extensions and paths
        - Change sizes (additions/deletions)
        """
        logger.info("AI analyzing PR context...")

        pr_data = state.get("pr_data", {})
        if not isinstance(pr_data, dict):
            logger.error(
                "pr_data missing or not a dict in state; received type: %s",
                type(pr_data),
            )
            state["stage"] = "error"
            state["summary"] = {"error": "invalid_pr_data"}
            return state

        pr_files = state.get("pr_files", [])
        python_files = [
            f
            for f in pr_files
            if isinstance(f, dict) and f.get("filename", "").endswith(".py")
        ]
        logger.info(f"Found {len(python_files)} Python files in PR")
        state["stage"] = "analyzed_context"
        state["progress"] = 20.0
        return state

    def select_files_for_analysis(self, state: AnalysisState) -> AnalysisState:
        """
        AI selects which files to analyze based on importance and change scope.

        AI considers:
        - File size and complexity
        - Number of changes
        - File importance (main modules vs tests)
        - Available analysis time
        """
        logger.info("AI selecting files for analysis...")

        # Filter to Python files only
        pr_files = state.get("pr_files", [])

        # AI logic to prioritize files
        # For now: select up to 5 most changed files
        sorted_files = sorted(
            [
                f
                for f in pr_files
                if isinstance(f, dict) and f.get("filename", "").endswith(".py")
            ],
            key=lambda x: x.get("changes", 0) if isinstance(x, dict) else 0,
            reverse=True,
        )

        selected = [f["filename"] for f in sorted_files[:5]]

        logger.info(f"AI selected {len(selected)} files for analysis: {selected}")

        state["selected_files"] = selected
        state["stage"] = "files_selected"
        state["progress"] = 40.0

        return state

    def fetch_file_contents(self, state: AnalysisState) -> AnalysisState:
        """
        Fetch content for selected files as needed.

        AI can decide to fetch files incrementally during analysis
        rather than all upfront.
        """
        logger.info("Fetching content for selected files...")

        # Build file content mapping from pr_files data already provided

        selected_files = state.get("selected_files", [])
        pr_files = state.get("pr_files", [])
        file_contents = {}
        for file_path in selected_files:
            if not isinstance(file_path, str):
                continue
            # find matching entry with content
            match = next(
                (
                    f
                    for f in pr_files
                    if isinstance(f, dict) and f.get("filename") == file_path
                ),
                None,
            )
            content = ""
            if isinstance(match, dict):
                content = match.get("content") or ""
            file_contents[file_path] = content
        state["file_contents"] = file_contents

        logger.info(f"Fetched content for {len(file_contents)} files")

        state["stage"] = "content_fetched"
        state["progress"] = 60.0

        return state

    def analyze_python_code(self, state: AnalysisState) -> AnalysisState:
        """
        AI performs multi-stage analysis on Python code.

        The AI decides:
        - Which analysis types to run on each file
        - How deep to analyze based on file complexity
        - Whether to focus on specific areas
        """
        logger.info("AI analyzing Python code...")

        from app.agents.tools.python_tools import (
            style_analysis_tool,
            bug_analysis_tool,
            performance_analysis_tool,
            best_practice_tool,
        )

        selected_files = state.get("selected_files", [])  # type: ignore
        file_contents = state.get("file_contents", {})  # type: ignore
        file_analyses: List[FileAnalysis] = []

        for file_path in selected_files:
            if not isinstance(file_path, str):
                continue
            content = file_contents.get(file_path, "")

            def run_tool(tool_obj, **kwargs):
                if hasattr(tool_obj, "invoke"):
                    return tool_obj.invoke(kwargs)
                return tool_obj(**kwargs)

            style_issues = run_tool(
                style_analysis_tool, file_content=content, file_path=file_path
            )
            bug_issues = run_tool(
                bug_analysis_tool, file_content=content, file_path=file_path
            )
            perf_issues = run_tool(
                performance_analysis_tool, file_content=content, file_path=file_path
            )
            best_issues = run_tool(
                best_practice_tool, file_content=content, file_path=file_path
            )

            all_issues_dicts: List[Dict[str, Any]] = (
                (style_issues or [])
                + (bug_issues or [])
                + (perf_issues or [])
                + (best_issues or [])
            )

            issue_objs: List[FileIssue] = []
            for issue in all_issues_dicts:
                if not isinstance(issue, dict):
                    continue
                issue_objs.append(
                    FileIssue(
                        type=AnalysisType(issue.get("type", "style"))
                        if issue.get("type") in AnalysisType.__members__.values()
                        else AnalysisType.STYLE,
                        line=int(issue.get("line", 1)),
                        description=issue.get("description", ""),
                        suggestion=issue.get("suggestion", ""),
                        severity=issue.get("severity", "medium"),
                    )
                )

            analysis = FileAnalysis(
                name=file_path.split("/")[-1],
                path=file_path,
                issues=issue_objs,
                analyzed=True,
                language="python",
            )
            file_analyses.append(analysis)

        state["file_analyses"] = file_analyses

        logger.info(
            f"AI completed analysis of {len(file_analyses)} files with total issues: "
            f"{sum(len(fa.issues) for fa in file_analyses)}"
        )

        state["stage"] = "analysis_complete"
        state["progress"] = 90.0

        return state

    def synthesize_results(self, state: AnalysisState) -> AnalysisState:
        """
        AI synthesizes all findings into a coherent report.

        The AI:
        - Prioritizes issues by severity and impact
        - Groups related issues
        - Provides overall recommendations
        - Creates summary statistics
        """
        logger.info("AI synthesizing analysis results...")

        file_analyses = state.get("file_analyses", [])  # type: ignore
        total_issues = sum(
            len(fa.issues) for fa in file_analyses if hasattr(fa, "issues")
        )
        critical_issues = sum(
            len([i for i in fa.issues if i.severity == "critical"])
            for fa in file_analyses
        )

        # Breakdown by type
        type_breakdown: Dict[str, int] = {}
        severity_breakdown: Dict[str, int] = {}
        for fa in file_analyses:
            for issue in fa.issues:
                type_breakdown[issue.type.value] = (
                    type_breakdown.get(issue.type.value, 0) + 1
                )
                severity_breakdown[issue.severity] = (
                    severity_breakdown.get(issue.severity, 0) + 1
                )

        state["summary"] = {
            "total_files": len(file_analyses),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "analysis_type": "ai_driven_python",
            "issue_type_breakdown": type_breakdown,
            "severity_breakdown": severity_breakdown,
        }

        state["stage"] = "complete"
        state["progress"] = 100.0

        logger.info("AI synthesis complete")

        return state

    def _format_results(self, state: AnalysisState) -> Dict[str, Any]:
        """Format results for API response"""
        files_results = []

        file_analyses = state.get("file_analyses", [])  # type: ignore
        for analysis in file_analyses:
            file_result = {
                "name": analysis.name,
                "path": analysis.path,
                "language": getattr(analysis, "language", "python"),
                "size": 0,
                "issues": [
                    {
                        "type": issue.type.value,
                        "severity": issue.severity,
                        "line": getattr(issue, "line", 1),
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "rule": getattr(issue, "rule", None),
                        "confidence": getattr(issue, "confidence", 0.8),
                    }
                    for issue in analysis.issues
                ],
            }
            files_results.append(file_result)
        summary = state.get("summary", {})  # type: ignore

        return {
            "analysis_type": "ai_driven_python",
            "status": "completed",
            "results": {"files": files_results, "summary": summary},
            "summary": summary,
            "file_analyses": [
                {
                    "file_path": fa.path,
                    "language": getattr(fa, "language", "python"),
                    "issues": [
                        {
                            "type": issue.type.value,
                            "line": issue.line,
                            "description": issue.description,
                            "suggestion": issue.suggestion,
                            "severity": issue.severity,
                        }
                        for issue in fa.issues
                    ],
                }
                for fa in file_analyses
            ],
        }

    def _create_error_response(
        self, pr_data: Dict[str, Any], error: str
    ) -> Dict[str, Any]:
        """Create error response"""
        return {
            "analysis_type": "ai_driven_error",
            "status": "failed",
            "error": error,
            "results": {
                "files": [],
                "summary": {"total_files": 0, "total_issues": 0, "critical_issues": 0},
            },
        }
