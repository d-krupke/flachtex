"""
Blank line normalization for LaTeX formatting.

This module handles reducing excessive blank lines while preserving
paragraph structure and origin tracking.
"""

from __future__ import annotations

import re

from ..traceable_string import TraceableString


def normalize_blank_lines(content: TraceableString) -> TraceableString:
    """
    Normalize excessive blank lines in the content.

    - Multiple consecutive blank lines are reduced to one blank line
    - Leading blank lines are removed
    - Trailing blank lines are reduced to at most one newline

    Args:
        content: The content to normalize

    Returns:
        Content with normalized blank lines
    """
    orig_str = str(content)

    # Handle empty content
    if not orig_str:
        return content

    # Find leading newlines to skip
    leading_newlines = len(orig_str) - len(orig_str.lstrip('\n'))

    # Find trailing newlines
    had_trailing_newline = orig_str.endswith('\n')
    orig_stripped = orig_str.rstrip('\n')

    # Work with the stripped version (no leading/trailing newlines)
    # We'll add back the trailing newline at the end
    work_start = leading_newlines
    work_end = len(orig_stripped)

    # Find all positions where we have 3+ consecutive newlines IN THE MIDDLE
    # (not counting leading/trailing which we already handled)
    excessive_newline_ranges = []
    for match in re.finditer(r'\n{3,}', orig_str):
        # Only process if this match is in the middle (not in leading/trailing areas)
        if match.start() >= work_start and match.end() <= work_end:
            # Keep first 2 newlines, mark the rest for removal
            keep_until = match.start() + 2
            excessive_newline_ranges.append((keep_until, match.end()))

    # Build result by concatenating chunks from original
    chunks = []
    current_pos = work_start

    # Add chunks between excessive newline ranges
    for skip_start, skip_end in excessive_newline_ranges:
        if current_pos < skip_start:
            chunks.append(content[current_pos:skip_start])
        current_pos = skip_end

    # Add final chunk
    if current_pos < work_end:
        chunks.append(content[current_pos:work_end])

    # Add back one trailing newline if there was one
    if had_trailing_newline:
        chunks.append(TraceableString('\n', origin="formatter"))

    # Concatenate all chunks
    if not chunks:
        return TraceableString("", origin="formatter")

    result = chunks[0]
    for chunk in chunks[1:]:
        result = result + chunk

    return result
