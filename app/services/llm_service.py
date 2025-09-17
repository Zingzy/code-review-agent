"""
LLM Service for AI-powered Code Analysis

Handles all interactions with the Large Language Model (LLM) provider,
including prompt formatting, API calls, and response parsing/validation.
"""

from typing import Any, Dict, List


from openai import AsyncOpenAI
import instructor
from pydantic import BaseModel, Field, field_validator

from app.config.settings import get_settings
from app.models.database import IssueType, IssueSeverity
from app.utils.logger import logger


# Pydantic models for structured output from LLM
class AIAnalysisIssue(BaseModel):
    """Validated issue structure for AI analysis"""

    type: IssueType = Field(..., description="The type of the issue.")
    severity: IssueSeverity = Field(..., description="The severity of the issue.")
    line: int = Field(..., description="The line number where the issue occurs.")
    description: str = Field(..., description="A description of the issue.")
    suggestion: str = Field(..., description="A suggestion to fix the issue.")

    @field_validator("type", mode="before")
    def validate_issue_type(cls, v):
        try:
            return IssueType(v.lower())
        except ValueError:
            logger.warning(f"Invalid issue type '{v}', defaulting to 'best_practice'.")
            return IssueType.BEST_PRACTICE

    @field_validator("severity", mode="before")
    def validate_issue_severity(cls, v):
        try:
            return IssueSeverity(v.lower())
        except ValueError:
            logger.warning(f"Invalid issue severity '{v}', defaulting to 'low'.")
            return IssueSeverity.LOW


class AIAnalysisResult(BaseModel):
    """Structured analysis result from the AI model"""

    issues: List[AIAnalysisIssue] = Field(
        ..., description="A list of issues found in the code."
    )


class LLMService:
    """
    Service for interacting with an OpenAI-compatible LLM.
    """

    def __init__(self):
        """Initialize the LLM service."""
        self.settings = get_settings()
        if not self.settings.llm.provider:
            raise ValueError("LLM provider not configured in settings")

        logger.info(
            f"Initializing LLM service for provider: {self.settings.llm.provider}"
        )

        # Configure the OpenAI client
        self.client = instructor.patch(
            AsyncOpenAI(
                api_key=self.settings.llm.openai_api_key,
                base_url=self.settings.llm.base_url,
            )
        )
        self.model = self.settings.llm.model

    async def analyze_code(
        self, file_path: str, code_content: str, analysis_type: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze code content using the configured LLM.

        Args:
            file_path: The path of the file being analyzed.
            code_content: The content of the code to analyze.
            analysis_type: The type of analysis to perform (e.g., 'bug', 'performance').

        Returns:
            A list of validated issues found in the code.
        """
        prompt = self._create_prompt(file_path, code_content, analysis_type)

        try:
            logger.debug(
                f"Sending request to LLM for {analysis_type} analysis of {file_path}"
            )

            # Use instructor to get structured output
            response: AIAnalysisResult = await self.client.chat.completions.create(
                model=self.model,
                response_model=AIAnalysisResult,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert code reviewer. Analyze the provided code and identify issues. Respond only with the structured JSON as requested.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_retries=2,
            )

            # Convert Pydantic models to dictionaries for consistent output
            validated_issues = [issue.model_dump() for issue in response.issues]

            logger.info(
                f"LLM analysis for {file_path} found {len(validated_issues)} issues."
            )
            return validated_issues

        except Exception as e:
            logger.error(f"Error during LLM API call for {file_path}: {e}")
            return []

    def _create_prompt(
        self, file_path: str, code_content: str, analysis_type: str
    ) -> str:
        """
        Create a detailed prompt for the LLM.
        """
        return f"""
        Analyze the following Python code from the file `{file_path}` for **{analysis_type.upper()}** issues.

        **Code:**
        ```python
        {code_content}
        ```

        **Instructions:**
        1.  Focus exclusively on identifying issues related to **{analysis_type}**.
        2.  For each issue found, provide the line number, a clear description, a suggested fix, and a severity level.
        3.  The `type` must be one of: {", ".join([e.value for e in IssueType])}.
        4.  The `severity` must be one of: {", ".join([e.value for e in IssueSeverity])}.
        5.  If no issues are found, return an empty list of issues.
        """


__all__ = ["LLMService"]
