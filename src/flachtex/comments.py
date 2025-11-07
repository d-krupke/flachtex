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
    regex = re.compile(r"^.*?(?<!\\)(?P<comment>%.*\n)", re.MULTILINE)
    comments: list[tuple[int, int]] = []
    for match in regex.finditer(str(content)):
        comments.append((match.start("comment"), match.end("comment")))
    comments.sort()

    # Remove comments by slicing, tracking offset as content shrinks
    offset = 0
    for start, end in comments:
        content = content[: start + offset] + content[end + offset :]
        offset -= end - start

    # Remove block comments from the comments package
    content = apply_skip_rules(content, [CommentsPackageSkipRule()])
    return content
