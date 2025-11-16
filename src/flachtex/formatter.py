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


class EnvironmentTracker:
    """Tracks LaTeX environment nesting for indentation."""

    # Environments that should be excluded from indentation
    EXCLUDE_FROM_INDENTATION = [
        "verbatim",
        "Verbatim",
        "lstlisting",
        "minted",
    ]

    def __init__(self, content: str):
        """Initialize with the content to track."""
        self.content = content
        self.lines = content.split('\n')

    def get_indentation_map(self) -> dict[int, int]:
        """
        Create a map of line number to indentation level.

        Returns:
            Dictionary mapping line number (0-indexed) to indentation level
        """
        indentation_map: dict[int, int] = {}
        current_level = 0
        inside_excluded_env = False
        excluded_env_stack: list[str] = []

        for line_num, line in enumerate(self.lines):
            # Check for environment end first
            end_match = re.match(r'^\s*\\end\{([^}]+)\}', line)
            if end_match:
                env_name = end_match.group(1)
                if excluded_env_stack and excluded_env_stack[-1] == env_name:
                    # Exiting an excluded environment
                    excluded_env_stack.pop()
                    if not excluded_env_stack:
                        inside_excluded_env = False
                    # \end line gets parent indentation
                    indentation_map[line_num] = max(0, current_level - 1)
                    current_level = max(0, current_level - 1)
                elif not inside_excluded_env:
                    # Exiting a normal environment
                    current_level = max(0, current_level - 1)
                    # \end line gets current level (after decrement)
                    indentation_map[line_num] = current_level
                else:
                    # Inside excluded environment, no indentation
                    indentation_map[line_num] = 0
            else:
                # Not an \end line, use current level
                indentation_map[line_num] = 0 if inside_excluded_env else current_level

            # Check for environment begin
            begin_match = re.match(r'^\s*\\begin\{([^}]+)\}', line)
            if begin_match:
                env_name = begin_match.group(1)
                if env_name in self.EXCLUDE_FROM_INDENTATION:
                    # Entering an excluded environment
                    excluded_env_stack.append(env_name)
                    inside_excluded_env = True
                    # \begin line stays at current level (before increment)
                elif not inside_excluded_env:
                    # Entering a normal environment
                    # \begin line stays at current level
                    current_level += 1

        return indentation_map


def _apply_indentation(
    content: TraceableString, indent_size: int
) -> TraceableString:
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

    lines = content_str.split('\n')
    result_lines = []

    for line_num, line in enumerate(lines):
        indent_level = indentation_map.get(line_num, 0)
        indent_str = ' ' * (indent_level * indent_size)

        # Remove existing leading whitespace and add our indentation
        stripped_line = line.lstrip()
        if stripped_line:  # Non-empty line
            result_lines.append(indent_str + stripped_line)
        else:  # Empty line
            result_lines.append('')

    result_str = '\n'.join(result_lines)

    # Rebuild as TraceableString, maintaining origins where possible
    # For simplicity, we'll reconstruct by finding matches
    # This is a bit complex with TraceableString, so let's do it carefully
    return _rebuild_traceable_string(content, result_str)


def _rebuild_traceable_string(
    original: TraceableString, new_str: str
) -> TraceableString:
    """
    Rebuild a TraceableString after formatting, preserving origins.

    This is done by tracking which parts of the original string
    correspond to which parts of the new string.
    """
    # For now, we'll use a simple approach: build up the result
    # by finding differences and inserting formatter-originated content
    result = TraceableString("", origin="formatter")

    orig_str = str(original)
    orig_pos = 0
    new_pos = 0

    while new_pos < len(new_str) and orig_pos < len(orig_str):
        # Check if we have matching content
        if new_str[new_pos] == orig_str[orig_pos]:
            # Find the extent of the match
            match_len = 0
            while (new_pos + match_len < len(new_str) and
                   orig_pos + match_len < len(orig_str) and
                   new_str[new_pos + match_len] == orig_str[orig_pos + match_len]):
                match_len += 1

            # Add the matched portion from original (preserving origins)
            result = result + original[orig_pos:orig_pos + match_len]
            new_pos += match_len
            orig_pos += match_len
        else:
            # We have a difference - this is likely added indentation
            # Skip the new content (spaces) and mark as formatter-added
            if new_str[new_pos] == ' ':
                space_len = 0
                while new_pos + space_len < len(new_str) and new_str[new_pos + space_len] == ' ':
                    space_len += 1
                result = result + TraceableString(' ' * space_len, origin="formatter")
                new_pos += space_len
            elif orig_str[orig_pos] == ' ':
                # Original had spaces that we're removing
                orig_pos += 1
            else:
                # Mismatch - shouldn't happen, but skip both
                new_pos += 1
                orig_pos += 1

    # Handle any remaining content
    if orig_pos < len(orig_str):
        # Original has more content
        pass  # We've consumed all new content
    if new_pos < len(new_str):
        # New string has more content (shouldn't happen)
        result = result + TraceableString(new_str[new_pos:], origin="formatter")

    return result


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
    3. Preserves verbatim-like environments unchanged
    4. Preserves math environments (but indents them)
    5. Preserves comments
    6. Preserves blank lines (paragraph separators)
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

        # Apply sentence splitting if we have boundaries
        if boundaries:
            # Build the formatted content by replacing spaces after sentence endings with newlines
            # We need to work backwards to maintain correct positions
            boundaries_reversed = sorted(boundaries, reverse=True)

            for boundary_pos in boundaries_reversed:
                # Find the end of the whitespace at this boundary
                space_end = boundary_pos
                while space_end < len(str(result)) and str(result)[space_end] in ' \t':
                    space_end += 1

                # Replace the whitespace with a newline
                # Keep everything before, replace spaces with newline, keep everything after
                result = result[:boundary_pos] + TraceableString("\n", origin="formatter") + result[space_end:]

    # Apply indentation if requested
    if indent > 0:
        result = _apply_indentation(result, indent)

    return result
