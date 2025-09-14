"""
Language Detection Utility

Utilities for detecting programming languages from file names and content.
"""

from pathlib import Path
from typing import Optional


class LanguageDetector:
    """
    Utility class for detecting programming languages from file extensions and content.
    """

    # Mapping of file extensions to programming languages
    EXTENSION_MAP = {
        # Python
        ".py": "python",
        ".pyi": "python",
        ".pyx": "python",
        ".pyw": "python",
        # JavaScript/TypeScript
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        # Java
        ".java": "java",
        ".class": "java",
        ".jar": "java",
        # C/C++
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".cc": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".hh": "cpp",
        # C#
        ".cs": "csharp",
        ".csx": "csharp",
        # Go
        ".go": "go",
        # Rust
        ".rs": "rust",
        ".rlib": "rust",
        # PHP
        ".php": "php",
        ".phtml": "php",
        ".php3": "php",
        ".php4": "php",
        ".php5": "php",
        ".phps": "php",
        # Ruby
        ".rb": "ruby",
        ".rbw": "ruby",
        ".rake": "ruby",
        ".gemspec": "ruby",
        # Swift
        ".swift": "swift",
        # Kotlin
        ".kt": "kotlin",
        ".kts": "kotlin",
        # Scala
        ".scala": "scala",
        ".sc": "scala",
        # R
        ".r": "r",
        ".R": "r",
        # MATLAB
        ".m": "matlab",
        # Shell scripting
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".fish": "shell",
        ".ksh": "shell",
        ".csh": "shell",
        ".tcsh": "shell",
        # Web languages
        ".html": "html",
        ".htm": "html",
        ".xhtml": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        # Database
        ".sql": "sql",
        ".mysql": "sql",
        ".pgsql": "sql",
        # Configuration/Data
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        # Documentation
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "rst",
        ".txt": "text",
        # Docker
        "dockerfile": "dockerfile",
        ".dockerfile": "dockerfile",
        # CI/CD (already defined above in Configuration/Data section)
    }

    # Special filename patterns
    FILENAME_PATTERNS = {
        "dockerfile": "dockerfile",
        "makefile": "makefile",
        "rakefile": "ruby",
        "gemfile": "ruby",
        "vagrantfile": "ruby",
        "procfile": "text",
        "license": "text",
        "readme": "markdown",
        "changelog": "text",
        "requirements.txt": "text",
        "package.json": "json",
        "composer.json": "json",
        "cargo.toml": "toml",
        "pyproject.toml": "toml",
    }

    @classmethod
    def detect_language_from_filename(cls, filename: str) -> Optional[str]:
        """
        Detect programming language from filename.

        Args:
            filename: Name of the file (can include path)

        Returns:
            Detected language or None if unknown
        """
        if not filename:
            return None

        # Get just the filename without path
        basename = Path(filename).name.lower()

        # Check special filename patterns first
        for pattern, language in cls.FILENAME_PATTERNS.items():
            if pattern in basename:
                return language

        # Check file extension
        extension = Path(filename).suffix.lower()
        if extension in cls.EXTENSION_MAP:
            return cls.EXTENSION_MAP[extension]

        return None

    @classmethod
    def detect_language_from_content(
        cls, content: str, filename: str = None
    ) -> Optional[str]:
        """
        Detect programming language from file content (basic detection).

        Args:
            content: File content as string
            filename: Optional filename for additional context

        Returns:
            Detected language or None if unknown
        """
        if not content:
            return None

        # First try filename-based detection
        if filename:
            lang = cls.detect_language_from_filename(filename)
            if lang:
                return lang

        # Look for shebangs (Unix scripts)
        lines = content.split("\n")
        if lines and lines[0].startswith("#!"):
            shebang = lines[0].lower()
            if "python" in shebang:
                return "python"
            elif "node" in shebang or "javascript" in shebang:
                return "javascript"
            elif "ruby" in shebang:
                return "ruby"
            elif "php" in shebang:
                return "php"
            elif any(shell in shebang for shell in ["bash", "sh", "zsh", "fish"]):
                return "shell"

        # Look for common language patterns in content
        content_lower = content.lower()

        # Python patterns
        if any(
            pattern in content for pattern in ["def ", "import ", "from ", "__name__"]
        ):
            return "python"

        # JavaScript/TypeScript patterns
        if any(
            pattern in content
            for pattern in ["function ", "const ", "let ", "var ", "=>"]
        ):
            if "interface " in content or "type " in content or ": " in content:
                return "typescript"
            return "javascript"

        # Java patterns
        if any(
            pattern in content
            for pattern in ["public class ", "private ", "public static void"]
        ):
            return "java"

        # C/C++ patterns
        if any(
            pattern in content for pattern in ["#include", "int main(", "void main("]
        ):
            if any(
                cpp_pattern in content
                for cpp_pattern in ["std::", "class ", "namespace "]
            ):
                return "cpp"
            return "c"

        # PHP patterns
        if content.startswith("<?php") or "<?php" in content:
            return "php"

        # HTML patterns
        if any(
            pattern in content_lower
            for pattern in ["<html", "<body", "<div", "<!doctype"]
        ):
            return "html"

        # CSS patterns
        if "{" in content and "}" in content and ":" in content and ";" in content:
            if any(
                pattern in content
                for pattern in ["color:", "margin:", "padding:", "font-"]
            ):
                return "css"

        # SQL patterns
        if any(
            pattern in content_lower
            for pattern in ["select ", "insert ", "update ", "delete ", "create table"]
        ):
            return "sql"

        # JSON pattern
        if content.strip().startswith("{") and content.strip().endswith("}"):
            try:
                import json

                json.loads(content)
                return "json"
            except Exception:
                pass

        # YAML patterns
        if any(pattern in content for pattern in [": ", "- ", "---"]):
            # Simple heuristic for YAML
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            yaml_like = sum(
                1 for line in lines if ": " in line or line.startswith("- ")
            )
            if yaml_like > len(lines) * 0.3:  # At least 30% of lines look like YAML
                return "yaml"

        return None

    @classmethod
    def is_supported_language(cls, language: str) -> bool:
        """
        Check if a language is supported for analysis.

        Args:
            language: Programming language name

        Returns:
            True if language is supported for analysis
        """
        if not language:
            return False

        # Get supported languages from config (we'll add this later)
        # For now, use a hardcoded list of commonly analyzed languages
        supported_languages = {
            "python",
            "javascript",
            "typescript",
            "java",
            "go",
            "rust",
            "cpp",
            "c",
            "csharp",
            "php",
            "ruby",
            "swift",
            "kotlin",
            "scala",
        }

        return language.lower() in supported_languages

    @classmethod
    def get_language_info(cls, filename: str, content: str = None) -> dict:
        """
        Get comprehensive language information for a file.

        Args:
            filename: Name of the file
            content: Optional file content

        Returns:
            Dictionary with language information
        """
        # Try filename detection first
        lang_from_filename = cls.detect_language_from_filename(filename)

        # Try content detection if available
        lang_from_content = None
        if content:
            lang_from_content = cls.detect_language_from_content(content, filename)

        # Determine final language (content detection takes precedence)
        detected_language = lang_from_content or lang_from_filename

        return {
            "filename": filename,
            "detected_language": detected_language,
            "detection_method": (
                "content"
                if lang_from_content
                else "filename"
                if lang_from_filename
                else "unknown"
            ),
            "is_supported": cls.is_supported_language(detected_language),
            "extension": Path(filename).suffix.lower() if filename else None,
        }


# Export the detector class
__all__ = ["LanguageDetector"]
