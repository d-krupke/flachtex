"""Cycle detection for LaTeX file inclusion."""

from __future__ import annotations


class CycleException(Exception):
    """Exception raised when a circular dependency is detected in file inclusions."""

    def __init__(self, path: str, origin: str | None) -> None:
        """
        Initialize the cycle exception.

        Args:
            path: The file path that created the cycle
            origin: The context/origin where the cycle was detected
        """
        super().__init__()
        self.path = path
        self.origin = origin

    def __str__(self) -> str:
        """Return a human-readable description of the cycle."""
        if self.origin:
            return f"CycleException importing {self.path} ({self.origin})."
        return f"CycleException importing {self.path}."


class CyclePrevention:
    """
    Track file inclusion paths to prevent circular dependencies.

    This class maintains a stack of currently-being-processed files and
    detects when a file is being included recursively.
    """

    def __init__(self) -> None:
        """Initialize an empty cycle prevention tracker."""
        self._checked_paths: list[str] = []

    def push(self, path: str, context: str | None = None) -> None:
        """
        Mark a file as currently being processed.

        Args:
            path: The file path being processed
            context: Optional context information for error messages

        Raises:
            CycleException: If the file is already being processed (circular dependency)
        """
        if path in self._checked_paths:
            raise CycleException(path, context)
        self._checked_paths.append(path)

    def pop(self) -> None:
        """Remove the most recently added file from the processing stack."""
        self._checked_paths.pop()
