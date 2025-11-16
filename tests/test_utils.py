"""Tests for utility classes and functions."""

import pytest

from flachtex.utils import Range, compute_row_index


class TestRange:
    """Test the Range class."""

    def test_basic_construction(self):
        """Test basic range construction."""
        r = Range(0, 10)
        assert r.start == 0
        assert r.end == 10

    def test_length(self):
        """Test range length calculation."""
        r = Range(5, 15)
        assert len(r) == 10

    def test_length_zero(self):
        """Test zero-length range."""
        r = Range(5, 5)
        assert len(r) == 0

    def test_repr(self):
        """Test string representation."""
        r = Range(10, 20)
        assert repr(r) == "[10:20]"

    def test_intersects_overlapping(self):
        """Test intersection detection for overlapping ranges."""
        r1 = Range(0, 10)
        r2 = Range(5, 15)
        assert r1.intersects(r2)
        assert r2.intersects(r1)

    def test_intersects_contained(self):
        """Test intersection when one range is fully contained in another."""
        r1 = Range(0, 20)
        r2 = Range(5, 15)
        assert r1.intersects(r2)
        assert r2.intersects(r1)

    def test_intersects_adjacent_no_overlap(self):
        """Test that adjacent ranges don't intersect."""
        r1 = Range(0, 10)
        r2 = Range(10, 20)
        assert not r1.intersects(r2)
        assert not r2.intersects(r1)

    def test_intersects_separate(self):
        """Test that separate ranges don't intersect."""
        r1 = Range(0, 10)
        r2 = Range(20, 30)
        assert not r1.intersects(r2)
        assert not r2.intersects(r1)

    def test_intersects_touching_at_start(self):
        """Test ranges that touch at the start boundary."""
        r1 = Range(10, 20)
        r2 = Range(5, 10)
        assert not r1.intersects(r2)
        assert not r2.intersects(r1)

    def test_intersects_single_point_overlap(self):
        """Test ranges with single point overlap."""
        r1 = Range(0, 11)
        r2 = Range(10, 20)
        assert r1.intersects(r2)
        assert r2.intersects(r1)

    def test_intersects_same_range(self):
        """Test that a range intersects with itself."""
        r = Range(5, 15)
        assert r.intersects(r)

    def test_less_than(self):
        """Test less than comparison."""
        r1 = Range(0, 10)
        r2 = Range(5, 15)
        r3 = Range(10, 20)
        assert r1 < r2
        assert r1 < r3
        assert r2 < r3
        assert not r2 < r1
        assert not r3 < r1

    def test_less_than_equal(self):
        """Test less than or equal comparison."""
        r1 = Range(0, 10)
        r2 = Range(0, 20)
        r3 = Range(5, 15)
        assert r1 <= r2
        assert r1 <= r3
        assert r2 <= r2  # Same start, should be equal
        assert not r3 <= r1

    def test_sorting(self):
        """Test that ranges can be sorted by start position."""
        ranges = [Range(10, 20), Range(0, 5), Range(5, 15), Range(0, 10)]
        sorted_ranges = sorted(ranges)
        assert sorted_ranges[0].start == 0
        assert sorted_ranges[1].start == 0
        assert sorted_ranges[2].start == 5
        assert sorted_ranges[3].start == 10


class TestComputeRowIndex:
    """Test the compute_row_index function."""

    def test_empty_string(self):
        """Test with empty string."""
        result = compute_row_index("")
        assert result == [0]

    def test_single_line(self):
        """Test with single line (no newlines)."""
        result = compute_row_index("hello world")
        assert result == [0]

    def test_two_lines(self):
        """Test with two lines."""
        result = compute_row_index("line1\nline2")
        assert result == [0, 6]

    def test_three_lines(self):
        """Test with three lines."""
        result = compute_row_index("a\nb\nc")
        assert result == [0, 2, 4]

    def test_empty_lines(self):
        """Test with empty lines."""
        result = compute_row_index("\n\n")
        assert result == [0, 1, 2]

    def test_trailing_newline(self):
        """Test with trailing newline."""
        result = compute_row_index("line1\nline2\n")
        assert result == [0, 6, 12]

    def test_multiline_document(self):
        """Test with realistic multiline document."""
        content = "First line\nSecond line\nThird line"
        result = compute_row_index(content)
        assert result == [0, 11, 23]
        # Verify we can use this to find line starts
        assert content[result[0]:result[1]-1] == "First line"
        assert content[result[1]:result[2]-1] == "Second line"
        assert content[result[2]:] == "Third line"

    def test_varying_line_lengths(self):
        """Test with varying line lengths."""
        content = "short\nthis is a longer line\nx\n"
        result = compute_row_index(content)
        assert result == [0, 6, 28, 30]
        assert len(result) == 4  # 3 newlines + initial position

    def test_only_newlines(self):
        """Test with only newlines."""
        result = compute_row_index("\n\n\n")
        assert result == [0, 1, 2, 3]

    def test_latex_document(self):
        """Test with LaTeX-like content."""
        content = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"
        result = compute_row_index(content)
        assert result == [0, 24, 41, 47]
        # Verify line extraction
        lines = []
        for i in range(len(result)):
            if i < len(result) - 1:
                lines.append(content[result[i]:result[i+1]-1])
            else:
                lines.append(content[result[i]:])
        assert lines[0] == "\\documentclass{article}"
        assert lines[1] == "\\begin{document}"
        assert lines[2] == "Hello"
        assert lines[3] == "\\end{document}"
