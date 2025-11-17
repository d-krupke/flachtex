"""
Core LaTeX formatting functionality.

This module contains the main format_latex function that orchestrates
sentence splitting, indentation, and blank line normalization.
"""

from __future__ import annotations

from ..traceable_string import TraceableString
from ..utils import Range
from .detectors import (
    CommentDetector,
    MathEnvironmentDetector,
    NoFormatDetector,
    RawDetector,
    VerbatimEnvironmentDetector,
)
from .indentation import apply_indentation
from .normalization import normalize_blank_lines
from .sentence_splitter import find_sentence_boundaries


def format_latex(
    content: TraceableString,
    indent: int = 0,
    sentence_per_line: bool = True,
) -> TraceableString:
    r"""
    Format LaTeX content to be diff-friendly using "one sentence per line".

    This formatter:
    1. Splits sentences at sentence boundaries (., !, ?) (if sentence_per_line=True)
    2. Indents content inside environments (if indent > 0)
    3. Normalizes excessive blank lines (reduces multiple blank lines to one)
    4. Preserves verbatim-like environments unchanged
    5. Preserves math environments (but indents them)
    6. Preserves comments (sentences inside comments are not split)
    7. Handles abbreviations and decimal numbers correctly

    Args:
        content: The LaTeX content to format
        indent: Number of spaces per indentation level (0 = no indentation)
        sentence_per_line: Whether to split sentences onto separate lines

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

    result = content

    # Apply sentence splitting if requested
    if sentence_per_line:
        # Find protected ranges (verbatim, math, comments, RAW markers, no-format markers, etc.)
        protected_ranges: list[Range] = []

        verbatim_detector = VerbatimEnvironmentDetector()
        protected_ranges.extend(verbatim_detector.find_all(content_str))

        math_detector = MathEnvironmentDetector()
        protected_ranges.extend(math_detector.find_all(content_str))

        comment_detector = CommentDetector()
        protected_ranges.extend(comment_detector.find_all(content_str))

        # RAW markers take priority - they protect from everything
        raw_detector = RawDetector()
        protected_ranges.extend(raw_detector.find_all(content_str))

        no_format_detector = NoFormatDetector()
        protected_ranges.extend(no_format_detector.find_all(content_str))

        # Sort ranges
        protected_ranges.sort()

        # Find sentence boundaries
        boundaries = find_sentence_boundaries(content_str, protected_ranges)

        # Apply sentence splitting if we have boundaries
        if boundaries:
            # Build the formatted content by replacing spaces after sentence endings with newlines
            # We need to work backwards to maintain correct positions
            boundaries_reversed = sorted(boundaries, reverse=True)

            for boundary_pos in boundaries_reversed:
                # Find the end of the whitespace at this boundary
                space_end = boundary_pos
                while space_end < len(str(result)) and str(result)[space_end] in " \t":
                    space_end += 1

                # Replace the whitespace with a newline
                # Keep everything before, replace spaces with newline, keep everything after
                result = (
                    result[:boundary_pos]
                    + TraceableString("\n", origin="formatter")
                    + result[space_end:]
                )

    # Apply indentation if requested
    if indent > 0:
        result = apply_indentation(result, indent)

    # Normalize blank lines (reduce excessive blank lines)
    result = normalize_blank_lines(result)

    return result
