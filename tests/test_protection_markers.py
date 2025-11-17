"""Tests for protection markers: RAW and NO-FORMAT.

Protection markers give users explicit control over which parts of their
documents are processed by flachtex. This is critical for:

1. RAW markers: Escape hatch when flachtex misinterprets complex LaTeX
2. NO-FORMAT markers: Preserve pre-formatted content (tables, algorithms)

Why users need protection markers:
- LaTeX is complex; flachtex WILL encounter edge cases it can't handle
- Users need immediate workarounds without filing bug reports
- Pre-formatted content (tables, pseudocode) should stay as-is
- Better to let users exclude problem regions than produce broken output
"""

import pytest

from flachtex import FileFinder, Preprocessor, TraceableString
from flachtex.formatter import format_latex
from flachtex.rules import BasicSkipRule, apply_skip_rules


class TestRawMarkers:
    """
    Test %%FLACHTEX-RAW-START/STOP markers for complete passthrough.

    RAW markers are the emergency escape hatch when flachtex breaks on complex
    LaTeX. Users wrap problematic sections in RAW markers to bypass ALL
    flachtex processing: skip rules, substitution, AND formatting.

    Why users need this:
    - Complex \\newcommand definitions that break substitution
    - Unusual package syntax that confuses comment detection
    - Nested environments that break indentation tracking
    - Any LaTeX construct flachtex misinterprets

    Expected behavior:
    - Content inside RAW markers appears in output unchanged
    - Skip rules do NOT apply to RAW content
    - Substitution rules do NOT apply to RAW content
    - Formatting does NOT apply to RAW content
    """

    def test_raw_markers_basic_passthrough(self):
        """
        Test that content inside RAW markers passes through unchanged.

        Users need this as an escape hatch: when flachtex breaks, wrap the
        problematic section in RAW markers and it gets included as-is.
        """
        document = {
            "main.tex": (
                "Normal text.\n"
                "%%FLACHTEX-RAW-START\n"
                "Complex LaTeX that flachtex might misinterpret.\n"
                "\\newcommand{\\problematic}{...}\n"
                "%%FLACHTEX-RAW-STOP\n"
                "More normal text."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Normal text." in result_str, "Content outside RAW blocks must be processed normally"
        assert "Complex LaTeX that flachtex might misinterpret." in result_str, "RAW block content must appear in output"
        assert "\\newcommand{\\problematic}{...}" in result_str, "RAW content must pass through unchanged"
        assert "More normal text." in result_str, "Content after RAW blocks must be processed"

    def test_raw_blocks_skip_preprocessing(self):
        """
        Test that skip rules do NOT apply inside RAW blocks.

        If user has wrapped content in RAW (to work around flachtex bug),
        skip rules inside that content should be ignored - RAW means
        "don't touch anything".
        """
        document = {
            "main.tex": (
                "Normal content.\n"
                "%%FLACHTEX-EXCLUDE-START\n"
                "This will be skipped.\n"
                "%%FLACHTEX-EXCLUDE-STOP\n"
                "%%FLACHTEX-RAW-START\n"
                "%%FLACHTEX-EXCLUDE-START\n"
                "This should NOT be skipped (inside RAW).\n"
                "%%FLACHTEX-EXCLUDE-STOP\n"
                "%%FLACHTEX-RAW-STOP\n"
                "End content."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Normal content." in result_str, "Normal content must be processed"
        assert "This will be skipped." not in result_str, "Skip blocks outside RAW must be removed"
        assert "This should NOT be skipped (inside RAW)." in result_str, "Skip markers inside RAW must be ignored"
        assert "%%FLACHTEX-EXCLUDE-START" in result_str, "Skip markers inside RAW must appear in output"
        assert "End content." in result_str, "Content after RAW must be processed"

    def test_raw_blocks_skip_substitution(self):
        """
        Test that command substitution does NOT apply inside RAW blocks.

        RAW content should bypass all preprocessing, including custom
        command substitution that might break complex LaTeX.
        """
        from flachtex.command_substitution import (
            NewCommandDefinition,
            NewCommandSubstitution,
        )

        document = {
            "main.tex": (
                "\\newcommand{\\test}{REPLACED}\n"
                "Normal: \\test\n"
                "%%FLACHTEX-RAW-START\n"
                "Raw: \\test\n"
                "%%FLACHTEX-RAW-STOP\n"
                "After: \\test"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        # Add command substitution
        ncs = NewCommandSubstitution()
        ncs.new_command(
            NewCommandDefinition(
                TraceableString("test", None), 0, TraceableString("REPLACED", None)
            )
        )
        preprocessor.substitution_rules.append(ncs)

        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Normal: REPLACED" in result_str, "Commands outside RAW must be substituted"
        assert "Raw: \\test" in result_str, "Commands inside RAW must NOT be substituted"
        assert "After: REPLACED" in result_str, "Commands after RAW must be substituted"

    def test_raw_blocks_skip_formatting(self):
        """
        Test that formatting does NOT apply inside RAW blocks.

        Even if user calls format_latex(), RAW blocks should be protected
        from all formatting (sentence splitting, indentation).
        """
        content = TraceableString(
            "Normal sentence. Another sentence.\n"
            "%%FLACHTEX-RAW-START\n"
            "Sentence one. Sentence two. Sentence three.\n"
            "%%FLACHTEX-RAW-STOP\n"
            "Final sentence. Last sentence.",
            "test.tex"
        )

        # Format with sentence-per-line
        result = format_latex(content)
        result_str = str(result)

        # Normal sentences should be split
        assert "Normal sentence.\n" in result_str, "Sentences outside RAW must be split"
        assert "Another sentence.\n" in result_str

        # RAW content should NOT be split
        assert "Sentence one. Sentence two. Sentence three." in result_str, "Sentences inside RAW must NOT be split"

        # Sentences after RAW should be split
        assert "Final sentence.\n" in result_str, "Sentences after RAW must be split"

    def test_multiple_raw_blocks(self):
        """
        Test multiple independent RAW blocks in one document.

        Users may have several problematic sections that need protection.
        All RAW blocks must be handled correctly.
        """
        document = {
            "main.tex": (
                "Text 1.\n"
                "%%FLACHTEX-RAW-START\n"
                "Raw block 1.\n"
                "%%FLACHTEX-RAW-STOP\n"
                "Text 2.\n"
                "%%FLACHTEX-RAW-START\n"
                "Raw block 2.\n"
                "%%FLACHTEX-RAW-STOP\n"
                "Text 3."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Raw block 1." in result_str, "First RAW block must be preserved"
        assert "Raw block 2." in result_str, "Second RAW block must be preserved"
        assert "Text 1." in result_str and "Text 2." in result_str and "Text 3." in result_str, "All non-RAW content must be processed"

    def test_raw_blocks_in_included_files(self):
        """
        Test RAW blocks work correctly in included files.

        Users may put RAW blocks in any file, not just main.tex.
        RAW protection must work for included files too.
        """
        document = {
            "main.tex": "\\input{section.tex}",
            "section.tex": (
                "Normal content.\n"
                "%%FLACHTEX-RAW-START\n"
                "Protected content.\n"
                "%%FLACHTEX-RAW-STOP\n"
                "More content."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Protected content." in result_str, "RAW blocks in included files must be protected"
        assert "Normal content." in result_str, "Non-RAW content in included files must be processed"

    def test_raw_blocks_preserve_exact_content(self):
        """
        Test that RAW blocks preserve content exactly as written.

        This includes whitespace, newlines, special characters - everything
        must pass through unchanged.
        """
        document = {
            "main.tex": (
                "%%FLACHTEX-RAW-START\n"
                "  Indented line\n"
                "Line with    multiple   spaces\n"
                "Line with\ttabs\n"
                "\n"
                "Line after blank\n"
                "%%FLACHTEX-RAW-STOP"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "  Indented line" in result_str, "Indentation must be preserved"
        assert "multiple   spaces" in result_str, "Multiple spaces must be preserved"
        assert "\ttabs" in result_str or "	tabs" in result_str, "Tabs must be preserved"


class TestRawMarkersErrorCases:
    """
    Test error conditions for RAW markers.

    Proper error handling prevents silent bugs and gives users clear feedback
    about what went wrong.
    """

    def test_unclosed_raw_block_error(self):
        """
        Test that unclosed RAW block raises an error.

        Unclosed RAW would protect everything after START marker, silently
        breaking preprocessing. Better to fail loudly so user can fix.
        """
        document = {
            "main.tex": (
                "Content\n"
                "%%FLACHTEX-RAW-START\n"
                "Unclosed block"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        with pytest.raises(ValueError, match="Unclosed RAW block"):
            preprocessor.expand_file("main.tex")

    def test_raw_stop_without_start_error(self):
        """
        Test that RAW-STOP without RAW-START raises an error.

        Unmatched markers indicate a user error that should be caught.
        """
        document = {
            "main.tex": (
                "Content\n"
                "%%FLACHTEX-RAW-STOP\n"
                "More content"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        with pytest.raises(ValueError, match="RAW-STOP without RAW-START"):
            preprocessor.expand_file("main.tex")

    def test_nested_raw_blocks_error(self):
        """
        Test that nested RAW blocks raise an error.

        Nesting is ambiguous (which STOP matches which START?) and should
        be disallowed.
        """
        document = {
            "main.tex": (
                "%%FLACHTEX-RAW-START\n"
                "Outer\n"
                "%%FLACHTEX-RAW-START\n"
                "Inner\n"
                "%%FLACHTEX-RAW-STOP\n"
                "%%FLACHTEX-RAW-STOP"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        with pytest.raises(ValueError, match="Nested RAW blocks"):
            preprocessor.expand_file("main.tex")

    def test_raw_blocks_with_imports_error(self):
        """
        Test that imports inside RAW blocks raise an error.

        If RAW contains \\input{file.tex}, should flachtex include file.tex?
        This is ambiguous. Better to disallow imports in RAW blocks.
        """
        document = {
            "main.tex": (
                "%%FLACHTEX-RAW-START\n"
                "\\input{section.tex}\n"
                "%%FLACHTEX-RAW-STOP"
            ),
            "section.tex": "Content"
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        with pytest.raises(ValueError, match="Import commands not allowed in RAW blocks"):
            preprocessor.expand_file("main.tex")


class TestNoFormatMarkers:
    """
    Test %%FLACHTEX-NO-FORMAT-START/STOP markers.

    NO-FORMAT markers let users preserve pre-formatted content while still
    allowing preprocessing (skip rules, substitution). This is for:
    - Carefully formatted tables
    - Algorithm pseudocode with meaningful line breaks
    - Pre-formatted paragraphs for stylistic reasons

    Expected behavior:
    - Content inside NO-FORMAT appears in output
    - Skip rules DO apply (preprocessing happens)
    - Substitution rules DO apply (preprocessing happens)
    - Formatting does NOT apply (sentence splitting, indentation skipped)
    """

    def test_no_format_basic(self):
        """
        Test that NO-FORMAT blocks prevent formatting but allow preprocessing.

        This is different from RAW: preprocessing should still apply,
        but formatting should not.
        """
        document = {
            "main.tex": (
                "Normal sentence. Another sentence.\n"
                "%%FLACHTEX-NO-FORMAT-START\n"
                "Sentence one. Sentence two.\n"
                "%%FLACHTEX-NO-FORMAT-STOP\n"
                "Final sentence."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")

        # Format the result
        formatted = format_latex(result)
        formatted_str = str(formatted)

        # Normal sentences should be split
        assert "Normal sentence.\n" in formatted_str, "Sentences outside NO-FORMAT must be split"
        assert "Another sentence.\n" in formatted_str

        # NO-FORMAT content should NOT be split
        assert "Sentence one. Sentence two." in formatted_str, "Sentences inside NO-FORMAT must NOT be split"

        # Sentence after should be split
        assert "Final sentence." in formatted_str

    def test_no_format_preserves_table_formatting(self):
        """
        Test NO-FORMAT preserves carefully formatted tables.

        This is the primary use case: users have pre-formatted tables with
        specific spacing and alignment. Formatter must not touch them.
        """
        content = TraceableString(
            "Normal text.\n"
            "%%FLACHTEX-NO-FORMAT-START\n"
            "\\begin{tabular}{lll}\n"
            "Column1 & Column2 & Column3 \\\\\n"
            "A       & B       & C       \\\\\n"
            "\\end{tabular}\n"
            "%%FLACHTEX-NO-FORMAT-STOP\n"
            "More text.",
            "test.tex"
        )

        formatted = format_latex(content)
        formatted_str = str(formatted)

        # Table structure should be preserved exactly
        assert "Column1 & Column2 & Column3" in formatted_str, "Table header must be preserved"
        assert "A       & B       & C" in formatted_str, "Table alignment must be preserved"

    def test_no_format_allows_skip_rules(self):
        """
        Test that skip rules still work inside NO-FORMAT blocks.

        NO-FORMAT only protects from formatting, not preprocessing.
        Users may want to skip content inside NO-FORMAT regions.
        """
        content = TraceableString(
            "%%FLACHTEX-NO-FORMAT-START\n"
            "Keep this.\n"
            "%%FLACHTEX-EXCLUDE-START\n"
            "Remove this.\n"
            "%%FLACHTEX-EXCLUDE-STOP\n"
            "Keep this too.\n"
            "%%FLACHTEX-NO-FORMAT-STOP",
            "test.tex"
        )

        # Apply skip rules
        skipped = apply_skip_rules(content, [BasicSkipRule()])

        # Then format
        formatted = format_latex(skipped)
        formatted_str = str(formatted)

        assert "Keep this." in formatted_str, "Content outside skip blocks must be kept"
        assert "Remove this." not in formatted_str, "Skip blocks must be removed even inside NO-FORMAT"
        assert "Keep this too." in formatted_str

    def test_no_format_with_indentation_disabled(self):
        """
        Test that NO-FORMAT blocks don't get indented.

        Even if user requests indentation, NO-FORMAT blocks should stay as-is.
        """
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item Normal item.\n"
            "%%FLACHTEX-NO-FORMAT-START\n"
            "\\item Pre-formatted item.\n"
            "Already has specific spacing.\n"
            "%%FLACHTEX-NO-FORMAT-STOP\n"
            "\\item Another normal item.\n"
            "\\end{itemize}",
            "test.tex"
        )

        formatted = format_latex(content, indent=2)
        formatted_str = str(formatted)

        # Normal items should be indented
        assert "  \\item Normal item." in formatted_str, "Items outside NO-FORMAT must be indented"
        assert "  \\item Another normal item." in formatted_str

        # NO-FORMAT content should NOT be indented
        assert "\\item Pre-formatted item.\n" in formatted_str, "NO-FORMAT content must not be indented"
        assert "Already has specific spacing." in formatted_str

    def test_multiple_no_format_blocks(self):
        """Test multiple NO-FORMAT blocks work correctly."""
        content = TraceableString(
            "Text 1.\n"
            "%%FLACHTEX-NO-FORMAT-START\n"
            "Block 1. Not split.\n"
            "%%FLACHTEX-NO-FORMAT-STOP\n"
            "Text 2. Text 3.\n"
            "%%FLACHTEX-NO-FORMAT-START\n"
            "Block 2. Also not split.\n"
            "%%FLACHTEX-NO-FORMAT-STOP",
            "test.tex"
        )

        formatted = format_latex(content)
        formatted_str = str(formatted)

        # Normal text should be split
        assert "Text 2.\n" in formatted_str and "Text 3." in formatted_str, "Sentences between NO-FORMAT blocks must be split"

        # NO-FORMAT blocks should not be split
        assert "Block 1. Not split." in formatted_str, "First NO-FORMAT block must not be split"
        assert "Block 2. Also not split." in formatted_str, "Second NO-FORMAT block must not be split"


class TestMarkersInteraction:
    """
    Test interactions between different marker types.

    Users may combine SKIP, RAW, and NO-FORMAT markers. These must work
    together correctly without conflicts.
    """

    def test_raw_and_skip_markers_together(self):
        """
        Test RAW and SKIP markers in same document.

        Users may use RAW for problematic sections and SKIP for draft notes.
        Both should work independently.
        """
        document = {
            "main.tex": (
                "%%FLACHTEX-EXCLUDE-START\n"
                "Skip this.\n"
                "%%FLACHTEX-EXCLUDE-STOP\n"
                "Keep this.\n"
                "%%FLACHTEX-RAW-START\n"
                "Raw content.\n"
                "%%FLACHTEX-RAW-STOP"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Skip this." not in result_str, "SKIP blocks must be removed"
        assert "Keep this." in result_str, "Normal content must be kept"
        assert "Raw content." in result_str, "RAW blocks must be kept"

    def test_no_format_and_skip_together(self):
        """
        Test NO-FORMAT and SKIP markers work together.

        NO-FORMAT blocks can contain SKIP markers (skip rules apply to them).
        """
        content = TraceableString(
            "%%FLACHTEX-NO-FORMAT-START\n"
            "Pre-formatted.\n"
            "%%FLACHTEX-EXCLUDE-START\n"
            "Remove this.\n"
            "%%FLACHTEX-EXCLUDE-STOP\n"
            "Still pre-formatted.\n"
            "%%FLACHTEX-NO-FORMAT-STOP",
            "test.tex"
        )

        # Skip then format
        skipped = apply_skip_rules(content, [BasicSkipRule()])
        formatted = format_latex(skipped)
        formatted_str = str(formatted)

        assert "Pre-formatted." in formatted_str, "NO-FORMAT content before SKIP must be kept"
        assert "Remove this." not in formatted_str, "SKIP blocks inside NO-FORMAT must be removed"
        assert "Still pre-formatted." in formatted_str, "NO-FORMAT content after SKIP must be kept"

    def test_all_three_markers_together(self):
        """
        Test SKIP, RAW, and NO-FORMAT all in one document.

        Complex documents may use all three protection mechanisms.
        """
        document = {
            "main.tex": (
                "%%FLACHTEX-EXCLUDE-START\nSkip\n%%FLACHTEX-EXCLUDE-STOP\n"
                "Normal: Format this.\n"
                "%%FLACHTEX-RAW-START\nRaw: Don't process.\n%%FLACHTEX-RAW-STOP\n"
                "%%FLACHTEX-NO-FORMAT-START\nNo-format: Process but don't format.\n%%FLACHTEX-NO-FORMAT-STOP"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        formatted = format_latex(result)
        formatted_str = str(formatted)

        assert "Skip" not in formatted_str, "SKIP content must be removed"
        assert "Format this." in formatted_str, "Normal content must be processed and formatted"
        assert "Don't process." in formatted_str, "RAW content must pass through"
        assert "Process but don't format." in formatted_str, "NO-FORMAT content must be processed but not formatted"
