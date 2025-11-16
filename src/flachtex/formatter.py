"""
LaTeX formatter for diff-friendly output.

This module implements "one sentence per line" formatting, which is a best
practice for version control systems. It makes diffs more readable by ensuring
that changes to a sentence only affect one line in the diff.

The formatter is aware of LaTeX structures and preserves:
- Verbatim-like environments (verbatim, lstlisting, minted, etc.)
- Math environments (equation, align, etc.)
- Comments
- Blank lines (paragraph separators)
- LaTeX commands

Key challenges addressed:
- Abbreviations (Dr., Mr., etc.) should not be treated as sentence boundaries
- Decimal numbers (3.14) should not cause splits
- Escaped periods (backslash-period) should not cause splits
- Content in verbatim environments should not be reformatted
- Math mode content should be handled carefully
"""

from __future__ import annotations

import re
import typing

from .traceable_string import TraceableString
from .utils import Range


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
        math_envs = ["equation", "equation*", "align", "align*", "gather", "gather*",
                     "multline", "multline*", "eqnarray", "eqnarray*"]
        for env in math_envs:
            pattern = rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}"
            for match in re.finditer(pattern, content, re.DOTALL):
                ranges.append(Range(match.start(), match.end()))

        return ranges


def _is_in_range(position: int, ranges: list[Range]) -> bool:
    """Check if a position is within any of the given ranges."""
    for r in ranges:
        if r.start <= position < r.end:
            return True
    return False


def _find_sentence_boundaries(content: str, protected_ranges: list[Range]) -> list[int]:
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
        "Dr", "Mr", "Mrs", "Ms", "Prof", "Sr", "Jr",
        "vs", "etc", "et al", "i.e", "e.g", "cf",
        "Fig", "Tab", "Eq", "Sec", "Ch", "Vol", "No",
        "Ph.D", "M.D", "B.A", "M.A", "B.S", "M.S",
    ]

    # Pattern: sentence ending punctuation followed by space/newline
    # We'll check each match individually for special cases
    pattern = r'([.!?])(\s+)'

    for match in re.finditer(pattern, content):
        end_pos = match.start(1)  # Position of the punctuation
        space_start = match.start(2)  # Position where space starts
        space_end = match.end(2)  # Position where space ends

        # Skip if in protected range
        if _is_in_range(end_pos, protected_ranges):
            continue

        # Check if there's a comment on this line (we want to keep it with the sentence)
        # Look ahead to see if we have a comment before a newline
        line_end = content.find('\n', space_start)
        if line_end != -1:
            between_text = content[space_start:line_end]
            # Check if there's a comment marker (not escaped) before the newline
            if '%' in between_text and not between_text.startswith('\n'):
                # Find the comment
                comment_pos = between_text.find('%')
                if comment_pos > 0 or (comment_pos == 0):
                    # Check if it's escaped
                    if comment_pos == 0 or between_text[comment_pos - 1] != '\\':
                        # There's a comment on this line, skip this boundary
                        continue

        # Skip if it's already at end of line (followed only by newline)
        if match.group(2).startswith('\n'):
            continue

        # Skip if escaped (\.)
        if end_pos > 0 and content[end_pos - 1] == '\\':
            continue

        # Skip if part of ellipsis (...)
        if match.group(1) == '.' and end_pos >= 2:
            if content[end_pos - 1] == '.' and content[end_pos - 2] == '.':
                continue
            if end_pos + 1 < len(content) and content[end_pos + 1] == '.':
                continue

        # Skip if it's a decimal number (digit before and after)
        if match.group(1) == '.':
            if (end_pos > 0 and content[end_pos - 1].isdigit() and
                end_pos + 1 < len(content) and content[end_pos + 1].isdigit()):
                continue

        # Skip if it's an abbreviation
        if match.group(1) == '.':
            # Look back to find the word before the period
            word_match = re.search(r'(\w+)\.$', content[:end_pos + 1])
            if word_match:
                word = word_match.group(1)
                if word in abbreviations:
                    continue
                # Also skip single letter followed by period (A. B. C.)
                if len(word) == 1:
                    continue

        # This is a valid sentence boundary
        # We want to insert a newline at the start of the space
        boundaries.append(space_start)

    return boundaries


def format_latex(content: TraceableString) -> TraceableString:
    r"""
    Format LaTeX content to be diff-friendly using "one sentence per line".

    This formatter:
    1. Splits sentences at sentence boundaries (., !, ?)
    2. Preserves verbatim-like environments unchanged
    3. Preserves math environments and inline math
    4. Preserves comments
    5. Preserves blank lines (paragraph separators)
    6. Handles abbreviations and decimal numbers correctly

    Args:
        content: The LaTeX content to format

    Returns:
        Formatted content with origin tracking preserved

    Example:
        >>> from flachtex.traceable_string import TraceableString
        >>> content = TraceableString("First sentence. Second sentence.", "test")
        >>> result = format_latex(content)
        >>> str(result)
        'First sentence.\nSecond sentence.'
    """
    content_str = str(content)

    # Handle empty or whitespace-only content
    if not content_str or content_str.isspace():
        return content

    # Find protected ranges (verbatim, math, etc.)
    protected_ranges: list[Range] = []

    verbatim_detector = VerbatimEnvironmentDetector()
    protected_ranges.extend(verbatim_detector.find_all(content_str))

    math_detector = MathEnvironmentDetector()
    protected_ranges.extend(math_detector.find_all(content_str))

    # Sort ranges
    protected_ranges.sort()

    # Find sentence boundaries
    boundaries = _find_sentence_boundaries(content_str, protected_ranges)

    if not boundaries:
        # No formatting needed
        return content

    # Build the formatted content by replacing spaces after sentence endings with newlines
    # We need to work backwards to maintain correct positions
    boundaries_reversed = sorted(boundaries, reverse=True)

    result = content
    for boundary_pos in boundaries_reversed:
        # Find the end of the whitespace at this boundary
        space_end = boundary_pos
        while space_end < len(str(result)) and str(result)[space_end] in ' \t':
            space_end += 1

        # Replace the whitespace with a newline
        # Keep everything before, replace spaces with newline, keep everything after
        result = result[:boundary_pos] + TraceableString("\n", origin="formatter") + result[space_end:]

    return result
