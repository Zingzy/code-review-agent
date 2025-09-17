"""
Python Analysis Tools for AI Agent

Tools that the LangGraph AI agent can use to analyze Python code.
Each tool performs a specific type of analysis and returns structured results.
"""

import ast
from typing import Dict, Any, List
from langchain_core.tools import tool

from app.utils.logger import logger


@tool
def get_file_content_tool(file_path: str, commit_sha: str = None) -> Dict[str, Any]:
    """
    Tool for AI to fetch file content from GitHub.

    Args:
        file_path: Path to the file in the repository
        commit_sha: Optional commit SHA to fetch from

    Returns:
        Dictionary with file content and metadata
    """
    # This would integrate with GitHubService
    # For now, return simulated content
    logger.info(f"AI requested content for file: {file_path}")

    return {
        "file_path": file_path,
        "content": f"# Simulated Python content for {file_path}\ndef example_function():\n    pass\n",
        "lines": 3,
        "size": 100,
        "language": "python",
    }


@tool
def style_analysis_tool(file_content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Tool for AI to analyze Python code style and formatting.

    Checks for:
    - PEP 8 compliance
    - Line length
    - Indentation
    - Naming conventions
    - Import organization

    Args:
        file_content: Python code content
        file_path: File path for context

    Returns:
        List of style issues found
    """
    logger.info(f"AI analyzing code style for: {file_path}")

    issues = []
    lines = file_content.split("\n")

    for i, line in enumerate(lines, 1):
        # Check line length
        if len(line) > 88:  # PEP 8 recommends 79, but 88 is more modern
            issues.append(
                {
                    "type": "style",
                    "line": i,
                    "description": f"Line too long ({len(line)} characters)",
                    "suggestion": "Break line into multiple lines or use parentheses",
                    "severity": "low",
                    "rule": "line_length",
                }
            )

        # Check for trailing whitespace
        if line.endswith(" ") or line.endswith("\t"):
            issues.append(
                {
                    "type": "style",
                    "line": i,
                    "description": "Trailing whitespace",
                    "suggestion": "Remove trailing spaces/tabs",
                    "severity": "low",
                    "rule": "trailing_whitespace",
                }
            )

        # Check for multiple imports on one line
        if line.strip().startswith("import ") and "," in line:
            issues.append(
                {
                    "type": "style",
                    "line": i,
                    "description": "Multiple imports on one line",
                    "suggestion": "Import each module on separate lines",
                    "severity": "medium",
                    "rule": "import_style",
                }
            )

    logger.info(f"Found {len(issues)} style issues")
    return issues


@tool
def bug_analysis_tool(file_content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Tool for AI to analyze potential bugs in Python code.

    Checks for:
    - Syntax errors
    - Undefined variables
    - Type mismatches
    - Logic errors
    - Exception handling issues

    Args:
        file_content: Python code content
        file_path: File path for context

    Returns:
        List of potential bugs found
    """
    logger.info(f"AI analyzing potential bugs for: {file_path}")

    issues = []
    lines = file_content.split("\n")

    try:
        # Parse the AST to check for syntax errors
        tree = ast.parse(file_content)

        # Walk the AST to find potential issues
        for node in ast.walk(tree):
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(
                    {
                        "type": "bug",
                        "line": node.lineno,
                        "description": "Bare except clause catches all exceptions",
                        "suggestion": "Specify the exception type or use 'except Exception:'",
                        "severity": "medium",
                        "rule": "bare_except",
                    }
                )

            # Check for comparison with None using == instead of is
            if isinstance(node, ast.Compare):
                for i, comparator in enumerate(node.comparators):
                    if (
                        isinstance(comparator, ast.Constant)
                        and comparator.value is None
                        and isinstance(node.ops[i], ast.Eq)
                    ):
                        issues.append(
                            {
                                "type": "bug",
                                "line": node.lineno,
                                "description": "Comparison with None should use 'is' not '=='",
                                "suggestion": "Use 'is None' instead of '== None'",
                                "severity": "medium",
                                "rule": "none_comparison",
                            }
                        )

    except SyntaxError as e:
        issues.append(
            {
                "type": "bug",
                "line": e.lineno or 1,
                "description": f"Syntax error: {e.msg}",
                "suggestion": "Fix the syntax error",
                "severity": "critical",
                "rule": "syntax_error",
            }
        )

    # Check for common patterns in text
    for i, line in enumerate(lines, 1):
        # Check for print statements (should use logging)
        if "print(" in line and not line.strip().startswith("#"):
            issues.append(
                {
                    "type": "bug",
                    "line": i,
                    "description": "Use logging instead of print statements",
                    "suggestion": "Replace print with logging.info/debug/warning",
                    "severity": "low",
                    "rule": "print_statement",
                }
            )

    logger.info(f"Found {len(issues)} potential bugs")
    return issues


@tool
def performance_analysis_tool(
    file_content: str, file_path: str
) -> List[Dict[str, Any]]:
    """
    Tool for AI to analyze performance issues in Python code.

    Checks for:
    - Inefficient loops
    - Unnecessary list comprehensions
    - String concatenation in loops
    - Inefficient data structures
    - Database query patterns

    Args:
        file_content: Python code content
        file_path: File path for context

    Returns:
        List of performance issues found
    """
    logger.info(f"AI analyzing performance for: {file_path}")

    issues = []
    lines = file_content.split("\n")

    try:
        tree = ast.parse(file_content)

        for node in ast.walk(tree):
            # Check for string concatenation in loops
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(
                        child.op, ast.Add
                    ):
                        # This is a simplified check
                        issues.append(
                            {
                                "type": "performance",
                                "line": child.lineno,
                                "description": "String concatenation in loop can be inefficient",
                                "suggestion": "Use join() or format strings instead",
                                "severity": "medium",
                                "rule": "string_concat_loop",
                            }
                        )

    except SyntaxError:
        # Skip performance analysis if syntax is invalid
        pass

    # Text-based checks
    for i, line in enumerate(lines, 1):
        # Check for inefficient membership testing
        if ".count(" in line and "if" in line:
            issues.append(
                {
                    "type": "performance",
                    "line": i,
                    "description": "Using .count() for membership testing is inefficient",
                    "suggestion": "Use 'in' operator instead",
                    "severity": "medium",
                    "rule": "inefficient_membership",
                }
            )

        # Check for list comprehension when generator would be better
        if "[" in line and "for" in line and "sum(" in line:
            issues.append(
                {
                    "type": "performance",
                    "line": i,
                    "description": "Consider using generator expression instead of list comprehension",
                    "suggestion": "Use () instead of [] for generator expression",
                    "severity": "low",
                    "rule": "generator_preferred",
                }
            )

    logger.info(f"Found {len(issues)} performance issues")
    return issues


@tool
def best_practice_tool(file_content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Tool for AI to analyze Python best practices.

    Checks for:
    - Function/class documentation
    - Type hints
    - Error handling patterns
    - Code organization
    - Security practices

    Args:
        file_content: Python code content
        file_path: File path for context

    Returns:
        List of best practice violations found
    """
    logger.info(f"AI analyzing best practices for: {file_path}")

    issues = []
    lines = file_content.split("\n")

    try:
        tree = ast.parse(file_content)

        for node in ast.walk(tree):
            # Check for functions without docstrings
            if isinstance(node, ast.FunctionDef):
                if (
                    not ast.get_docstring(node)
                    and not node.name.startswith("_")  # Skip private methods
                    and node.name != "__init__"
                ):  # Skip __init__ for now
                    issues.append(
                        {
                            "type": "best_practice",
                            "line": node.lineno,
                            "description": f"Function '{node.name}' lacks documentation",
                            "suggestion": "Add docstring explaining function purpose and parameters",
                            "severity": "medium",
                            "rule": "missing_docstring",
                        }
                    )

            # Check for classes without docstrings
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    issues.append(
                        {
                            "type": "best_practice",
                            "line": node.lineno,
                            "description": f"Class '{node.name}' lacks documentation",
                            "suggestion": "Add docstring explaining class purpose",
                            "severity": "medium",
                            "rule": "missing_class_docstring",
                        }
                    )

    except SyntaxError:
        # Skip best practice analysis if syntax is invalid
        pass

    # Text-based checks
    for i, line in enumerate(lines, 1):
        # Check for hardcoded credentials/secrets
        if any(
            keyword in line.lower()
            for keyword in ["password", "secret", "key", "token"]
        ):
            if "=" in line and any(quote in line for quote in ['"', "'"]):
                issues.append(
                    {
                        "type": "best_practice",
                        "line": i,
                        "description": "Potential hardcoded credential detected",
                        "suggestion": "Use environment variables or secure configuration",
                        "severity": "high",
                        "rule": "hardcoded_credentials",
                    }
                )

        # Check for TODO/FIXME comments
        if any(keyword in line.upper() for keyword in ["TODO", "FIXME", "XXX"]):
            issues.append(
                {
                    "type": "best_practice",
                    "line": i,
                    "description": "TODO/FIXME comment found",
                    "suggestion": "Address the comment or create a proper issue",
                    "severity": "low",
                    "rule": "todo_comment",
                }
            )

    logger.info(f"Found {len(issues)} best practice issues")
    return issues
