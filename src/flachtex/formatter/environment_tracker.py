"""
Environment tracking for LaTeX indentation.

This module tracks LaTeX environment nesting to determine appropriate indentation
levels for each line.
"""

from __future__ import annotations

import re


class EnvironmentTracker:
    """Tracks LaTeX environment nesting for indentation."""

    # Verbatim-like environments: content must be preserved as-is (no indentation)
    VERBATIM_ENVIRONMENTS = [
        "verbatim",
        "Verbatim",
        "lstlisting",
        "minted",
        "algorithmic",
    ]

    # Document-level environments: don't increase indentation level
    # (but nested environments inside them still get indented)
    DOCUMENT_LEVEL_ENVIRONMENTS = [
        "document",
        "abstract",
    ]

    def __init__(self, content: str):
        """Initialize with the content to track."""
        self.content = content
        self.lines = content.split("\n")

    def get_indentation_map(self) -> dict[int, int]:
        """
        Create a map of line number to indentation level.

        Returns:
            Dictionary mapping line number (0-indexed) to indentation level
        """
        indentation_map: dict[int, int] = {}
        current_level = 0
        inside_verbatim = False
        verbatim_stack: list[str] = []

        for line_num, line in enumerate(self.lines):
            # Check for environment end first
            end_match = re.match(r"^\s*\\end\{([^}]+)\}", line)
            if end_match:
                env_name = end_match.group(1)
                if verbatim_stack and verbatim_stack[-1] == env_name:
                    # Exiting a verbatim environment
                    verbatim_stack.pop()
                    if not verbatim_stack:
                        inside_verbatim = False
                    # \end line gets no indentation (inside verbatim)
                    indentation_map[line_num] = 0
                elif not inside_verbatim:
                    # Exiting a normal environment
                    if env_name not in self.DOCUMENT_LEVEL_ENVIRONMENTS:
                        current_level = max(0, current_level - 1)
                    # \end line gets current level (after decrement)
                    indentation_map[line_num] = current_level
                else:
                    # Inside verbatim environment, no indentation
                    indentation_map[line_num] = 0
            else:
                # Not an \end line, use current level
                indentation_map[line_num] = 0 if inside_verbatim else current_level

            # Check for environment begin
            begin_match = re.match(r"^\s*\\begin\{([^}]+)\}", line)
            if begin_match:
                env_name = begin_match.group(1)
                if env_name in self.VERBATIM_ENVIRONMENTS:
                    # Entering a verbatim environment
                    verbatim_stack.append(env_name)
                    inside_verbatim = True
                    # \begin line stays at current level (before increment)
                elif not inside_verbatim:
                    # Entering a normal or document-level environment
                    # \begin line stays at current level
                    # Only increment level if not a document-level environment
                    if env_name not in self.DOCUMENT_LEVEL_ENVIRONMENTS:
                        current_level += 1

        return indentation_map
