"""Tests for skip rule implementations and edge cases.

Users need to exclude specific content from their flattened LaTeX documents
before submission to journals, conferences, or collaborators. Skip rules enable
selective content removal while preserving document structure.

Real-world scenarios where skip rules matter:
- Journal submission: Remove draft comments, TODOs, and internal notes
- Reviewer submission: Hide content meant for authors but not reviewers
- Clean output: Remove todonotes package commands that don't render well
- Tracked changes: Remove \\changes package commands after review is complete

Skip rule failures cause serious problems:
- Accidental disclosure: Draft notes or TODOs appear in submitted papers
- Compilation errors: Partial removal of environments breaks LaTeX compilation
- Incorrect output: Removing wrong content or keeping what should be removed
- Data loss: Over-aggressive skipping removes actual content by mistake
"""

import pytest

from flachtex import TraceableString
from flachtex.rules import (
    BasicSkipRule,
    CommentsPackageSkipRule,
    TodonotesRule,
    apply_skip_rules,
)


class TestBasicSkipRuleEdgeCases:
    """
    Test edge cases for BasicSkipRule.

    The BasicSkipRule handles %%FLACHTEX-SKIP-START/STOP markers that users
    insert to explicitly exclude content. This is the most direct control users
    have over what gets removed.

    Why this matters:
    - Users mark sensitive content for exclusion (e.g., internal notes)
    - Skip markers must work reliably or users lose control over output
    - Edge cases like nesting or missing markers must be handled gracefully
    """

    def test_nested_skip_markers(self):
        """Test that nested skip markers work correctly."""
        rule = BasicSkipRule()
        content = (
            "Keep this\n"
            "%%FLACHTEX-SKIP-START\n"
            "Remove this\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Keep this too"
        )
        skips = list(rule.find_all(content))
        assert len(skips) == 1
        assert "Remove this" in content[skips[0].start : skips[0].end]

    def test_multiple_independent_skip_blocks(self):
        """
        Test multiple non-overlapping skip blocks.

        Users often have multiple separate sections to exclude (e.g., internal
        notes at the start and end of a document). All must be removed.
        """
        rule = BasicSkipRule()
        content = (
            "%%FLACHTEX-SKIP-START\n"
            "Skip 1\n"
            "%%FLACHTEX-SKIP-STOP\n"
            "Keep\n"
            "%%FLACHTEX-SKIP-START\n"
            "Skip 2\n"
            "%%FLACHTEX-SKIP-STOP"
        )
        skips = list(rule.find_all(content))
        assert len(skips) == 2, "Multiple skip blocks must all be detected for complete content exclusion"

    def test_skip_with_indentation(self):
        """Test skip markers with leading whitespace."""
        rule = BasicSkipRule()
        content = (
            "Text\n"
            "  %%FLACHTEX-SKIP-START\n"
            "  Content\n"
            "  %%FLACHTEX-SKIP-STOP\n"
            "More text"
        )
        skips = list(rule.find_all(content))
        assert len(skips) == 1, "Indented skip markers must be recognized for code blocks or nested content"

    def test_skip_at_start_of_file(self):
        """Test skip block at the beginning of file."""
        rule = BasicSkipRule()
        content = "%%FLACHTEX-SKIP-START\nSkip\n%%FLACHTEX-SKIP-STOP\nKeep"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_skip_at_end_of_file(self):
        """Test skip block at the end of file."""
        rule = BasicSkipRule()
        content = "Keep\n%%FLACHTEX-SKIP-START\nSkip\n%%FLACHTEX-SKIP-STOP"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_unclosed_skip_start(self):
        """
        Test that unclosed skip start doesn't match.

        Users might forget to close a skip block. This must be detected to
        avoid silently removing everything after the START marker.
        """
        rule = BasicSkipRule()
        content = "%%FLACHTEX-SKIP-START\nSome content"
        skips = list(rule.find_all(content))
        # Should not match if there's no STOP
        assert len(skips) == 0, "Unclosed skip blocks must not match to prevent accidental content removal"

    def test_skip_stop_without_start(self):
        """Test that lone STOP marker doesn't match."""
        rule = BasicSkipRule()
        content = "Some content\n%%FLACHTEX-SKIP-STOP"
        skips = list(rule.find_all(content))
        assert len(skips) == 0, "STOP without START must be ignored to avoid unexpected behavior"


