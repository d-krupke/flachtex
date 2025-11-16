"""
Detectors for identifying protected ranges in LaTeX content.

Protected ranges include verbatim environments, math environments, and comments
that should not be reformatted during sentence splitting.
"""

from __future__ import annotations

import re

from ..utils import Range


class VerbatimEnvironmentDetector:
    """Detects verbatim-like environments that should not be reformatted."""

    # Environments where content should be preserved as-is
    VERBATIM_ENVIRONMENTS = [
        "verbatim",
        "Verbatim",  # from fancyvrb
        "lstlisting",
        "minted",
        "algorithmic",
        "algorithm",
        "lstinputlisting",
    ]

    def find_all(self, content: str) -> list[Range]:
        """
        Find all verbatim-like environment ranges in the content.

        Args:
            content: The LaTeX content to search

        Returns:
            List of ranges that should be preserved as-is
        """
        ranges: list[Range] = []
        for env in self.VERBATIM_ENVIRONMENTS:
            # Match \begin{env}...\end{env}, including optional arguments
            pattern = (
                rf"\\begin\{{{env}\}}(?:\[.*?\])?(?:\{{.*?\}})?"
                rf".*?"
                rf"\\end\{{{env}\}}"
            )
            regex = re.compile(pattern, re.DOTALL)
            for match in regex.finditer(content):
                ranges.append(Range(match.start(), match.end()))
        return ranges


class MathEnvironmentDetector:
    """Detects math environments and inline math."""

    def find_all(self, content: str) -> list[Range]:
        """
        Find all math mode ranges in the content.

        Args:
            content: The LaTeX content to search

        Returns:
            List of ranges containing math
        """
        ranges: list[Range] = []

        # Display math: \[ ... \]
        pattern = r"\\\[.*?\\\]"
        for match in re.finditer(pattern, content, re.DOTALL):
            ranges.append(Range(match.start(), match.end()))

        # Display math: $$ ... $$
        pattern = r"\$\$.*?\$\$"
        for match in re.finditer(pattern, content, re.DOTALL):
            ranges.append(Range(match.start(), match.end()))

        # Math environments
        math_envs = [
            "equation",
            "equation*",
            "align",
            "align*",
            "gather",
            "gather*",
            "multline",
            "multline*",
            "eqnarray",
            "eqnarray*",
        ]
        for env in math_envs:
            pattern = rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}"
            for match in re.finditer(pattern, content, re.DOTALL):
                ranges.append(Range(match.start(), match.end()))

        return ranges


class CommentDetector:
    """Detects LaTeX comments (% to end of line)."""

    def find_all(self, content: str) -> list[Range]:
        """
        Find all comment ranges in the content.

        A comment starts with an unescaped % and continues to the end of the line
        (but does not include the newline character).

        Args:
            content: The LaTeX content to search

        Returns:
            List of comment ranges that should be protected from sentence splitting
        """
        ranges: list[Range] = []

        # Match % followed by anything until end of line
        # But not if the % is escaped (preceded by \)
        for match in re.finditer(r"(?<!\\)%.*", content):
            ranges.append(Range(match.start(), match.end()))

        return ranges
