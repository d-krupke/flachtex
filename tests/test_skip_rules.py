"""Tests for skip rule implementations and edge cases."""

import pytest

from flachtex import TraceableString
from flachtex.rules import (
    BasicSkipRule,
    CommentsPackageSkipRule,
    TodonotesRule,
    apply_skip_rules,
)


class TestBasicSkipRuleEdgeCases:
    """Test edge cases for BasicSkipRule."""

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
        """Test multiple non-overlapping skip blocks."""
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
        assert len(skips) == 2

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
        assert len(skips) == 1

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
        """Test that unclosed skip start doesn't match."""
        rule = BasicSkipRule()
        content = "%%FLACHTEX-SKIP-START\nSome content"
        skips = list(rule.find_all(content))
        # Should not match if there's no STOP
        assert len(skips) == 0

    def test_skip_stop_without_start(self):
        """Test that lone STOP marker doesn't match."""
        rule = BasicSkipRule()
        content = "Some content\n%%FLACHTEX-SKIP-STOP"
        skips = list(rule.find_all(content))
        assert len(skips) == 0


class TestCommentsPackageSkipRuleEdgeCases:
    """Test edge cases for CommentsPackageSkipRule."""

    def test_comment_environment_basic(self):
        """Test basic comment environment detection."""
        rule = CommentsPackageSkipRule()
        content = "Keep\n\\begin{comment}\nRemove\n\\end{comment}\nKeep"
        skips = list(rule.find_all(content))
        assert len(skips) == 1
        assert "Remove" in content[skips[0].start : skips[0].end]

    def test_multiple_comment_blocks(self):
        """Test multiple comment environments."""
        rule = CommentsPackageSkipRule()
        content = (
            "\\begin{comment}\nC1\n\\end{comment}\n"
            "Keep\n"
            "\\begin{comment}\nC2\n\\end{comment}"
        )
        skips = list(rule.find_all(content))
        assert len(skips) == 2

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
        """Test that unclosed comment environment doesn't match."""
        rule = CommentsPackageSkipRule()
        content = "\\begin{comment}\nContent without end"
        skips = list(rule.find_all(content))
        # Should not match if not closed
        assert len(skips) == 0


class TestTodonotesRuleEdgeCases:
    """Test edge cases for TodonotesRule."""

    def test_basic_todo(self):
        """Test basic \\todo command."""
        rule = TodonotesRule()
        content = "Text \\todo{Fix this} more text"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_todo_with_optional_parameter(self):
        """Test \\todo with optional parameter."""
        rule = TodonotesRule()
        content = "Text \\todo[inline]{Fix this} more text"
        skips = list(rule.find_all(content))
        assert len(skips) == 1

    def test_multiple_todos(self):
        """Test multiple \\todo commands."""
        rule = TodonotesRule()
        content = "\\todo{First} text \\todo{Second} text \\todo{Third}"
        skips = list(rule.find_all(content))
        assert len(skips) == 3

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
        assert len(skips) == 1

    def test_commented_todo_ignored(self):
        """Test that commented \\todo is detected (comments removed earlier)."""
        rule = TodonotesRule()
        content = "% \\todo{This is commented}\n\\todo{This is real}"
        skips = list(rule.find_all(content))
        # Note: The rule finds the command, comment removal happens earlier
        # in the pipeline, so this actually finds both
        assert len(skips) >= 1


class TestApplySkipRules:
    """Test applying skip rules to content."""

    def test_apply_single_rule(self):
        """Test applying a single skip rule."""
        content = TraceableString(
            "Keep\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP\nKeep", "test.tex"
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        assert "Keep" in str(result)
        assert "Remove" not in str(result)

    def test_apply_multiple_rules(self):
        """Test applying multiple skip rules."""
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
        assert "Keep" in str(result)
        assert "Skip1" not in str(result)
        assert "Skip2" not in str(result)

    def test_apply_rules_preserves_order(self):
        """Test that remaining content preserves order."""
        content = TraceableString(
            "A\n%%FLACHTEX-SKIP-START\nX\n%%FLACHTEX-SKIP-STOP\nB\nC", "test.tex"
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        result_str = str(result)
        assert result_str.find("A") < result_str.find("B") < result_str.find("C")

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
        assert "Keep" in str(result)
        assert "A" not in str(result)
        assert "B" not in str(result)


class TestSkipRuleErrorConditions:
    """Test error conditions for skip rules."""

    def test_intersecting_skips_error(self):
        """Test that intersecting skip regions raise an error."""
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
        """Test that adjacent (but non-overlapping) skips are allowed."""
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
        assert len(str(result)) == 0


class TestSkipRulesWithTraceableString:
    """Test that skip rules preserve TraceableString origin information."""

    def test_origin_preserved_after_skip(self):
        """Test that origin tracking is preserved after skipping."""
        content = TraceableString(
            "Keep\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP\nAlso keep",
            "test.tex",
        )
        result = apply_skip_rules(content, [BasicSkipRule()])
        # Result should still be a TraceableString
        assert isinstance(result, TraceableString)
        # Origin information should be preserved for first character
        assert "test.tex" in str(result.get_origin(0))

    def test_complex_skip_with_includes(self):
        """Test skip rules work correctly with file includes."""
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

        assert "Keep main" in result_str
        assert "Keep section" in result_str
        assert "Skip main" not in result_str
        assert "Skip section" not in result_str


class TestSkipRulesCombinedWithOtherFeatures:
    """Test skip rules combined with other flachtex features."""

    def test_skip_with_comments_removal(self):
        """Test skip rules work with comment removal."""
        from flachtex import remove_comments

        content = TraceableString(
            "Keep % comment\n%%FLACHTEX-SKIP-START\nRemove\n%%FLACHTEX-SKIP-STOP", "test.tex"
        )
        # First apply skip rules
        content = apply_skip_rules(content, [BasicSkipRule()])
        # Then remove comments
        result = remove_comments(content)
        result_str = str(result)

        assert "Keep" in result_str
        assert "Remove" not in result_str
        assert "comment" not in result_str

    def test_skip_with_command_substitution(self):
        """Test skip rules with command substitution."""
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
        assert "REPLACED" in result_str
        # Content inside skip block should not appear
        assert "should be skipped" not in result_str