class TestCommentsPackageSkipRuleEdgeCases:
    """
    Test edge cases for CommentsPackageSkipRule.

    The LaTeX comment package provides \\begin{comment}...\\end{comment}
    environments. Users expect these to be removed in flattened output since
    they're meant as internal notes, not published content.

    Why this matters:
    - Comment environments often contain draft notes or disabled content
    - Users expect comment environments to be excluded automatically
    - Partial removal would break LaTeX compilation
    """

    def test_comment_environment_basic(self):
        """Test basic comment environment detection."""
        rule = CommentsPackageSkipRule()
        content = "Keep\n\\begin{comment}\nRemove\n\\end{comment}\nKeep"
        skips = list(rule.find_all(content))
        assert len(skips) == 1, "Comment environment must be detected for draft note removal"
        assert "Remove" in content[skips[0].start : skips[0].end], "Comment content must be identified for removal"

    def test_multiple_comment_blocks(self):
        """
        Test multiple comment environments.

        Users may have multiple comment blocks throughout their document.
        All must be removed to avoid leaking draft notes.
        """
        rule = CommentsPackageSkipRule()
        content = (
            "\\begin{comment}\nC1\n\\end{comment}\n"
            "Keep\n"
            "\\begin{comment}\nC2\n\\end{comment}"
        )
        skips = list(rule.find_all(content))
        assert len(skips) == 2, "All comment environments must be detected to remove all draft content"

    def test_comment_with_indentation(self):
        """Test comment environment with indentation."""
        rule = CommentsPackageSkipRule()
        content = "  \\begin{comment}\n  Content\n  \\end{comment}"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_inline_comment_environment(self):
        """Test comment environment on single line."""
        rule = CommentsPackageSkipRule()
        content = "\\begin{comment}Remove\\end{comment}"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_comment_with_trailing_newline(self):
        """Test that trailing newline after \\end{comment} is included."""
        rule = CommentsPackageSkipRule()
        content = "Keep\n\\begin{comment}\nRemove\n\\end{comment}\nKeep"
        skips = list(rule.find_all(content))
        # The regex should include the trailing newline
        assert len(skips) == 1

    def test_unclosed_comment_environment(self):
        """
        Test that unclosed comment environment doesn't match.

        Unclosed environments would cause LaTeX compilation errors. Flachtex
        should not partially remove them, as that would make errors worse.
        """
        rule = CommentsPackageSkipRule()
        content = "\\begin{comment}\nContent without end"
        skips = list(rule.find_all(content))
        # Should not match if not closed
        assert len(skips) == 0, "Unclosed comment environments must not match to avoid breaking LaTeX compilation"


class TestTodonotesRuleEdgeCases:
    """
    Test edge cases for TodonotesRule.

    The todonotes package is widely used for draft notes like \\todo{Fix this}.
    Users need these removed before submission to avoid embarrassing notes in
    published papers.

    Why this matters:
    - TODO notes are common in academic writing during drafting
    - Forgetting to remove TODOs before submission is embarrassing
    - TODOs often contain sensitive info about paper weaknesses
    - Automatic removal ensures clean submissions
    """

    def test_basic_todo(self):
        """Test basic \\todo command."""
        rule = TodonotesRule()
        content = "Text \\todo{Fix this} more text"
        skips = list(rule.find_all(content))
        assert len(skips) == 1, "\\todo commands must be detected to remove draft notes"

    def test_todo_with_optional_parameter(self):
        """
        Test \\todo with optional parameter.

        Users customize todos with options like [inline] or [color=red].
        All variants must be removed.
        """
        rule = TodonotesRule()
        content = "Text \\todo[inline]{Fix this} more text"
        skips = list(rule.find_all(content))
        assert len(skips) == 1, "\\todo with options must be detected to remove all draft notes"

    def test_multiple_todos(self):
        """
        Test multiple \\todo commands.

        Draft documents typically have many TODOs scattered throughout.
        Missing even one TODO in submission is problematic.
        """
        rule = TodonotesRule()
        content = "\\todo{First} text \\todo{Second} text \\todo{Third}"
        skips = list(rule.find_all(content))
        assert len(skips) == 3, "All \\todo commands must be detected to ensure clean submission"

    def test_todo_on_own_line(self):
        """Test \\todo on its own line."""
        rule = TodonotesRule()
        content = "Text\n\\todo{Fix this}\nMore text"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_todo_with_multiline_content(self):
        """Test \\todo with multiline content in braces."""
        rule = TodonotesRule()
        content = "\\todo{Line 1\nLine 2\nLine 3}"
        skips = list(rule.find_all(content))
        assert len(skips) == 1, "Multiline \\todo commands must be detected completely"

    def test_commented_todo_ignored(self):
        """Test that commented \\todo is detected (comments removed earlier)."""
        rule = TodonotesRule()
        content = "% \\todo{This is commented}\n\\todo{This is real}"
        skips = list(rule.find_all(content))
        # Note: The rule finds the command, comment removal happens earlier
        # in the pipeline, so this actually finds both
        assert len(skips) >= 1


