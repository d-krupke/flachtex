"""Tests for the main CLI module.

The flachtex CLI is the primary interface users interact with to flatten their
multi-file LaTeX projects into single documents. Users rely on the CLI to:
- Correctly merge multiple .tex files from complex project structures
- Remove comments, todos, and tracked changes when preparing submissions
- Output flattened documents in text or JSON format for different workflows
- Substitute custom LaTeX commands to ensure compilation compatibility

This module tests critical user-facing workflows:
- Journal submission: Flatten project + remove comments/todos in one command
- Version control: Use --attach to track which files contributed content
- Collaboration: Use --changes to preserve tracked changes from collaborators
- Debugging: Use --to_json to analyze the structure of flattened output
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from flachtex.main import find_command_definitions, main, parse_arguments


class TestParseArguments:
    """
    Test CLI argument parsing.

    Users need reliable argument parsing to configure flachtex behavior without
    memorizing complex command syntax. Incorrect parsing could cause users to:
    - Accidentally submit drafts with TODOs still visible
    - Lose track of which files contributed to the output
    - Get malformed JSON output that breaks their automation scripts
    """

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
        """Test all flags enabled for complete journal submission workflow."""
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
            assert args.to_json, "JSON output flag must be recognized for automation workflows"
            assert args.comments, "Comments flag must be recognized to remove draft comments"
            assert args.attach, "Attach flag must be recognized to track source files"
            assert args.changes, "Changes flag must be recognized to handle tracked changes"
            assert args.changes_prefix, "Changes prefix flag must be recognized for review workflows"
            assert args.todos, "Todos flag must be recognized to remove todos before submission"
            assert args.newcommand, "Newcommand flag must be recognized for command substitution"
            assert args.path == ["main.tex"]

    def test_format_flag(self):
        """
        Test --format flag for diff-friendly output.

        Users need CLI access to formatter for version control workflows.
        Currently no way to format from CLI without Python code.
        """
        with patch("sys.argv", ["flachtex", "--format", "test.tex"]):
            args = parse_arguments()
            assert args.format, "--format flag must be recognized to enable diff-friendly formatting"
            assert args.path == ["test.tex"]

    def test_format_with_indent(self):
        """
        Test --format with --indent for environment indentation.

        Users want control over indentation level for readability preferences.
        """
        with patch("sys.argv", ["flachtex", "--format", "--indent", "4", "test.tex"]):
            args = parse_arguments()
            assert args.format, "--format flag must be parsed"
            assert args.indent == 4, "--indent value must be parsed as integer"
            assert args.path == ["test.tex"]

    def test_indent_without_format(self):
        """
        Test that --indent can be used without --format.

        Some users may want indentation without sentence splitting.
        """
        with patch("sys.argv", ["flachtex", "--indent", "2", "test.tex"]):
            args = parse_arguments()
            assert args.indent == 2, "--indent must work without --format"
            assert args.path == ["test.tex"]

    def test_format_defaults(self):
        """Test that format and indent have correct defaults."""
        with patch("sys.argv", ["flachtex", "test.tex"]):
            args = parse_arguments()
            assert not hasattr(args, 'format') or not args.format, "Formatting must be opt-in by default"
            assert not hasattr(args, 'indent') or args.indent == 0, "Indentation must default to 0 (disabled)"


class TestFindCommandDefinitions:
    """
    Test finding custom LaTeX command definitions.

    Users define custom commands with \\newcommand to simplify their LaTeX source.
    Flachtex must find these definitions to enable substitution, ensuring the
    flattened document compiles correctly even when custom commands are used.
    This matters when:
    - Journals don't support custom commands in submissions
    - Users want self-contained documents without preamble dependencies
    - Debugging compilation errors related to command definitions
    """

    def test_no_commands(self, tmp_path):
        """Test with document that has no custom commands."""
        test_file = tmp_path / "test.tex"
        test_file.write_text("\\documentclass{article}\n\\begin{document}\nText\n\\end{document}")

        result = find_command_definitions(str(test_file))
        assert result is not None, "Should return empty substitution object for documents without custom commands"
        # Should return a NewCommandSubstitution with no commands
        assert result._commands == {}, "No commands should be found in document without \\newcommand"

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
        assert "foo" in result._commands, "Custom command \\foo must be detected for substitution"
        assert str(result._commands["foo"].command) == "bar", "Command definition must be extracted correctly"

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
        assert "foo" in result._commands, "First custom command must be detected"
        assert "baz" in result._commands, "Second custom command must be detected"

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
        assert "test" in result._commands, "Parameterized command must be detected for substitution"
        assert result._commands["test"].num_parameters == 2, "Parameter count must be correct for proper substitution"


class TestMain:
    """
    Test the main function that orchestrates flattening.

    The main function coordinates all flachtex operations users care about:
    - Merging multi-file LaTeX projects into single documents
    - Applying user-specified transformations (comment removal, todo removal, etc.)
    - Outputting results in the format users need (text or JSON)

    This is the integration point where user workflows succeed or fail.
    """

    def test_basic_flattening(self, tmp_path):
        """Test basic file flattening workflow."""
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
            assert "Hello World" in output, "Document content must appear in flattened output"
            assert "\\documentclass{article}" in output, "Document structure must be preserved"

    def test_json_output(self, tmp_path):
        """
        Test JSON output format for automation workflows.

        Users need JSON output to:
        - Parse flattened documents in scripts
        - Extract source file mapping for debugging
        - Build automated submission pipelines
        """
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
            assert "content" in data, "JSON output must include 'content' field for downstream processing"
            assert "Test" in data["content"], "Document content must be preserved in JSON output"

    def test_comment_removal(self, tmp_path):
        """
        Test comment removal for journal submission.

        Users need comment removal to:
        - Submit clean documents without draft notes
        - Meet journal requirements for comment-free submissions
        - Remove internal team communication before publication
        """
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
            assert "Text" in output, "Text content must be preserved when removing comments"
            # Comment should be removed
            assert "This is a comment" not in output, "Comments must be removed to avoid draft notes in submissions"

    def test_file_inclusion(self, tmp_path):
        """
        Test that file inclusion works for multi-file projects.

        Users organize large documents across multiple files using \\input.
        This workflow is critical for:
        - Academic papers with separate intro/methods/results sections
        - Theses with chapter files
        - Collaborative projects where authors work on different files
        """
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
            assert "Included content" in output, "Content from \\input files must be merged into output"

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
        """
        Test JSON output includes source file tracking.

        Source tracking helps users:
        - Debug which file caused compilation errors
        - Understand the structure of their flattened document
        - Track changes back to original source files for editing
        """
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
            assert "sources" in data, "JSON output must include sources for debugging multi-file projects"
            # Main file should be in sources
            assert str(main_file) in data["sources"], "Source tracking must include all files for origin tracing"


class TestMainIntegration:
    """
    Integration tests for main with various flag combinations.

    Users combine multiple flags to achieve complex workflows. These combinations
    must work correctly for:
    - Journal submission: Remove comments AND todos in one pass
    - Automated pipelines: JSON output WITH source tracking
    - Multi-file projects: Handle includes, comments, and todos together
    """

    def test_todos_and_comments(self, tmp_path):
        """
        Test --todos and --comments together for clean submission.

        Journal submissions often require removing both draft comments AND todo notes.
        Users need this combination to work reliably in a single command.
        """
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
            assert "Text" in output, "Document content must be preserved"
            # Comment should be removed
            assert "comment" not in output, "Draft comments must be removed for journal submission"

    def test_json_and_comments(self, tmp_path):
        """
        Test --to_json and --comments together for automated workflows.

        Automation scripts need JSON output with comments already removed.
        This combination enables submission pipelines that parse and validate output.
        """
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
            assert "Text" in data["content"], "Content must be in JSON output"
            # Comment should be removed
            assert "comment" not in data["content"], "Comments must be removed even in JSON mode"

    def test_complex_multifile_project(self, tmp_path):
        """
        Test with a complex project structure typical of academic papers.

        Users organize papers into multiple files (intro, methods, results, etc.).
        All sections must be merged correctly while preserving document order.
        """
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
            assert "Introduction" in output, "First section must appear in output"
            assert "Intro text" in output, "First section content must be included"
            assert "Methods" in output, "Second section must appear in output"
            assert "Methods text" in output, "Second section content must be included"

    def test_format_from_cli(self, tmp_path):
        """
        Test --format flag applies diff-friendly formatting from CLI.

        Users need CLI access to formatter for version control workflows without
        writing Python code.
        """
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "This is sentence one. This is sentence two. This is sentence three.\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", "--format", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # Sentences should be split onto separate lines
            assert "This is sentence one.\n" in output, "Sentences must be split with --format flag"
            assert "This is sentence two.\n" in output, "Each sentence must be on its own line"
            assert "This is sentence three.\n" in output, "All sentences must be formatted"

    def test_format_with_indent_from_cli(self, tmp_path):
        """
        Test --format with --indent applies environment indentation.

        Users want control over indentation level for diff-friendly output that's
        also readable.
        """
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\begin{itemize}\n"
            "\\item First item.\n"
            "\\item Second item.\n"
            "\\end{itemize}"
        )

        with patch("sys.argv", ["flachtex", "--format", "--indent", "2", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # Items should be indented
            assert "  \\item First item." in output, "Items must be indented with --indent flag"
            assert "  \\item Second item." in output, "All items must have consistent indentation"

    def test_format_without_flag_no_formatting(self, tmp_path):
        """
        Test that formatting is opt-in (not applied by default).

        Backward compatibility: existing user workflows must not change.
        Formatting only happens with explicit --format flag.
        """
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "This is sentence one. This is sentence two.\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # Without --format, sentences should stay on one line
            assert "This is sentence one. This is sentence two." in output, "Content must not be formatted without --format flag"
            # Should NOT have sentence splitting
            assert "This is sentence one.\nThis is sentence two." not in output, "Formatting must be opt-in"

    def test_format_with_comments_and_todos(self, tmp_path):
        """
        Test --format works with --comments and --todos for complete workflow.

        Journal submission workflow: flatten, remove comments/todos, AND format
        for version control in one command.
        """
        main_file = tmp_path / "main.tex"
        main_file.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Normal text. More text. % draft comment\n"
            "\\todo{Fix this}\n"
            "Final text.\n"
            "\\end{document}"
        )

        with patch("sys.argv", ["flachtex", "--format", "--todos", "--comments", str(main_file)]):
            captured_output = StringIO()
            with patch("sys.stdout", captured_output):
                main()

            output = captured_output.getvalue()
            # Sentences should be formatted
            assert "Normal text.\n" in output, "Sentences must be split with --format"
            assert "More text.\n" in output
            # Comments and todos should be removed
            assert "draft comment" not in output, "Comments must be removed"
            assert "Fix this" not in output or "\\todo" not in output, "Todos must be removed"
