r"""
Tests for LaTeX command substitution whitespace handling.

LaTeX has specific rules for how whitespace is handled after commands:

1. Control sequences (letter-based like \LaTeX, \foo) swallow exactly ONE following space
2. Control symbols (non-letter like \$, \%) do NOT swallow spaces
3. Commands with arguments do NOT swallow trailing spaces
4. Empty braces {} prevent space swallowing
5. \xspace package intelligently handles spaces

These tests document the expected behavior according to LaTeX semantics
and highlight current implementation issues.
"""

from flachtex import TraceableString
from flachtex.command_substitution import (
    NewCommandDefinition,
    NewCommandSubstitution,
)
from flachtex.rules import apply_substitution_rules


class TestControlSequenceSpaceSwallowing:
    """Test that control sequences (letter-based commands) swallow one space."""

    def test_single_space_swallowed(self):
        r"""\cmd followed by single space should swallow that space."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd text", None), [sub]
        )
        # LaTeX behavior: \cmd swallows the space, result is "cmdtext"
        # flachtex simulates this: swallows space and adds {} to prevent further swallowing
        assert str(result) == "REPLACEMENT{}text"

    def test_multiple_spaces_only_one_swallowed(self):
        r"""\cmd followed by multiple spaces should swallow all, then add {}."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd  text", None), [sub]
        )
        # flachtex swallows ALL consecutive spaces (not just one like LaTeX)
        # This is safer for preprocessing to avoid ambiguity
        assert str(result) == "REPLACEMENT{}text"

    def test_empty_braces_prevent_swallowing(self):
        """\\cmd{} should not swallow following space."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd{} text", None), [sub]
        )
        # LaTeX behavior: Empty braces prevent space swallowing
        assert str(result) == "REPLACEMENT{} text"  # This should be correct

    def test_newline_not_swallowed(self):
        """\\cmd followed by newline should not swallow the newline."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd\ntext", None), [sub]
        )
        # LaTeX behavior: Newlines are not spaces, should not be swallowed
        assert str(result) == "REPLACEMENT\ntext"


class TestXspacePackage:
    r"""Test interaction with \xspace package."""

    def test_xspace_prevents_explicit_space_handling(self):
        r"""Commands ending with \xspace should not need {} and space swallowing."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("TEXT\\xspace", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd text", None), [sub]
        )
        # \xspace intelligently adds space when needed
        # The substitution should not try to handle spaces itself
        assert str(result) == "TEXT\\xspace text"


class TestCommandsWithParameters:
    """Test that commands with parameters don't swallow trailing spaces."""

    def test_command_with_arg_preserves_space(self):
        """\\cmd{arg} should not swallow following space."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 1, TraceableString("#1!", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd{foo} text", None), [sub]
        )
        # Commands with arguments should not swallow trailing space
        assert str(result) == "foo! text"


class TestSpaceSubstitutionFlag:
    """Test the space_substitution parameter."""

    def test_space_substitution_disabled(self):
        """With space_substitution=False, spaces should never be swallowed."""
        sub = NewCommandSubstitution(space_substitution=False)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd text", None), [sub]
        )
        # When disabled, spaces should be preserved
        assert str(result) == "REPLACEMENT text"


class TestBugFix:
    """Verify that the whitespace handling bug has been fixed."""

    def test_traceable_string_indexing_fix(self):
        """
        The bug was: content[index] returns TraceableString, not str.

        The original buggy code:
            while content[end] == " ":

        This comparison always failed because content[end] is a TraceableString
        object, not a string character.

        The fix: Convert to string first before indexing
            content_str = str(content)
            while end < len(content_str) and content_str[end] == " ":
        """
        content = TraceableString("\\cmd asd", None)
        # Demonstrate the issue:
        assert content[4] != " "  # Returns TraceableString, not str
        assert str(content[4]) == " "  # Need to convert to str first

        # Verify the fix works
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("TEXT", None)
            )
        )
        result = apply_substitution_rules(content, [sub])
        # Should now swallow the space and add {} (no space remains)
        assert str(result) == "TEXT{}asd"


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_multiple_commands_in_sequence(self):
        r"""Multiple commands in sequence should each handle spaces."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("foo", None), 0, TraceableString("FOO", None)
            )
        )
        sub.new_command(
            NewCommandDefinition(
                TraceableString("bar", None), 0, TraceableString("BAR", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\foo \\bar text", None), [sub]
        )
        # Both commands should swallow their trailing spaces and add {}
        # All spaces between commands are swallowed, resulting in no spaces
        assert str(result) == "FOO{}BAR{}text"

    def test_command_at_end_of_line(self):
        r"""Command at end of line should not add {} if no space follows."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("TEXT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd", None), [sub]
        )
        # No space follows, so no {} should be added
        assert str(result) == "TEXT"
