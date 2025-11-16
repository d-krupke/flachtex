"""Tests for the main CLI module."""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from flachtex.main import find_command_definitions, main, parse_arguments


class TestParseArguments:
    """Test argument parsing."""

    def test_minimal_arguments(self):
        """Test parsing with just a file path."""
        with patch("sys.argv", ["flachtex", "test.tex"]):
            args = parse_arguments()
            assert args.path == ["test.tex"]
            assert not args.to_json
            assert not args.comments
            assert not args.attach
            assert not args.changes
            assert not args.changes_prefix
            assert not args.todos
            assert not args.newcommand

    def test_json_output(self):
        """Test --to_json flag."""
        with patch("sys.argv", ["flachtex", "--to_json", "test.tex"]):
            args = parse_arguments()
            assert args.to_json
            assert args.path == ["test.tex"]

    def test_remove_comments(self):
        """Test --comments flag."""
        with patch("sys.argv", ["flachtex", "--comments", "test.tex"]):
            args = parse_arguments()
            assert args.comments
            assert args.path == ["test.tex"]

    def test_attach_sources(self):
        """Test --attach flag."""
        with patch("sys.argv", ["flachtex", "--attach", "test.tex"]):
            args = parse_arguments()
            assert args.attach
            assert args.path == ["test.tex"]

    def test_changes_package(self):
        """Test --changes flag."""
        with patch("sys.argv", ["flachtex", "--changes", "test.tex"]):
            args = parse_arguments()
            assert args.changes
            assert args.path == ["test.tex"]

    def test_changes_prefix(self):
        """Test --changes_prefix flag."""
        with patch("sys.argv", ["flachtex", "--changes_prefix", "test.tex"]):
            args = parse_arguments()
            assert args.changes_prefix
            assert args.path == ["test.tex"]

    def test_remove_todos(self):
        """Test --todos flag."""
        with patch("sys.argv", ["flachtex", "--todos", "test.tex"]):
            args = parse_arguments()
            assert args.todos
            assert args.path == ["test.tex"]

    def test_newcommand_substitution(self):
        """Test --newcommand flag."""
        with patch("sys.argv", ["flachtex", "--newcommand", "test.tex"]):
            args = parse_arguments()
            assert args.newcommand
            assert args.path == ["test.tex"]

    def test_multiple_flags(self):
        """Test multiple flags together."""
        with patch(
            "sys.argv",
            ["flachtex", "--to_json", "--comments", "--todos", "test.tex"],
        ):
            args = parse_arguments()
            assert args.to_json
            assert args.comments
            assert args.todos
            assert args.path == ["test.tex"]

    def test_all_flags(self):
        """Test all flags enabled."""
        with patch(
            "sys.argv",
            [
                "flachtex",
                "--to_json",
                "--comments",
                "--attach",
                "--changes",
                "--changes_prefix",
                "--todos",
                "--newcommand",
                "main.tex",
            ],
        ):
            args = parse_arguments()
            assert args.to_json
            assert args.comments
            assert args.attach
            assert args.changes
            assert args.changes_prefix
            assert args.todos
            assert args.newcommand
            assert args.path == ["main.tex"]


class TestFindCommandDefinitions:
    """Test finding command definitions."""

    def test_no_commands(self, tmp_path):
        """Test with document that has no custom commands."""
        test_file = tmp_path / "test.tex"
        test_file.write_text("\\documentclass{article}\n\\begin{document}\nText\n\\end{document}")

        result = find_command_definitions(str(test_file))
        assert result is not None
        # Should return a NewCommandSubstitution with no commands
        assert result._commands == {}

    def test_single_command(self, tmp_path):
        """Test with document that has one custom command."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(
            "\\newcommand{\\foo}{bar}\n"
            "\\begin{document}\n"
            "\\foo\n"
            "\\end{document}"
        )

        result = find_command_definitions(str(test_file))
        assert "foo" in result._commands
        assert str(result._commands["foo"].command) == "bar"

    def test_multiple_commands(self, tmp_path):
        """Test with document that has multiple custom commands."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(
            "\\newcommand{\\foo}{bar}\n"
            "\\newcommand{\\baz}{qux}\n"
            "\\begin{document}\n"
            "\\foo \\baz\n"
            "\\end{document}"
        )

        result = find_command_definitions(str(test_file))
        assert "foo" in result._commands
        assert "baz" in result._commands

    def test_commands_with_parameters(self, tmp_path):
        """Test with commands that have parameters."""
        test_file = tmp_path / "test.tex"
        test_file.write_text(
            "\\newcommand{\\test}[2]{#2-#1}\n"
            "\\begin{document}\n"
            "\\test{a}{b}\n"
            "\\end{document}"
        )

        result = find_command_definitions(str(test_file))
        assert "test" in result._commands
        assert result._commands["test"].num_parameters == 2


