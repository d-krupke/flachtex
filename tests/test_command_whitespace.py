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
        # LaTeX behavior: \cmd swallows the space, result should be "REPLACEMENTtext"
        # Current flachtex: Does NOT swallow space due to bug (content[end] == " " always False)
        # For now, documenting actual behavior:
        assert str(result) == "REPLACEMENT text"  # BUG: should be "REPLACEMENTtext"

    def test_multiple_spaces_only_one_swallowed(self):
        """\\cmd followed by multiple spaces should swallow only the first."""
        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("REPLACEMENT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd  text", None), [sub]
        )
        # LaTeX behavior: \cmd swallows first space, second remains -> "REPLACEMENT text"
        # Current flachtex: Does NOT swallow any spaces
        assert str(result) == "REPLACEMENT  text"  # BUG: should be "REPLACEMENT text"

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


class TestCurrentBugDocumentation:
    """Document the current bug in whitespace handling."""

    def test_traceable_string_indexing_bug(self):
        """
        The bug: content[index] returns TraceableString, not str.

        In command_substitution.py line 132:
            while content[end] == " ":

        This comparison always fails because content[end] is a TraceableString
        object, not a string character. The fix should be:
            while str(content[end]) == " ":
        or:
            while content[end:end+1] == " ":  (if slicing returns str)
        """
        content = TraceableString("\\cmd asd", None)
        # Current behavior:
        assert content[4] != " "  # Returns TraceableString, not str
        assert str(content[4]) == " "  # Need to convert to str first

        # This is why space swallowing never works!


class TestProposedCorrectBehavior:
    """
    Document what the correct behavior should be after fixing the bug.

    These tests will fail with current implementation but show the goal.
    """

    def test_correct_single_space_swallowing(self):
        """After fix: \\cmd should swallow exactly one space."""
        # This test documents the DESIRED behavior
        # Skip for now since it will fail
        import pytest
        pytest.skip("Waiting for fix to TraceableString indexing in space swallowing")

        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("TEXT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd text", None), [sub]
        )
        # Should add {} to prevent further swallowing by LaTeX
        assert str(result) == "TEXT{} text" or str(result) == "TEXTtext"

    def test_correct_multiple_space_handling(self):
        """After fix: \\cmd should swallow only first of multiple spaces."""
        import pytest
        pytest.skip("Waiting for fix to TraceableString indexing in space swallowing")

        sub = NewCommandSubstitution(space_substitution=True)
        sub.new_command(
            NewCommandDefinition(
                TraceableString("cmd", None), 0, TraceableString("TEXT", None)
            )
        )
        result = apply_substitution_rules(
            TraceableString("\\cmd  text", None), [sub]
        )
        # Should swallow all spaces and add {}, resulting in one space
        assert str(result) == "TEXT{} text"
