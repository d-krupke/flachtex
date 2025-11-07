"""
Traceable string implementation with origin tracking.

This module provides TraceableString, a string wrapper that maintains
information about where each character originated from in the source files.
This is crucial for error reporting and source tracing during LaTeX flattening.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .utils import compute_row_index


@dataclass(frozen=True, slots=True)
class OriginOfRange:
    """
    Immutable range representing the origin of a substring.

    Tracks a contiguous substring's source file, position, and offset.
    Immutability ensures thread-safety and prevents accidental mutations.

    Attributes:
        begin: Start position in the current string (inclusive)
        end: End position in the current string (exclusive)
        origin: Source file or identifier where this text came from
        offset: Offset into the original source file
    """

    begin: int
    end: int
    origin: str | None
    offset: int = 0

    def __len__(self) -> int:
        """Return the length of this range."""
        return self.end - self.begin

    def __contains__(self, item: int) -> bool:
        """Check if an index is within this range."""
        return self.begin <= item < self.end

    def __lt__(self, other: OriginOfRange) -> bool:
        """Compare ranges by start position."""
        return self.begin < other.begin

    def cut_front(self, n: int) -> OriginOfRange | None:
        """
        Remove indices < n from the front of this range.

        Args:
            n: New first position (indices before this are cut)

        Returns:
            New OriginOfRange adjusted for the cut, or None if entirely removed

        Example:
            >>> origin = OriginOfRange(5, 10, "file.tex", 0)
            >>> origin.cut_front(7)
            OriginOfRange(begin=0, end=3, origin='file.tex', offset=2)
        """
        if self.end <= n:
            return None
        if self.begin <= n < self.end:
            new_offset = self.offset + (n - self.begin)
        else:
            new_offset = self.offset
        return OriginOfRange(
            max(0, self.begin - n), self.end - n, self.origin, new_offset
        )

    def cut_back(self, n: int) -> OriginOfRange | None:
        """
        Remove indices >= n from the back of this range.

        Args:
            n: New end index (indices from here onwards are cut)

        Returns:
            New OriginOfRange adjusted for the cut, or None if entirely removed

        Example:
            >>> origin = OriginOfRange(5, 10, "file.tex", 0)
            >>> origin.cut_back(8)
            OriginOfRange(begin=5, end=8, origin='file.tex', offset=0)
        """
        if self.begin >= n:
            return None
        return OriginOfRange(self.begin, min(self.end, n), self.origin, self.offset)

    def slice(self, begin: int, end: int) -> OriginOfRange | None:
        """
        Extract a slice of this range.

        Args:
            begin: Start of the slice
            end: End of the slice

        Returns:
            New OriginOfRange for the slice, or None if no overlap
        """
        # Cut back first to avoid changing indices
        shortened = self.cut_back(end)
        if shortened:
            return shortened.cut_front(begin)
        return None

    def move(self, n: int) -> OriginOfRange:
        """
        Shift this range by n positions.

        Args:
            n: Number of positions to shift (can be negative)

        Returns:
            New OriginOfRange shifted by n positions
        """
        return OriginOfRange(self.begin + n, self.end + n, self.origin, self.offset)

    def get_offset(self, i: int) -> int:
        """
        Get the offset in the original source for a position.

        Args:
            i: Position in the current string

        Returns:
            Offset in the original source file

        Raises:
            ValueError: If i is not within this range
        """
        if i not in self:
            msg = f"Index {i} is not within range [{self.begin}:{self.end}]"
            raise ValueError(msg)
        return self.offset + (i - self.begin)

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return f"{self.origin}[{self.begin}:{self.end}:+{self.offset}]"


class TraceableString:
    """
    String wrapper that tracks the origin of each character.

    This class maintains a string along with origin information for every
    character, enabling precise error reporting and source tracing during
    LaTeX document flattening.

    The class supports string-like operations (slicing, concatenation) while
    preserving origin information. Line index is computed lazily for performance.

    Attributes:
        content: The actual string content
        origins: List of OriginOfRange objects tracking source locations
    """

    __slots__ = ("content", "origins", "_line_index")

    def __init__(self, content: str, origin: str | None, offset: int = 0) -> None:
        """
        Initialize a traceable string.

        Args:
            content: The string content
            origin: Source identifier (usually a file path)
            offset: Starting offset in the source file
        """
        self.content = content
        self.origins: list[OriginOfRange] = [
            OriginOfRange(0, len(content), origin, offset)
        ]
        self._line_index: list[int] | None = None

    def __len__(self) -> int:
        """Return the length of the string."""
        return len(self.content)

    def __str__(self) -> str:
        """Return the string content."""
        return self.content

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"TraceableString({self.content!r}, origins={self.origins})"

    def _normalize_slice(self, s: slice) -> tuple[int, int]:
        """
        Normalize a slice to absolute start/stop positions.

        Args:
            s: The slice object

        Returns:
            Tuple of (start, stop) as absolute positions

        Raises:
            IndexError: If stop is beyond string length
            NotImplementedError: If step is not 1 or None
        """
        start = s.start if s.start is not None else 0
        start = start if start >= 0 else len(self) + start
        stop = s.stop if s.stop is not None else len(self)
        stop = stop if stop >= 0 else len(self) + stop

        if stop > len(self):
            msg = f"Slice stop {stop} exceeds length {len(self)}"
            raise IndexError(msg)

        if s.step is not None and s.step != 1:
            msg = "Slicing with steps is not supported"
            raise NotImplementedError(msg)

        return start, stop

    def __getitem__(self, item: int | slice) -> str | TraceableString:
        """
        Get a character or substring with origin tracking.

        Args:
            item: Index or slice

        Returns:
            Single character (str) for index, TraceableString for slice

        Example:
            >>> ts = TraceableString("hello", "file.tex")
            >>> ts[0]
            'h'
            >>> str(ts[1:4])
            'ell'
        """
        if isinstance(item, slice):
            content = self.content[item]
            start, stop = self._normalize_slice(item)

            # Slice origins and filter out None results
            origins = (o.slice(start, stop) for o in self.origins)
            valid_origins = [o for o in origins if o is not None]

            ts = TraceableString.__new__(TraceableString)
            ts.content = content
            ts.origins = valid_origins
            ts._line_index = None
            return ts

        return self.content[item]

    def get_origin(self, i: int) -> tuple[str | None, int] | None:
        """
        Get the origin information for a character position.

        Args:
            i: Index in the string

        Returns:
            Tuple of (origin, offset) or None if no origin found

        Raises:
            IndexError: If i is beyond string length
        """
        if i >= len(self):
            msg = f"Index {i} exceeds length {len(self)}"
            raise IndexError(msg)

        for o in self.origins:
            if i in o:
                return o.origin, o.get_offset(i)
        return None

    def _populate_line_index(self) -> None:
        """Lazily compute the line index for line-based operations."""
        self._line_index = compute_row_index(self.content)

    def get_origin_of_line(self, line: int, col: int = 0) -> tuple[str | None, int] | None:
        """
        Get origin information for a specific line and column.

        Args:
            line: Line number (0-indexed)
            col: Column number (0-indexed, default 0)

        Returns:
            Tuple of (origin, offset) or None

        Example:
            >>> ts = TraceableString("line1\\nline2\\n", "file.tex")
            >>> ts.get_origin_of_line(1)  # Second line
            ('file.tex', 6)
        """
        if self._line_index is None:
            self._populate_line_index()
        assert self._line_index is not None  # For type checker

        i = self._line_index[line] + col
        return self.get_origin(i)

    def to_json(self) -> dict[str, Any]:
        """
        Serialize to JSON-compatible dictionary.

        Returns:
            Dictionary with 'content' and 'origins' keys

        Example:
            >>> ts = TraceableString("text", "file.tex")
            >>> ts.to_json()
            {'content': 'text', 'origins': [{'begin': 0, 'end': 4, ...}]}
        """
        return {
            "content": self.content,
            "origins": [
                {
                    "begin": o.begin,
                    "end": o.end,
                    "origin": str(o.origin) if o.origin else None,
                    "offset": o.offset,
                }
                for o in self.origins
            ],
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> TraceableString:
        """
        Deserialize from JSON-compatible dictionary.

        Args:
            data: Dictionary with 'content' and 'origins' keys

        Returns:
            Reconstructed TraceableString

        Raises:
            ValueError: If data is invalid or missing required fields

        Example:
            >>> data = {'content': 'text', 'origins': [...]}
            >>> ts = TraceableString.from_json(data)
        """
        try:
            if not isinstance(data.get("content"), str):
                msg = "Missing or invalid 'content' field"
                raise ValueError(msg)

            if not isinstance(data.get("origins"), list):
                msg = "Missing or invalid 'origins' field"
                raise ValueError(msg)

            ts = TraceableString.__new__(TraceableString)
            ts.content = data["content"]
            ts.origins = [
                OriginOfRange(
                    begin=int(o["begin"]),
                    end=int(o["end"]),
                    origin=o.get("origin"),
                    offset=int(o.get("offset", 0)),
                )
                for o in data["origins"]
            ]
            ts._line_index = None
            return ts

        except (KeyError, TypeError, ValueError) as e:
            msg = f"Invalid TracingString JSON data: {e}"
            raise ValueError(msg) from e

    def __add__(self, other: TraceableString) -> TraceableString:
        """
        Concatenate two traceable strings.

        Args:
            other: The TraceableString to append

        Returns:
            New TraceableString with combined content and adjusted origins

        Example:
            >>> ts1 = TraceableString("hello ", "file1.tex")
            >>> ts2 = TraceableString("world", "file2.tex")
            >>> combined = ts1 + ts2
            >>> str(combined)
            'hello world'
        """
        ts = TraceableString.__new__(TraceableString)
        ts.content = self.content + other.content
        ts.origins = self.origins + [o.move(len(self)) for o in other.origins]
        ts._line_index = None
        return ts

    def __eq__(self, other: object) -> bool:
        """
        Check equality based on content and origins.

        Args:
            other: Object to compare with

        Returns:
            True if content and origins match
        """
        if not isinstance(other, TraceableString):
            return False
        return self.content == other.content and self.origins == other.origins

    def __hash__(self) -> int:
        """
        Compute hash based on content and origins.

        This allows TraceableString to be used in sets and as dict keys,
        but only if origins are hashable (which they are with frozen dataclass).

        Returns:
            Hash value
        """
        return hash((self.content, tuple(self.origins)))
