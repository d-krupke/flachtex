"""Tests for utility classes and functions.

The Range class is used throughout flachtex to track regions of text that need
special handling (skip blocks, imports, verbatim environments, etc.). Proper
intersection detection is critical to prevent conflicting rules.

The compute_row_index function enables accurate error reporting by mapping
character positions to line numbers in LaTeX source files.
"""

import pytest

from flachtex.utils import Range, compute_row_index


class TestRange:
    """
    Test the Range class used to track text regions.

    Users benefit from Range intersection detection when:
    - Preventing overlapping %%FLACHTEX-SKIP-START blocks (would be ambiguous)
    - Detecting conflicting import statements
    - Ensuring skip rules and import rules don't interfere with each other
    """

    def test_basic_construction(self):
        """Range should store start and end positions for tracking text regions."""
        r = Range(0, 10)
        assert r.start == 0, "Range should track where a region starts"
        assert r.end == 10, "Range should track where a region ends"

    def test_length(self):
        """Range length is needed to calculate offset adjustments after text removal."""
        r = Range(5, 15)
        assert len(r) == 10, "Length should be end - start for calculating text removal impact"

    def test_length_zero(self):
        """Zero-length ranges can occur at document boundaries."""
        r = Range(5, 5)
        assert len(r) == 0, "Zero-length range should be supported for edge cases"

    def test_repr(self):
        """Readable representation helps debug which text regions are being processed."""
        r = Range(10, 20)
        assert repr(r) == "[10:20]", "Range representation should clearly show start:end positions"

    def test_intersects_overlapping(self):
        """
        Overlapping skip blocks would be ambiguous - users need clear error messages.
        Example: If user writes overlapping %%FLACHTEX-SKIP-START blocks, which takes precedence?
        """
        r1 = Range(0, 10)  # First skip block
        r2 = Range(5, 15)  # Second skip block overlaps with first
        assert r1.intersects(r2), "Overlapping ranges must be detected to prevent ambiguous skip regions"
        assert r2.intersects(r1), "Intersection detection must be symmetric"

    def test_intersects_contained(self):
        """
        Nested skip blocks are also ambiguous and should be detected.
        Example: %%FLACHTEX-SKIP-START ... %%FLACHTEX-SKIP-START ... %%FLACHTEX-SKIP-STOP
        """
        r1 = Range(0, 20)  # Outer skip block
        r2 = Range(5, 15)  # Inner skip block (fully contained)
        assert r1.intersects(r2), "Nested skip blocks must be detected as intersecting"
        assert r2.intersects(r1), "Intersection must work both directions for nested blocks"

    def test_intersects_adjacent_no_overlap(self):
        """
        Adjacent skip blocks are allowed - users can have multiple separate skip regions.
        Example: Skip lines 1-10, then skip lines 10-20 (no conflict).
        """
        r1 = Range(0, 10)
        r2 = Range(10, 20)
        assert not r1.intersects(r2), "Adjacent ranges should NOT intersect - allows multiple skip blocks"
        assert not r2.intersects(r1), "Adjacent check must be symmetric"

    def test_intersects_separate(self):
        """Completely separate ranges should not intersect - normal case for multiple skip blocks."""
        r1 = Range(0, 10)
        r2 = Range(20, 30)
        assert not r1.intersects(r2), "Separate skip blocks should be independent"
        assert not r2.intersects(r1), "Separation check must be symmetric"

    def test_intersects_touching_at_start(self):
        """
        Ranges touching at boundaries are not considered intersecting.
        This allows skip blocks to be immediately adjacent without conflict.
        """
        r1 = Range(10, 20)
        r2 = Range(5, 10)
        assert not r1.intersects(r2), "Boundary-touching ranges should NOT intersect"
        assert not r2.intersects(r1), "Boundary check must be symmetric"

    def test_intersects_single_point_overlap(self):
        """
        Even a single character overlap is ambiguous and must be detected.
        Prevents edge cases where skip blocks share one character.
        """
        r1 = Range(0, 11)
        r2 = Range(10, 20)
        assert r1.intersects(r2), "Single character overlap must be detected to avoid ambiguity"
        assert r2.intersects(r1), "Single character overlap detection must be symmetric"

    def test_intersects_same_range(self):
        """A range always intersects with itself (sanity check)."""
        r = Range(5, 15)
        assert r.intersects(r), "Range must intersect with itself"

    def test_less_than(self):
        """
        Ranges are sorted by start position for sequential processing.
        This ensures skip blocks are processed in document order.
        """
        r1 = Range(0, 10)
        r2 = Range(5, 15)
        r3 = Range(10, 20)
        assert r1 < r2, "Earlier range should be less than later range"
        assert r1 < r3, "First range should be less than third range"
        assert r2 < r3, "Second range should be less than third range"
        assert not r2 < r1, "Later range should not be less than earlier range"
        assert not r3 < r1, "Last range should not be less than first range"

    def test_less_than_equal(self):
        """
        Ranges with same start position are equal for sorting purposes.
        Ensures consistent ordering when processing document.
        """
        r1 = Range(0, 10)
        r2 = Range(0, 20)
        r3 = Range(5, 15)
        assert r1 <= r2, "Range should be <= another range with same start"
        assert r1 <= r3, "Earlier range should be <= later range"
        assert r2 <= r2, "Range should be <= itself"
        assert not r3 <= r1, "Later range should not be <= earlier range"

    def test_sorting(self):
        """
        Ranges must be sortable for processing in document order.
        Users expect skip blocks to be processed top-to-bottom through their document.
        """
        ranges = [Range(10, 20), Range(0, 5), Range(5, 15), Range(0, 10)]
        sorted_ranges = sorted(ranges)
        assert sorted_ranges[0].start == 0, "First sorted range should start at position 0"
        assert sorted_ranges[1].start == 0, "Second sorted range should also start at position 0"
        assert sorted_ranges[2].start == 5, "Third sorted range should start at position 5"
        assert sorted_ranges[3].start == 10, "Last sorted range should start at position 10"


