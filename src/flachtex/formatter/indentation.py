"""
Indentation support for LaTeX formatting.

This module handles applying indentation to LaTeX content based on environment
nesting while preserving origin tracking.
"""

from __future__ import annotations

from ..traceable_string import TraceableString
from .environment_tracker import EnvironmentTracker


def apply_indentation(content: TraceableString, indent_size: int) -> TraceableString:
    """
    Apply indentation to content based on environment nesting.

    Args:
        content: The content to indent
        indent_size: Number of spaces per indentation level

    Returns:
        Content with indentation applied
    """
    if indent_size <= 0:
        return content

    content_str = str(content)
    tracker = EnvironmentTracker(content_str)
    indentation_map = tracker.get_indentation_map()

    lines = content_str.split("\n")
    result_lines = []

    for line_num, line in enumerate(lines):
        indent_level = indentation_map.get(line_num, 0)
        indent_str = " " * (indent_level * indent_size)

        # Remove existing leading whitespace and add our indentation
        stripped_line = line.lstrip()
        if stripped_line:  # Non-empty line
            result_lines.append(indent_str + stripped_line)
        else:  # Empty line
            result_lines.append("")

    result_str = "\n".join(result_lines)

    # Rebuild as TraceableString, maintaining origins where possible
    # For simplicity, we'll reconstruct by finding matches
    # This is a bit complex with TraceableString, so let's do it carefully
    return rebuild_traceable_string(content, result_str)


def rebuild_traceable_string(
    original: TraceableString, new_str: str
) -> TraceableString:
    """
    Rebuild a TraceableString after formatting, preserving origins.

    This works line-by-line, matching stripped content and adding indentation.
    """
    orig_str = str(original)
    orig_lines = orig_str.split("\n")
    new_lines = new_str.split("\n")

    # If line counts don't match, something went wrong - just create new TraceableString
    if len(orig_lines) != len(new_lines):
        return TraceableString(new_str, origin="formatter")

    result = TraceableString("", origin="formatter")
    orig_pos = 0

    for line_idx, (orig_line, new_line) in enumerate(zip(orig_lines, new_lines)):
        # Add newline from previous line
        if line_idx > 0:
            result = result + TraceableString("\n", origin="formatter")
            orig_pos += 1  # Account for newline in original

        # Find leading spaces in new line
        new_leading_spaces = len(new_line) - len(new_line.lstrip())
        new_content = new_line.lstrip()

        # Find leading spaces in original line
        orig_leading_spaces = len(orig_line) - len(orig_line.lstrip())
        orig_content = orig_line.lstrip()

        # Add the new leading spaces (from formatter)
        if new_leading_spaces > 0:
            result = result + TraceableString(
                " " * new_leading_spaces, origin="formatter"
            )

        # Add the content from original (preserving origin)
        if orig_content:
            # Find where this content is in the original string
            content_start = orig_pos + orig_leading_spaces
            content_end = content_start + len(orig_content)
            result = result + original[content_start:content_end]

        # Move position forward
        orig_pos += len(orig_line)

    return result
