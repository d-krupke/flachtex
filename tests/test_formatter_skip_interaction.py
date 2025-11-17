"""
Tests for the interaction between formatter and skip rules.

This module documents the expected behavior when skip rules and formatting
are used together. Understanding this interaction is critical for users who
want both clean, formatted output AND selective content removal.

Key questions this module answers:
1. What order do operations happen in (skip then format, or format then skip)?
2. How are skip markers themselves handled during formatting?
3. What happens to blank lines left after skip blocks are removed?
4. Can users format content before applying skip rules?
5. How do indentation and skip blocks interact?
"""

import pytest

from flachtex import FileFinder, Preprocessor, TraceableString
from flachtex.formatter import format_latex
from flachtex.rules import BasicSkipRule, apply_skip_rules


class TestSkipThenFormat:
    """
    Test the standard workflow: apply skip rules during flattening, then format.

    This is the typical flachtex usage pattern where:
    1. Document is flattened (skip rules apply automatically during read_file)
    2. Result is optionally formatted for diff-friendly output

    Users expect: Removed content never gets formatted (efficient, clean)
    """

    def test_skip_during_flatten_then_format(self):
        """
        Test that skip rules apply during flattening, before formatting.

        User workflow: Flatten document with skip rules, then format result.
        Expected: Skip blocks are removed during flattening, formatter never sees them.
        """
        document = {
            "main.tex": (
                "This is sentence one. This is sentence two.\n"
                "%%FLACHTEX-SKIP-START\n"
                "This should be skipped. Also this.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "This is sentence three."
            )
        }

        # Flatten (skip rules apply automatically in preprocessor.read_file)
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")

        # Skip block should already be gone
        assert "should be skipped" not in str(flattened), "Skip block must be removed during flattening"
        assert "%%FLACHTEX-SKIP" not in str(flattened), "Skip markers must be removed"

        # Then format
        result = format_latex(flattened)
        result_str = str(result)

        # Sentences should be split
        assert "This is sentence one.\n" in result_str, "Sentences must be split after skipping"
        assert "This is sentence two.\n" in result_str
        assert "This is sentence three." in result_str
        # Skipped content should not appear
        assert "should be skipped" not in result_str, "Skipped content must not appear in formatted output"

    def test_blank_lines_after_skip_normalized(self):
        """
        Test that blank lines left by skip blocks are normalized by formatter.

        When skip blocks are removed, they often leave excessive blank lines.
        Users expect the formatter to clean these up for professional output.
        """
        document = {
            "main.tex": (
                "First paragraph.\n"
                "\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip this paragraph.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\n"
                "Second paragraph."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")

        # After skipping, there might be multiple blank lines
        # Format should normalize them
        result = format_latex(flattened)
        result_str = str(result)

        # Should have at most 2 consecutive newlines (1 blank line)
        assert "\n\n\n" not in result_str, "Excessive blank lines must be normalized"
        assert "First paragraph." in result_str
        assert "Second paragraph." in result_str

    def test_skip_inside_environment_then_format_with_indent(self):
        """
        Test skip blocks inside environments, then format with indentation.

        Users organize content in environments and may want to skip some items.
        Remaining items should be properly indented after skip blocks are removed.
        """
        document = {
            "main.tex": (
                "\\begin{itemize}\n"
                "\\item First item.\n"
                "%%FLACHTEX-SKIP-START\n"
                "\\item Skipped item.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\\item Second item.\n"
                "\\end{itemize}"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")

        # Format with indentation
        result = format_latex(flattened, indent=2)
        result_str = str(result)

        # Should be properly indented
        assert "  \\item First item." in result_str, "Remaining items must be indented correctly"
        assert "  \\item Second item." in result_str
        # Skipped item should not appear
        assert "Skipped item" not in result_str, "Skipped items must not appear in formatted output"


class TestFormatThenSkip:
    """
    Test the reverse workflow: format first, then apply skip rules.

    This is an alternative workflow where users might:
    1. Format their document for readability
    2. Then apply skip rules to remove marked sections

    Users might expect this to work if they call format_latex() manually.
    """

    def test_format_preserves_skip_markers(self):
        """
        Test that skip markers are preserved during formatting.

        If a user formats before applying skip rules, the skip markers
        (which are comments) should be preserved so skip rules can still work.

        Why this matters: Users doing manual formatting might format first,
        then want to apply skip rules. Skip markers must survive formatting.
        """
        content = TraceableString(
            "Text before.\n"
            "%%FLACHTEX-SKIP-START\n"
            "Content to skip.\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Text after.",
            "test.tex"
        )

        # Format first
        formatted = format_latex(content)
        formatted_str = str(formatted)

        # Skip markers should still be present (they're comments)
        assert "%%FLACHTEX-SKIP-START" in formatted_str, "Skip markers must be preserved during formatting"
        assert "%%FLACHTEX-SKIP-STOP" in formatted_str, "Skip markers must be preserved during formatting"

        # Then apply skip rules
        result = apply_skip_rules(formatted, [BasicSkipRule()])
        result_str = str(result)

        # Skip block should be removed
        assert "Content to skip" not in result_str, "Skip rules must work on formatted content"
        assert "%%FLACHTEX-SKIP" not in result_str, "Skip markers must be removed"
        assert "Text before" in result_str
        assert "Text after" in result_str

    def test_format_then_skip_maintains_formatting(self):
        """
        Test that formatting is maintained after skip rules are applied.

        If content is formatted (sentence per line) before skip rules,
        the sentence splitting should be preserved after skip rules remove content.
        """
        content = TraceableString(
            "Sentence one. Sentence two.\n"
            "%%FLACHTEX-SKIP-START\n"
            "Skip this. And this.\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Sentence three.",
            "test.tex"
        )

        # Format first (sentence per line)
        formatted = format_latex(content)

        # Then skip
        result = apply_skip_rules(formatted, [BasicSkipRule()])
        result_str = str(result)

        # Sentences should still be on separate lines
        assert "Sentence one.\n" in result_str, "Sentence formatting must be preserved after skipping"
        assert "Sentence two.\n" in result_str
        assert "Sentence three." in result_str
        assert "Skip this" not in result_str


class TestSkipMarkersInFormattedContent:
    """
    Test how skip markers themselves behave during formatting.

    Skip markers are special comments (%%FLACHTEX-...). Understanding how
    the formatter treats them is important for predictable behavior.
    """

    def test_skip_markers_are_comment_lines(self):
        """
        Test that skip markers are recognized as comment lines by formatter.

        Skip markers start with %%, making them LaTeX comments. The formatter's
        CommentDetector should identify them as protected content that won't be
        reformatted.
        """
        content = TraceableString(
            "Text before.\n"
            "%%FLACHTEX-SKIP-START\n"
            "Content.\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Text after.",
            "test.tex"
        )

        formatted = format_latex(content)
        formatted_str = str(formatted)

        # Skip markers should remain on their own lines
        assert "%%FLACHTEX-SKIP-START\n" in formatted_str, "Skip START marker must stay on own line"
        assert "%%FLACHTEX-SKIP-STOP\n" in formatted_str, "Skip STOP marker must stay on own line"

    def test_indented_skip_markers_preserved(self):
        """
        Test that indented skip markers are preserved during formatting.

        Users might indent skip markers within environments. These should be
        preserved by the formatter (as comments) and still work with skip rules.
        """
        content = TraceableString(
            "\\begin{itemize}\n"
            "  \\item Item one.\n"
            "  %%FLACHTEX-SKIP-START\n"
            "  \\item Skip this.\n"
            "  %%FLACHTEX-SKIP-STOP\n"
            "  \\item Item two.\n"
            "\\end{itemize}",
            "test.tex"
        )

        # Format with indentation
        formatted = format_latex(content, indent=2)

        # Skip markers should still be present
        assert "%%FLACHTEX-SKIP-START" in str(formatted), "Indented skip markers must be preserved"

        # Skip rules should still work
        result = apply_skip_rules(formatted, [BasicSkipRule()])
        assert "Skip this" not in str(result), "Skip rules must work on indented markers"


class TestEdgeCases:
    """
    Test edge cases in the skip-format interaction.

    These tests document corner cases and unexpected scenarios that users
    might encounter when combining skip rules with formatting.
    """

    def test_skip_block_with_sentences_never_formatted(self):
        """
        Test that content inside skip blocks never gets sentence formatting.

        Efficiency check: If skip rules run before formatting (standard workflow),
        content inside skip blocks should never be formatted since it's removed first.
        """
        document = {
            "main.tex": (
                "Keep this. And this.\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip sentence one. Skip sentence two. Skip sentence three.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "Keep this too."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")

        # Flattened content should not have skip block
        flattened_str = str(flattened)
        assert "Skip sentence" not in flattened_str, "Skip block must be removed before formatting"

        # Format (skip content never gets formatted - efficient!)
        result = format_latex(flattened)

        # Only kept sentences should be formatted
        assert "Keep this.\n" in str(result)
        assert "And this.\n" in str(result)

    def test_empty_skip_block_leaves_no_trace(self):
        """
        Test that empty skip blocks are removed cleanly.

        Users might have empty skip blocks. These should be removed without
        leaving extra blank lines or other artifacts.
        """
        content = TraceableString(
            "Text before.\n"
            "%%FLACHTEX-SKIP-START\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Text after.",
            "test.tex"
        )

        # Apply skip rules
        skipped = apply_skip_rules(content, [BasicSkipRule()])

        # Format
        result = format_latex(skipped)
        result_str = str(result)

        # Should just have the two text lines
        assert "Text before." in result_str
        assert "Text after." in result_str
        # No skip markers
        assert "%%FLACHTEX-SKIP" not in result_str

    def test_multiple_skip_blocks_with_formatting(self):
        """
        Test multiple skip blocks with formatting.

        Complex documents may have multiple skip blocks scattered throughout.
        All should be removed cleanly, and remaining content should format correctly.
        """
        document = {
            "main.tex": (
                "Intro sentence one. Intro sentence two.\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip block 1.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "Middle sentence one. Middle sentence two.\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip block 2.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "End sentence one."
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")
        result = format_latex(flattened)
        result_str = str(result)

        # All kept sentences should be formatted
        assert "Intro sentence one.\n" in result_str
        assert "Middle sentence one.\n" in result_str
        assert "End sentence one." in result_str

        # Skip blocks should not appear
        assert "Skip block 1" not in result_str
        assert "Skip block 2" not in result_str


class TestUserWorkflowDocumentation:
    """
    Document recommended user workflows for combining skip and format.

    These tests serve as documentation for how users should structure their
    flachtex workflow to get predictable results.
    """

    def test_recommended_workflow_flatten_then_format(self):
        """
        Recommended workflow: Flatten (with skip) then format.

        This is the standard, efficient workflow:
        1. flachtex flattens document (skip rules apply during preprocessing)
        2. Call format_latex() on the flattened result
        3. Get clean, formatted output with unwanted content already removed

        Why this is best:
        - Skip content never gets formatted (faster)
        - Skip markers themselves are removed during flattening
        - Clean separation of concerns: flatten then prettify
        """
        document = {
            "main.tex": "\\input{content.tex}",
            "content.tex": (
                "Academic content here. More content.\n"
                "%%FLACHTEX-SKIP-START\n"
                "Internal notes. Do not publish.\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "Published content continues."
            )
        }

        # Step 1: Flatten (skip rules apply automatically)
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        flattened = preprocessor.expand_file("main.tex")

        # Step 2: Format
        formatted = format_latex(flattened, indent=2)

        # Result: Clean, formatted, without internal notes
        result_str = str(formatted)
        assert "Academic content here.\n" in result_str, "Content must be formatted"
        assert "Internal notes" not in result_str, "Skip blocks must be removed"
        assert "Published content continues." in result_str

    def test_alternative_workflow_manual_format_then_skip(self):
        """
        Alternative workflow: Manually format content, then apply skip rules.

        Some users might want to:
        1. Format their LaTeX source for readability
        2. Then apply skip rules to remove marked sections

        This works because skip markers are preserved during formatting.
        However, it's less efficient (formats content that will be removed).
        """
        content = TraceableString(
            "Content one. Content two.\n"
            "%%FLACHTEX-SKIP-START\n"
            "Skip this. And this.\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Content three.",
            "test.tex"
        )

        # Step 1: Format
        formatted = format_latex(content)

        # Step 2: Apply skip rules
        result = apply_skip_rules(formatted, [BasicSkipRule()])

        # Result: Formatted content with skip blocks removed
        result_str = str(result)
        assert "Content one.\n" in result_str, "Formatting must be preserved"
        assert "Content two.\n" in result_str
        assert "Skip this" not in result_str, "Skip blocks must be removed"
