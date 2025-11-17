"""LaTeX document preprocessing and flattening."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from .cycle_prevention import CyclePrevention
from .filefinder import FileFinder
from .rules import (
    BASIC_INCLUDE_RULES,
    BASIC_SKIP_RULES,
    Import,
    ImportRule,
    SkipRule,
    SubimportSubstitutionRule,
    SubstitutionRule,
    apply_skip_rules,
    apply_subimport_substitution_rules,
    apply_substitution_rules,
    find_imports,
)
from .traceable_string import TraceableString


class Preprocessor:
    """
    Main preprocessor for LaTeX document flattening.

    This class handles the complete preprocessing pipeline:
    1. Reading files
    2. Applying skip rules (removing marked sections)
    3. Applying substitution rules (transforming commands)
    4. Finding and resolving imports
    5. Recursively flattening included files
    6. Handling subimport path adjustments
    """

    def __init__(self, project_root: Path | str) -> None:
        """
        Initialize the preprocessor.

        Args:
            project_root: The root directory of the LaTeX project, used for
                         resolving relative paths in include statements
        """
        self.skip_rules: list[SkipRule] = list(BASIC_SKIP_RULES)
        self.subimport_rules: list[SubimportSubstitutionRule] = []
        self.substitution_rules: list[SubstitutionRule] = []
        self.import_rules: list[ImportRule] = list(BASIC_INCLUDE_RULES)
        self.file_finder = FileFinder(project_root)
        self.structure: dict[str, dict[str, Any]] = {}

    def _extract_raw_blocks(
        self, content: TraceableString
    ) -> tuple[TraceableString, dict[str, TraceableString]]:
        """
        Extract RAW blocks and replace with placeholders.

        RAW blocks are marked with:
        %%FLACHTEX-RAW-START
        ...content...
        %%FLACHTEX-RAW-STOP

        These blocks should be completely excluded from preprocessing.

        Args:
            content: The content to extract RAW blocks from

        Returns:
            Tuple of (content with placeholders, mapping of placeholder to raw content)

        Raises:
            ValueError: If RAW blocks are unclosed, nested, or contain imports
        """
        raw_blocks: dict[str, TraceableString] = {}
        content_str = str(content)

        # Check for unclosed RAW blocks
        start_count = content_str.count("%%FLACHTEX-RAW-START")
        stop_count = content_str.count("%%FLACHTEX-RAW-STOP")
        if start_count != stop_count:
            if start_count > stop_count:
                msg = f"Unclosed RAW block: {start_count} START markers but only {stop_count} STOP markers"
            else:
                msg = f"RAW-STOP without RAW-START: {stop_count} STOP markers but only {start_count} START markers"
            raise ValueError(msg)

        # Pattern to match RAW blocks (non-greedy to avoid matching across multiple blocks)
        pattern = r"%%FLACHTEX-RAW-START\n(.*?)%%FLACHTEX-RAW-STOP"
        matches = list(re.finditer(pattern, content_str, re.DOTALL))

        # Check for nested RAW blocks
        for i, match in enumerate(matches):
            block_content = match.group(1)
            if "%%FLACHTEX-RAW-START" in block_content:
                msg = "Nested RAW blocks are not allowed"
                raise ValueError(msg)

            # Check for imports inside RAW blocks
            import_patterns = [
                r"\\input\{",
                r"\\include\{",
                r"\\subimport\{",
                r"\\subfile\{",
            ]
            for import_pattern in import_patterns:
                if re.search(import_pattern, block_content):
                    msg = f"Import commands not allowed in RAW blocks: found {import_pattern}"
                    raise ValueError(msg)

        # Extract RAW blocks and replace with placeholders
        # Work backwards to maintain correct positions
        result = content
        for match in reversed(matches):
            # Extract the content inside RAW markers (group 1)
            raw_content = content[match.start(1) : match.end(1)]

            # Generate a unique placeholder
            placeholder = f"%%FLACHTEX-RAW-PLACEHOLDER-{uuid.uuid4()}%%"
            raw_blocks[placeholder] = raw_content

            # Replace the entire RAW block (including markers) with the placeholder
            result = (
                result[: match.start()]
                + TraceableString(placeholder, origin="preprocessor")
                + result[match.end() :]
            )

        return result, raw_blocks

    def _restore_raw_blocks(
        self, content: TraceableString, raw_blocks: dict[str, TraceableString]
    ) -> TraceableString:
        """
        Restore RAW blocks from placeholders.

        Args:
            content: The content with placeholders
            raw_blocks: Mapping of placeholder to raw content

        Returns:
            Content with RAW blocks restored (including markers)
        """
        result = content
        for placeholder, raw_content in raw_blocks.items():
            # Replace placeholder with original content (with markers)
            original_block = (
                TraceableString("%%FLACHTEX-RAW-START\n", origin="preprocessor")
                + raw_content
                + TraceableString("%%FLACHTEX-RAW-STOP", origin="preprocessor")
            )

            # Find the placeholder position
            content_str = str(result)
            placeholder_pos = content_str.find(placeholder)
            if placeholder_pos != -1:
                # Replace using slicing
                result = (
                    result[:placeholder_pos]
                    + original_block
                    + result[placeholder_pos + len(placeholder) :]
                )

        return result

    def read_file(self, file_path: Path | str) -> TraceableString:
        """
        Read a file and apply skip and substitution rules.

        RAW blocks (%%FLACHTEX-RAW-START/STOP) are extracted before processing
        and restored after, so they are completely excluded from preprocessing.

        Args:
            file_path: Path to the file to read

        Returns:
            The file content after applying preprocessing rules

        Raises:
            ValueError: If RAW blocks are malformed or contain imports
        """
        content = TraceableString(self.file_finder.read(file_path), origin=file_path)

        # Extract RAW blocks before preprocessing
        content, raw_blocks = self._extract_raw_blocks(content)

        # Apply normal preprocessing (skip rules, substitution)
        content = apply_skip_rules(content, self.skip_rules)
        content = apply_substitution_rules(content, self.substitution_rules)

        # Restore RAW blocks after preprocessing
        content = self._restore_raw_blocks(content, raw_blocks)

        return content

    def include_path(
        self, content: TraceableString, subimport_path: str | None
    ) -> TraceableString:
        """
        Apply subimport path transformations to content.

        When using \\subimport, relative paths need to be adjusted to include
        the subimport directory prefix.

        Args:
            content: The content to transform
            subimport_path: The subimport directory path, or None

        Returns:
            The content with paths adjusted for subimport context
        """
        if subimport_path is None or subimport_path == "":
            return content
        return apply_subimport_substitution_rules(
            content, self.subimport_rules, subimport_path
        )

    def find_imports(self, content: TraceableString) -> list[Import]:
        """
        Find all import commands in the file content.

        Uses the configured import rules to detect \\input, \\include,
        \\subimport, and other import commands.

        Args:
            content: The content to search for imports

        Returns:
            List of all found imports
        """
        return find_imports(content, self.import_rules)

    def _add_structure(self, path: str, included_files: list[str]) -> None:
        """
        Record the file structure for later analysis.

        Args:
            path: The file path
            included_files: List of files included by this file
        """
        self.structure[path] = {
            "content": self.file_finder.read(path),
            "includes": included_files,
        }

    def expand_file(
        self,
        file_path: Path | str,
        _cycle_prevention: CyclePrevention | None = None,
        is_subimport: bool = False,
        subimport_path: str | None = None,
    ) -> TraceableString:
        """
        Recursively expand and flatten a LaTeX file.

        This method:
        1. Reads the file and applies preprocessing rules
        2. Finds all import commands
        3. Recursively expands each imported file
        4. Replaces import commands with their expanded content
        5. Applies subimport path adjustments if needed

        Args:
            file_path: Path to the file to expand
            _cycle_prevention: Internal cycle detection tracker
            is_subimport: Whether this file was included via \\subimport
            subimport_path: The subimport directory path, if applicable

        Returns:
            The fully flattened content with all includes resolved

        Raises:
            CycleException: If a circular include dependency is detected
            KeyError: If an included file cannot be found
        """
        if _cycle_prevention is None:
            _cycle_prevention = CyclePrevention()

        file_path_str = str(file_path)
        offset = 0
        _cycle_prevention.push(file_path_str, context=file_path_str)
        content = self.read_file(file_path_str)
        imports = self.find_imports(content)
        self._add_structure(file_path_str, [import_.path for import_ in imports])

        # Replace each import with its expanded content
        for match in imports:
            try:
                insertion_file = self.file_finder.find_best_matching_path(
                    match.path, origin=file_path_str
                )
                insertion = self.expand_file(
                    insertion_file,
                    _cycle_prevention,
                    match.is_subimport,
                    match.subimport_path,
                )
                content = (
                    content[: match.start + offset]
                    + insertion
                    + content[match.end + offset :]
                )
                offset += len(insertion) - len(match)
            except KeyError:
                pass  # Allow non-existent includes to be skipped

        # Apply subimport path adjustments if this was a subimport
        if is_subimport:
            if not subimport_path:
                msg = "Subimport path must be provided for subimports."
                raise ValueError(msg)
            content = self.include_path(content, subimport_path)

        _cycle_prevention.pop()
        return content