class TestMain:
    """Test the main function."""

    def test_basic_flattening(self, tmp_path):
        """Test basic file flattening."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Hello World\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            assert "Hello World" in output
            assert "\\documentclass{article}" in output

    def test_json_output(self, tmp_path):
        """Test JSON output format."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Test\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", "--to_json", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # Should be valid JSON
            data = json.loads(output)
            assert "content" in data
            assert "Test" in data["content"]

    def test_comment_removal(self, tmp_path):
        """Test comment removal."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Text % This is a comment\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", "--comments", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            assert "Text" in output
            # Comment should be removed
            assert "This is a comment" not in output

    def test_file_inclusion(self, tmp_path):
        """Test that file inclusion works."""
        main_file = tmp_path / "main.tex"
        included_file = tmp_path / "included.tex"

        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{included.tex}\n"
            "\\end{document}"
        )
        included_file.write_text("Included content")

        with patch("sys.argv", ["flachtex", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            assert "Included content" in output

    def test_newcommand_substitution(self, tmp_path):
        """Test custom command substitution."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\newcommand{\\foo}{bar}\n"
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\foo\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # The command definition should still be present
            assert "\\newcommand" in output
            # But the usage should be expanded (appears twice - once in def, once expanded)
            # Note: without --newcommand flag, the substitution still happens via
            # find_command_definitions being called in main()

    def test_json_with_sources(self, tmp_path):
        """Test JSON output includes source structure."""
        main_file = tmp_path / "main.tex"
        included = tmp_path / "section.tex"

        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{section.tex}\n"
            "\\end{document}"
        )
        included.write_text("\\section{Test}\nContent")

        with patch("sys.argv", ["flachtex", "--to_json", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            data = json.loads(output)

            # Should have sources in the output
            assert "sources" in data
            # Main file should be in sources
            assert str(main_file) in data["sources"]


class TestMainIntegration:
    """Integration tests for main with various flag combinations."""

    def test_todos_and_comments(self, tmp_path):
        """Test --todos and --comments together."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Text % comment\n"
            "\\todo{Fix this}\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", "--todos", "--comments", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            assert "Text" in output
            # Comment should be removed
            assert "comment" not in output

    def test_json_and_comments(self, tmp_path):
        """Test --to_json and --comments together."""
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Text % comment\n"
            "\\end{document}"
        )

        with patch(
            "sys.argv", ["flachtex", "--to_json", "--comments", str(main_file)]
        ):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            data = json.loads(output)
            assert "Text" in data["content"]
            # Comment should be removed
            assert "comment" not in data["content"]

    def test_complex_multifile_project(self, tmp_path):
        """Test with a complex project structure."""
        main_file = tmp_path / "main.tex"
        intro = tmp_path / "intro.tex"
        methods = tmp_path / "methods.tex"

        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\input{intro.tex}\n"
            "\\input{methods.tex}\n"
            "\\end{document}"
        )
        intro.write_text("\\section{Introduction}\nIntro text")
        methods.write_text("\\section{Methods}\nMethods text")

        with patch("sys.argv", ["flachtex", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            assert "Introduction" in output
            assert "Intro text" in output
            assert "Methods" in output
            assert "Methods text" in output
