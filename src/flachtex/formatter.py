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
        self.lines = content.split('\n')

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
            end_match = re.match(r'^\s*\\end\{([^}]+)\}', line)
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
            begin_match = re.match(r'^\s*\\begin\{([^}]+)\}', line)
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

    This works line-by-line, matching stripped content and adding indentation.
    """
    orig_str = str(original)
    orig_lines = orig_str.split('\n')
    new_lines = new_str.split('\n')

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
            result = result + TraceableString(' ' * new_leading_spaces, origin="formatter")

        # Add the content from original (preserving origin)
        if orig_content:
            # Find where this content is in the original string
            content_start = orig_pos + orig_leading_spaces
            content_end = content_start + len(orig_content)
            result = result + original[content_start:content_end]

        # Move position forward
        orig_pos += len(orig_line)

    return result


def _normalize_blank_lines(content: TraceableString) -> TraceableString:
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
    import re

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
    6. Preserves comments
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

    # Normalize blank lines (reduce excessive blank lines)
    result = _normalize_blank_lines(result)

    return result