class TestComputeRowIndex:
    """
    Test the compute_row_index function for error reporting.

    Users benefit from accurate line numbers when:
    - Viewing error messages about malformed LaTeX
    - Debugging which file caused a circular dependency
    - Understanding origin tracking output

    This function converts character positions to line numbers.
    """

    def test_empty_string(self):
        """Empty document still has line 1 (position 0) for error reporting."""
        result = compute_row_index("")
        assert result == [0], "Empty document should have one line starting at position 0"

    def test_single_line(self):
        """Single-line document has one entry in the index."""
        result = compute_row_index("hello world")
        assert result == [0], "Single-line document should have only line 1 at position 0"

    def test_two_lines(self):
        """
        Two-line document allows mapping errors to line 1 or line 2.
        Example: "line1\nline2" - error at position 8 is on line 2.
        """
        result = compute_row_index("line1\nline2")
        assert result == [0, 6], "Two lines should start at positions 0 and 6 (after \\n)"

    def test_three_lines(self):
        """Multiple lines enable accurate error reporting throughout document."""
        result = compute_row_index("a\nb\nc")
        assert result == [0, 2, 4], "Three lines should start at positions 0, 2, and 4"

    def test_empty_lines(self):
        """
        Empty lines still need position tracking for accurate error reporting.
        Users need to know if error is on line 1, 2, or 3 even if lines are blank.
        """
        result = compute_row_index("\n\n")
        assert result == [0, 1, 2], "Empty lines should still be indexed for error reporting"

    def test_trailing_newline(self):
        """
        Trailing newline creates an (empty) third line for error reporting.
        Important when errors occur at end of file.
        """
        result = compute_row_index("line1\nline2\n")
        assert result == [0, 6, 12], "Trailing newline creates third line for EOF error reporting"

    def test_multiline_document(self):
        """
        Realistic LaTeX documents have multiple lines that need accurate tracking.
        Users expect error messages like 'Error in file.tex:2' to point to correct line.
        """
        content = "First line\nSecond line\nThird line"
        result = compute_row_index(content)
        assert result == [0, 11, 23], "Line starts should be at positions 0, 11, and 23"
        # Verify we can use this to extract lines for error messages
        assert content[result[0]:result[1]-1] == "First line", "Index should help extract line 1"
        assert content[result[1]:result[2]-1] == "Second line", "Index should help extract line 2"
        assert content[result[2]:] == "Third line", "Index should help extract line 3"

    def test_varying_line_lengths(self):
        """
        LaTeX documents have varying line lengths - index must handle all cases.
        Short lines, long lines, single-character lines all need accurate tracking.
        """
        content = "short\nthis is a longer line\nx\n"
        result = compute_row_index(content)
        assert result == [0, 6, 28, 30], "Lines of different lengths should be indexed correctly"
        assert len(result) == 4, "Should track all 4 lines (3 newlines + initial position)"

    def test_only_newlines(self):
        """
        Document with only newlines needs tracking for error reporting.
        Edge case: user might have blank template or generated content.
        """
        result = compute_row_index("\n\n\n")
        assert result == [0, 1, 2, 3], "Newline-only document should index each line"

    def test_latex_document(self):
        """
        Real LaTeX documents need accurate line tracking for error messages.
        Example: 'Undefined control sequence at main.tex:3' should point to correct line.
        """
        content = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        result = compute_row_index(content)
        assert result == [0, 24, 41, 47], "LaTeX document lines should be indexed for error reporting"
        # Verify we can extract LaTeX lines for error messages
        lines = []
        for i in range(len(result)):
            if i < len(result) - 1:
                lines.append(content[result[i]:result[i+1]-1])
            else:
                lines.append(content[result[i]:])
        assert lines[0] == "\\documentclass{article}", "Should extract LaTeX command from line 1"
        assert lines[1] == "\\begin{document}", "Should extract begin from line 2"
        assert lines[2] == "Hello", "Should extract content from line 3"
        assert lines[3] == "\\end{document}", "Should extract end from line 4"
