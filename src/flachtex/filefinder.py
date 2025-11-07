"""File finding and reading functionality for LaTeX documents."""

from __future__ import annotations

import os.path
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol


class FileSystemProtocol(Protocol):
    """Protocol defining the interface for file system access."""

    def __contains__(self, item: str) -> bool:
        """Check if a file exists."""
        ...

    def __getitem__(self, item: str) -> str:
        """Read and return the contents of a file."""
        ...


class FileSystem:
    """
    File system wrapper for actual disk I/O.

    This class wraps file system access so it can be replaced with a simple
    dictionary for testing purposes.
    """

    def __contains__(self, path: str) -> bool:
        """
        Check if a file exists on the file system.

        Args:
            path: Path to check

        Returns:
            True if the path exists and is a file
        """
        return Path(path).is_file()

    def __getitem__(self, path: str) -> str:
        """
        Read and return the contents of a file.

        Args:
            path: Path to the file to read

        Returns:
            The file contents as a string

        Raises:
            FileNotFoundError: If the file does not exist
            OSError: If the file cannot be read
        """
        file_path = Path(path)
        if not file_path.is_file():
            msg = f"Could not find '{path}'"
            raise FileNotFoundError(msg)
        try:
            return file_path.read_text(errors="ignore")
        except Exception as exc:
            msg = f"Error reading '{path}': {exc!s}"
            raise OSError(msg) from exc


class FileFinder:
    """
    Find and read LaTeX files with intelligent path resolution.

    This class handles file path resolution for LaTeX documents, searching in multiple
    locations and handling both absolute and relative paths. It supports custom include
    directories and automatic .tex extension addition.
    """

    def __init__(
        self,
        project_root: str = ".",
        file_system: FileSystemProtocol | dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the file finder.

        Args:
            project_root: The root directory of the project (relative to cwd)
            file_system: A file system implementation or dictionary for testing.
                        If None, uses the real file system.
        """
        if file_system is None:
            file_system = FileSystem()
        self.file_system: FileSystemProtocol | dict[str, str] = file_system
        self._PATH = [project_root]
        self._project_root = project_root

    def set_root(self, project_root: str) -> None:
        """
        Set a new project root directory.

        Args:
            project_root: The new root directory path
        """
        self._PATH = [project_root]

    def find_best_matching_path(self, path: str, origin: str) -> str:
        """
        Find the best matching file path from multiple search locations.

        Searches for the file in multiple locations with various strategies:
        1. As an absolute path
        2. Relative to the origin file's directory
        3. In include directories
        4. Walking up from the origin directory

        Args:
            path: The path to resolve
            origin: The path of the file requesting this include

        Returns:
            The resolved absolute path to the file

        Raises:
            KeyError: If no matching file is found in any location
        """
        for p in self.get_checked_paths(path, origin):
            if p in self.file_system:
                return p
        checked = list(self.get_checked_paths(path, origin))
        msg = f"Not matching file found. Tried: {', '.join(checked)}"
        raise KeyError(msg)

    def _normalize(self, path: str) -> str:
        """Normalize a file path."""
        return os.path.normpath(path)

    def get_checked_paths(self, path: str, origin: str) -> Iterable[str]:
        """
        Get all possible file paths that will be checked.

        This method yields paths in order of priority, including variations
        with and without the .tex extension. It walks up the directory tree
        from the origin file, stopping when it reaches the project root or
        the filesystem root.

        Args:
            path: The requested file path
            origin: The path of the file making the request

        Yields:
            Possible file paths to check, in priority order
        """
        # If it is an absolute path, try this one first
        if os.path.isabs(path):
            yield os.path.normpath(path)
            yield os.path.normpath(path) + ".tex"

        # Try relative to the origin file's directory
        d = os.path.dirname(origin)
        yield self._normalize(os.path.join(d, path))
        yield self._normalize(os.path.join(d, path)) + ".tex"

        # Try include directories
        for include in self._PATH:
            yield self._normalize(os.path.join(include, path))
            yield self._normalize(os.path.join(include, path)) + ".tex"

        # Walk upwards from the origin file directory
        while d != self._project_root:
            yield self._normalize(os.path.join(d, path))
            yield self._normalize(os.path.join(d, path)) + ".tex"

            # Check if we've reached the filesystem root to prevent infinite loop
            # os.path.dirname("/") returns "/", so we need to detect this
            d_ = os.path.dirname(d)
            if d_ == d:
                break
            d = d_  # go one directory above

    def read(self, path: str) -> str:
        """
        Read and return the contents of a file.

        Args:
            path: Path to the file to read

        Returns:
            The file contents as a string
        """
        return self.file_system[self._normalize(path)]
