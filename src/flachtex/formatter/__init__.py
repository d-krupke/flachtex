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

from .core import format_latex

__all__ = ["format_latex"]
