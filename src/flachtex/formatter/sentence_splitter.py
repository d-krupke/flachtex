"""
Sentence boundary detection for LaTeX content.

This module handles splitting LaTeX content into sentences while respecting
abbreviations, decimal numbers, and protected ranges.
"""

from __future__ import annotations

import re

from ..utils import Range


def _is_in_range(position: int, ranges: list[Range]) -> bool:
    """Check if a position is within any of the given ranges."""
    for r in ranges:
        if r.start <= position < r.end:
            return True
    return False


def find_sentence_boundaries(content: str, protected_ranges: list[Range]) -> list[int]:
    r"""
    Find positions where sentences end (and should be followed by newline).

    A sentence boundary is a period, question mark, or exclamation mark
    followed by whitespace, but not in the following cases:
    - Inside protected ranges (verbatim, math, etc.)
    - After abbreviations (Dr., Mr., etc.)
    - In decimal numbers (3.14)
    - Escaped periods (\.)
    - Ellipsis (...)

    Args:
        content: The LaTeX content
        protected_ranges: Ranges that should not be reformatted

    Returns:
        List of positions where line breaks should be inserted
    """
    boundaries: list[int] = []

    # Common abbreviations that should not trigger sentence boundaries
    # This is not exhaustive but covers common cases
    abbreviations = [
        "Dr",
        "Mr",
        "Mrs",
        "Ms",
        "Prof",
        "Sr",
        "Jr",
        "vs",
        "etc",
        "et al",
        "i.e",
        "e.g",
        "cf",
        "Fig",
        "Tab",
        "Eq",
        "Sec",
        "Ch",
        "Vol",
        "No",
        "Ph.D",
        "M.D",
        "B.A",
        "M.A",
        "B.S",
        "M.S",
    ]

    # Pattern: sentence ending punctuation followed by space/newline
    # We'll check each match individually for special cases
    pattern = r"([.!?])(\s+)"

    for match in re.finditer(pattern, content):
        end_pos = match.start(1)  # Position of the punctuation
        space_start = match.start(2)  # Position where space starts
        space_end = match.end(2)  # Position where space ends

        # Skip if in protected range (includes comments, verbatim, math)
        if _is_in_range(end_pos, protected_ranges):
            continue

        # Skip if the space after the boundary is in a protected range
        # This prevents splitting whitespace that's part of a comment or other protected content
        if _is_in_range(space_start, protected_ranges):
            continue

        # Skip if there's a comment immediately after this boundary (on the same line)
        # We want to keep the comment attached to its sentence
        # But still allow splitting earlier sentences on the same line
        line_end = content.find("\n", space_start)
        if line_end == -1:
            line_end = len(content)

        # Check if there's a comment starting right after the spaces at this boundary
        next_nonspace = space_end
        while next_nonspace < line_end and content[next_nonspace] in " \t":
            next_nonspace += 1

        if next_nonspace < line_end and content[next_nonspace] == "%":
            # Comment immediately follows this sentence boundary
            # Keep the comment with this sentence
            continue

        # Skip if it's already at end of line (followed only by newline)
        if match.group(2).startswith("\n"):
            continue

        # Skip if escaped (\.)
        if end_pos > 0 and content[end_pos - 1] == "\\":
            continue

        # Skip if part of ellipsis (...)
        if match.group(1) == "." and end_pos >= 2:
            if content[end_pos - 1] == "." and content[end_pos - 2] == ".":
                continue
            if end_pos + 1 < len(content) and content[end_pos + 1] == ".":
                continue

        # Skip if it's a decimal number (digit before and after)
        if match.group(1) == ".":
            if (
                end_pos > 0
                and content[end_pos - 1].isdigit()
                and end_pos + 1 < len(content)
                and content[end_pos + 1].isdigit()
            ):
                continue

        # Skip if it's an abbreviation
        if match.group(1) == ".":
            # Look back to find the word before the period
            word_match = re.search(r"(\w+)\.$", content[: end_pos + 1])
            if word_match:
                word = word_match.group(1)
                if word in abbreviations:
                    continue
                # Also skip single letter followed by period (A. B. C.)
                # But not digits (Text 2. should be split)
                if len(word) == 1 and word.isalpha():
                    continue

        # This is a valid sentence boundary
        # We want to insert a newline at the start of the space
        boundaries.append(space_start)

    return boundaries
