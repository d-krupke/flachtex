"""Utility classes and functions for flachtex."""

from __future__ import annotations


class Range:
    """
    A simple range representing a span within text.

    This class represents a continuous span of text from start to end position.
    It provides methods for intersection checking and comparison operations.
    """

    def __init__(self, start: int, end: int) -> None:
        """
        Initialize a text range.

        Args:
            start: The starting position (inclusive)
            end: The ending position (exclusive)
        """
        self.start = start
        self.end = end

    def intersects(self, other: Range) -> bool:
        """
        Check if this range intersects with another range.

        Two ranges intersect if they have any overlapping positions.

        Args:
            other: The range to check for intersection

        Returns:
            True if the ranges intersect, False otherwise
        """
        # Check if one range's start lies within the other
        if self.start <= other.start < self.end:
            return True
        return bool(
            other.start <= self.start < self.end and not other.end <= self.start
        )

    def __le__(self, other: Range) -> bool:
        """Compare ranges by their start position (less than or equal)."""
        return self.start <= other.start

    def __lt__(self, other: Range) -> bool:
        """Compare ranges by their start position (less than)."""
        return self.start < other.start

    def __len__(self) -> int:
        """Return the length of the range."""
        return self.end - self.start

    def __repr__(self) -> str:
        """Return a string representation of the range."""
        return f"[{self.start}:{self.end}]"


def compute_row_index(content: str) -> list[int]:
    """
    Compute the starting position of each line in the text.

    Creates an index where index[i] gives the starting position of line i
    in the content string.

    Args:
        content: The text content to index

    Returns:
        A list where each element is the starting position of that line number

    Example:
        >>> compute_row_index("a\\nb\\nc")
        [0, 2, 4]
    """
    index = [0]
    i = content.find("\n")
    while i >= 0:
        index.append(i + 1)
        i = content.find("\n", i + 1)
    return index
