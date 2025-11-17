"""
Comment removal functionality for LaTeX documents.

Comments should be removed at the end of processing, as they may contain
directives for flachtex. Removing them during preprocessing could lead to
unwanted side effects.

If you don't want comments in the output, apply the remove_comments function
to the flattened content.
"""

from __future__ import annotations

import re

from .rules.skip_rules import CommentsPackageSkipRule, apply_skip_rules
from .traceable_string import TraceableString


def remove_comments(content: TraceableString) -> TraceableString:
    """
    Remove LaTeX comments from the content.

    This function removes both:
    1. Line comments (% to end of line, not preceded by backslash)
    2. Block comments from the comments package (\\begin{comment}...\\end{comment})

    Args:
        content: The traceable string content to process

    Returns:
        The content with comments removed

    Example:
        >>> from flachtex.traceable_string import TraceableString
        >>> content = TraceableString("text % comment\\nmore text", origin="test")
        >>> result = remove_comments(content)
        >>> str(result)
        'text more text'
    """
    # Find all line comments (% to end of line, not preceded by backslash)
    # Capture trailing whitespace before the comment, but keep the newline
    regex = re.compile(r"^.*?(?<!\\)(?P<ws>[ \t]*)(?P<comment>%.*?)(?P<nl>\n)", re.MULTILINE)
    replacements: list[tuple[int, int, str]] = []  # (start, end, replacement)
    for match in regex.finditer(str(content)):
        # Remove the whitespace and comment, but keep the newline
        ws_start = match.start("ws")
        nl_start = match.start("nl")
        nl_end = match.end("nl")
        # Replace "  % comment\n" with just "\n"
        replacements.append((ws_start, nl_start, ""))

    # Apply replacements in reverse order to maintain positions
    for start, end, replacement in reversed(replacements):
        content = content[:start] + TraceableString(replacement, origin="comment_removal") + content[end:]

    # Remove block comments from the comments package
    content = apply_skip_rules(content, [CommentsPackageSkipRule()])
    return content