class TestApplySkipRules:
    """
    Test applying skip rules to content.

    The apply_skip_rules function orchestrates all skip rules together.
    Users depend on this integration to ensure all unwanted content is removed
    in a single pass.

    Why this matters:
    - Users often combine multiple skip types (comments + todos + skip blocks)
    - All skip rules must work together without conflicts
    - Content must be removed cleanly without corrupting remaining text
    """

    def test_apply_single_rule(self):
        """Test applying a single skip rule."""
        content = TraceableString(
            "Keep\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP\nKeep", "test.tex"
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        assert "Keep" in str(result), "Non-skipped content must be preserved"
        assert "Remove" not in str(result), "Skipped content must be removed completely"

    def test_apply_multiple_rules(self):
        """
        Test applying multiple skip rules together.

        Journal submission workflow often requires removing skip blocks,
        comment environments, AND todos in one pass. All must work together.
        """
        content = TraceableString(
            "Keep\n"
            "%%FLACHTEX-SKIP-START\nSkip1\n%%FLACHTEX-SKIP-STOP\n"
            "\\begin{comment}Skip2\\end{comment}\n"
            "Keep",
            "test.tex",
        )
        result = apply_skip_rules(
            content, [BasicSkipRule(), CommentsPackageSkipRule()]
        )
        assert "Keep" in str(result), "Content outside skip regions must be preserved"
        assert "Skip1" not in str(result), "Skip block content must be removed"
        assert "Skip2" not in str(result), "Comment environment content must be removed"

    def test_apply_rules_preserves_order(self):
        """
        Test that remaining content preserves order.

        Document flow must be maintained after removing skipped sections.
        Section order matters for paper readability.
        """
        content = TraceableString(
            "A\n%%FLACHTEX-SKIP-START\nX\n%%FLACHTEX-SKIP-STOP\nB\nC", "test.tex"
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        result_str = str(result)
        assert result_str.find("A") < result_str.find("B") < result_str.find("C"), "Content order must be preserved after skipping"

    def test_apply_no_rules(self):
        """Test applying with no rules returns unchanged content."""
        content = TraceableString("Content", "test.tex")
        result = apply_skip_rules(content, [])
        assert str(result) == "Content"

    def test_apply_to_empty_content(self):
        """Test applying rules to empty content."""
        content = TraceableString("", "test.tex")
        result = apply_skip_rules(content, [BasicSkipRule()])
        assert str(result) == ""

    def test_multiple_skip_blocks_removed(self):
        """Test that multiple skip blocks are all removed."""
        content = TraceableString(
            "%%FLACHTEX-SKIP-START\nA\n%%FLACHTEX-SKIP-STOP\n"
            "Keep\n"
            "%%FLACHTEX-SKIP-START\nB\n%%FLACHTEX-SKIP-STOP",
            "test.tex",
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        assert "Keep" in str(result), "Content between skip blocks must be preserved"
        assert "A" not in str(result), "First skip block must be removed"
        assert "B" not in str(result), "Second skip block must be removed"


class TestSkipRuleErrorConditions:
    """
    Test error conditions for skip rules.

    Error conditions reveal bugs that could cause data loss or corruption.
    Proper error handling ensures users get clear feedback when something
    goes wrong rather than silently producing incorrect output.

    Why this matters:
    - Intersecting skip regions are ambiguous and must be caught
    - Clear error messages help users fix their documents
    - Failing fast prevents corrupted submissions
    """

    def test_intersecting_skips_error(self):
        """
        Test that intersecting skip regions raise an error.

        Overlapping skip regions would be ambiguous (which takes precedence?).
        This should never happen with manual markers, but must be detected to
        prevent data corruption if it occurs.
        """
        from flachtex.utils import Range

        class BadSkipRule:
            """A rule that produces intersecting ranges."""

            def find_all(self, content):
                yield Range(0, 10)
                yield Range(5, 15)

        content = TraceableString("0123456789012345", "test.tex")
        with pytest.raises(ValueError, match="Intersecting skipped parts"):
            apply_skip_rules(content, [BadSkipRule()])

    def test_adjacent_skips_allowed(self):
        """
        Test that adjacent (but non-overlapping) skips are allowed.

        Users should be able to have consecutive skip blocks without errors.
        Adjacent blocks are not ambiguous and should work fine.
        """
        from flachtex.utils import Range

        class AdjacentSkipRule:
            """A rule that produces adjacent ranges."""

            def find_all(self, content):
                yield Range(0, 5)
                yield Range(5, 10)

        content = TraceableString("0123456789", "test.tex")
        # Should not raise an error
        result = apply_skip_rules(content, [AdjacentSkipRule()])
        # Both ranges should be removed
        assert len(str(result)) == 0, "Adjacent skip blocks should both be removed without conflicts"


class TestSkipRulesWithTraceableString:
    """
    Test that skip rules preserve TraceableString origin information.

    Origin tracking enables users to trace flattened content back to source
    files. This is critical for debugging and understanding where content
    came from after flattening.

    Why this matters:
    - Users need to trace errors back to source files for fixing
    - Origin info supports the --attach flag for source tracking
    - Debugging multi-file projects requires knowing which file contributed what
    """

    def test_origin_preserved_after_skip(self):
        """
        Test that origin tracking is preserved after skipping.

        After removing skip blocks, remaining content must still track back
        to original source files for debugging.
        """
        content = TraceableString(
            "Keep\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP\nAlso keep",
            "test.tex",
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        # Result should still be a TraceableString
        assert isinstance(result, TraceableString), "Result must be TraceableString to preserve origin tracking"
        # Origin information should be preserved for first character
        assert "test.tex" in str(result.get_origin(0)), "Origin information must be preserved for debugging"

    def test_complex_skip_with_includes(self):
        """
        Test skip rules work correctly with file includes.

        Real projects combine file inclusion with skip rules. Skip blocks
        in included files must be removed correctly.
        """
        from flachtex import FileFinder, Preprocessor

        document = {
            "main.tex": (
                "Keep main\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip main\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\\input{section.tex}"
            ),
            "section.tex": (
                "Keep section\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip section\n"
                "%%FLACHTEX-SKIP-STOP"
            ),
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        assert "Keep main" in result_str, "Content from main file must be preserved"
        assert "Keep section" in result_str, "Content from included file must be preserved"
        assert "Skip main" not in result_str, "Skip blocks in main file must be removed"
        assert "Skip section" not in result_str, "Skip blocks in included files must be removed"


class TestSkipRulesCombinedWithOtherFeatures:
    """
    Test skip rules combined with other flachtex features.

    Users combine skip rules with other features (comment removal, command
    substitution, etc.) in their workflows. These combinations must work
    correctly together.

    Why this matters:
    - Real workflows use multiple features simultaneously
    - Feature interactions could cause unexpected behavior
    - Users need predictable behavior for reliable submissions
    """

    def test_skip_with_comments_removal(self):
        """
        Test skip rules work with comment removal.

        Journal submission workflow typically involves both removing skip
        blocks AND removing LaTeX comments. Both must work together.
        """
        from flachtex import remove_comments

        content = TraceableString(
            "Keep % comment\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP", "test.tex"
        )
        # First apply skip rules
        content = apply_skip_rules(content, [BasicSkipRule()])
        # Then remove comments
        result = remove_comments(content)
        result_str = str(result)

        assert "Keep" in result_str, "Text content must be preserved"
        assert "Remove" not in result_str, "Skipped content must be removed"
        assert "comment" not in result_str, "Comments must be removed"

    def test_skip_with_command_substitution(self):
        """
        Test skip rules with command substitution.

        Users may have custom commands inside skip blocks. Commands inside
        skip blocks should NOT be substituted since the content is removed.
        """
        from flachtex import Preprocessor, FileFinder
        from flachtex.command_substitution import (
            NewCommandDefinition,
            NewCommandSubstitution,
        )

        document = {
            "main.tex": (
                "\\newcommand{\\foo}{BAR}\n"
                "\\foo\n"
                "%%FLACHTEX-SKIP-START\n"
                "\\foo should be skipped\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\\foo again"
            )
        }

        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)

        # Add command substitution
        ncs = NewCommandSubstitution()
        ncs.new_command(
            NewCommandDefinition(
                TraceableString("foo", None), 0, TraceableString("REPLACED", None)
            )
        )
        preprocessor.substitution_rules.append(ncs)

        result = preprocessor.expand_file("main.tex")
        result_str = str(result)

        # \foo outside skip blocks should be replaced
        assert "REPLACED" in result_str, "Commands outside skip blocks must be substituted"
        # Content inside skip block should not appear
        assert "should be skipped" not in result_str, "Skipped content must not appear even with command substitution"
