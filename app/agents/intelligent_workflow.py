"""
Intelligent AI-Driven Code Analysis Workflow

This module defines a sophisticated LangGraph workflow where an AI agent
makes intelligent decisions about how to analyze a pull request.
"""

from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.tools.ai_tools import analyze_code_with_ai
from app.services.llm_service import LLMService
from app.utils.logger import logger


class FileAnalysis(TypedDict):
    """Represents the analysis results for a single file."""

    file_path: str
    issues: List[Dict[str, Any]]


class IntelligentAnalysisState(TypedDict):
    """
    Represents the state of the intelligent analysis workflow.
    """

    pr_data: Dict[str, Any]
    files_data: List[Dict[str, Any]]
    critical_files: List[str]
    current_file_path: Optional[str]
    analysis_results: List[FileAnalysis]
    final_summary: Dict[str, Any]
    llm_service: LLMService


class IntelligentWorkflow:
    """
    Orchestrates an AI agent's decision-making process for code review.
    """

    def __init__(self):
        self.graph = self._build_graph()
        logger.info("AI Agent analysis workflow initialized")

    def _build_graph(self) -> StateGraph:
        """
        Builds the LangGraph workflow for the intelligent agent.
        """
        workflow = StateGraph(IntelligentAnalysisState)

        # Add nodes
        workflow.add_node("triage_pr", self.triage_pr_node)
        workflow.add_node("file_analysis_loop", self.file_analysis_loop_node)
        workflow.add_node("synthesize_report", self.synthesize_report_node)

        # Define the flow
        workflow.set_entry_point("triage_pr")
        workflow.add_edge("triage_pr", "file_analysis_loop")
        workflow.add_conditional_edges(
            "file_analysis_loop",
            self.should_continue_analysis,
            {
                "continue": "file_analysis_loop",
                "end": "synthesize_report",
            },
        )
        workflow.add_edge("synthesize_report", END)

        return workflow.compile()

    async def run(
        self, pr_data: Dict[str, Any], files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run the intelligent analysis workflow.
        """
        llm_service = LLMService()

        initial_state: IntelligentAnalysisState = {
            "pr_data": pr_data,
            "files_data": files_data,
            "critical_files": [],
            "current_file_path": None,
            "analysis_results": [],
            "final_summary": {},
            "llm_service": llm_service,
        }
        final_state = await self.graph.ainvoke(initial_state)
        return self._format_output(final_state)

    async def triage_pr_node(
        self, state: IntelligentAnalysisState
    ) -> IntelligentAnalysisState:
        """
        AI agent examines the PR to identify critical files for review.
        """
        # This is where the AI would decide which files to prioritize.
        # For now, we'll select all Python files.
        state["critical_files"] = [
            f["filename"]
            for f in state["files_data"]
            if f.get("filename", "").endswith(".py")
        ]
        logger.info(
            f"AI triage identified {len(state['critical_files'])} critical files."
        )
        return state

    async def file_analysis_loop_node(
        self, state: IntelligentAnalysisState
    ) -> IntelligentAnalysisState:
        """
        Analyzes one file at a time, decided by the agent's strategy.
        """
        if not state["critical_files"]:
            return state

        file_path = state["critical_files"].pop(0)
        state["current_file_path"] = file_path

        file_data = next(
            (f for f in state["files_data"] if f.get("filename") == file_path), None
        )
        if not file_data or not file_data.get("content"):
            logger.warning(f"No content found for file {file_path}, skipping analysis.")
            return state

        logger.info(f"AI is analyzing file: {file_path}")
        # AI performs a deep analysis using the AI tool
        llm_service = state["llm_service"]
        issues = await analyze_code_with_ai(
            llm_service, file_path, file_data["content"]
        )

        state["analysis_results"].append({"file_path": file_path, "issues": issues})
        return state

    def should_continue_analysis(self, state: IntelligentAnalysisState) -> str:
        """
        Determines if there are more files to analyze.
        """
        if state["critical_files"]:
            return "continue"
        return "end"

    async def synthesize_report_node(
        self, state: IntelligentAnalysisState
    ) -> IntelligentAnalysisState:
        """
        Synthesizes all findings into a final report.
        """
        logger.info("AI is synthesizing the final report.")
        analysis_results = state["analysis_results"]
        total_issues = sum(len(res.get("issues", [])) for res in analysis_results)
        total_files = len(analysis_results)

        severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        type_breakdown = {}

        for result in analysis_results:
            for issue in result.get("issues", []):
                severity = issue.get("severity", "low")
                issue_type = issue.get("type", "style")
                if severity in severity_breakdown:
                    severity_breakdown[severity] += 1
                type_breakdown[issue_type] = type_breakdown.get(issue_type, 0) + 1

        summary = {
            "total_files_analyzed": total_files,
            "total_issues": total_issues,
            "severity_breakdown": severity_breakdown,
            "issue_type_breakdown": type_breakdown,
            "overall_summary": f"AI analysis complete. Found {total_issues} issues across {total_files} files.",
        }

        state["final_summary"] = summary
        logger.info("AI has synthesized the final report.")
        return state

    def _format_output(self, final_state: IntelligentAnalysisState) -> Dict[str, Any]:
        """
        Formats the final state into the required output structure for database saving.
        """
        formatted_files = {}
        for file_analysis in final_state.get("analysis_results", []):
            file_path = file_analysis["file_path"]
            formatted_files[file_path] = {
                "language": "python",
                "issues": file_analysis["issues"],
            }

        return {
            "summary": final_state.get("final_summary", {}),
            "files": formatted_files,
        }
