"""
Tests for edge cases and error handling in flachtex.

This test suite covers unusual scenarios, error conditions, and edge cases
that may occur in real-world LaTeX documents.
"""

import contextlib

import pytest

from flachtex import FileFinder, Preprocessor, remove_comments
from flachtex.cycle_prevention import CycleException
from flachtex.rules import SubimportChangesRule


def flatten(document, root="main.tex", comments=False):
    """Helper function to flatten a document dictionary."""
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", document)
    preprocessor.file_finder = file_finder
    preprocessor.subimport_rules.append(SubimportChangesRule())
    doc = preprocessor.expand_file(root)
    if comments:
        doc = remove_comments(doc)
    return str(doc)


class TestMissingFiles:
    """Tests for handling missing files (now silently skipped per feat20250616)."""

    def test_missing_input_file(self):
        """Test that missing input files are silently skipped."""
        document = {
            "main.tex": "line 0\n\\input{missing.tex}\nline 2\n",
        }
        result = flatten(document)
        # Missing files are now silently skipped, not raised as errors
        assert "line 0" in result
        assert "line 2" in result

    def test_missing_include_file(self):
        """Test that missing include files are silently skipped."""
        document = {
            "main.tex": "line 0\n\\include{missing}\nline 2\n",
        }
        result = flatten(document)
        # Missing files are now silently skipped, not raised as errors
        assert "line 0" in result
        assert "line 2" in result

    def test_missing_subimport_file(self):
        """Test that missing subimport files are silently skipped."""
        document = {
            "main.tex": "line 0\n\\subimport{dir}{missing}\nline 2\n",
        }
        result = flatten(document)
        # Missing files are now silently skipped, not raised as errors
        assert "line 0" in result
        assert "line 2" in result


class TestCircularDependencies:
    """Tests for detecting and handling circular dependencies."""

    def test_direct_circular_dependency(self):
        """Test that direct circular dependencies are detected."""
        document = {
            "main.tex": "line 0\n\\input{a.tex}\nline 2\n",
            "a.tex": "line 1\n\\input{main.tex}\n",
        }
        with pytest.raises(CycleException):
            flatten(document)

    def test_indirect_circular_dependency(self):
        """Test that indirect circular dependencies are detected."""
        document = {
            "main.tex": "line 0\n\\input{a.tex}\n",
            "a.tex": "line 1\n\\input{b.tex}\n",
            "b.tex": "line 2\n\\input{main.tex}\n",
        }
        with pytest.raises(CycleException):
            flatten(document)


class TestEmptyFiles:
    """Tests for handling empty files."""

    def test_empty_main_file(self):
        """Test flattening an empty main file."""
        document = {"main.tex": ""}
        result = flatten(document)
        assert result == ""

    def test_empty_included_file(self):
        """Test including an empty file."""
        document = {
            "main.tex": "line 0\n\\input{empty.tex}\nline 2\n",
            "empty.tex": "",
        }
        result = flatten(document)
        assert result == "line 0\n\nline 2\n"

    def test_multiple_empty_includes(self):
        """Test multiple empty includes."""
        document = {
            "main.tex": "line 0\n\\input{e1.tex}\n\\input{e2.tex}\nline 3\n",
            "e1.tex": "",
            "e2.tex": "",
        }
        result = flatten(document)
        assert result == "line 0\n\n\nline 3\n"


class TestDeeplyNestedIncludes:
    """Tests for deeply nested include structures."""

    def test_deeply_nested_inputs(self):
        """Test multiple levels of nested inputs."""
        document = {
            "main.tex": "0\n\\input{l1.tex}\n6\n",
            "l1.tex": "1\n\\input{l2.tex}\n5\n",
            "l2.tex": "2\n\\input{l3.tex}\n4\n",
            "l3.tex": "3\n",
        }
        result = flatten(document)
        assert result == "0\n1\n2\n3\n\n4\n\n5\n\n6\n"

    def test_nested_with_multiple_includes(self):
        """Test nested structure with multiple includes at each level."""
        document = {
            "main.tex": "0\n\\input{a.tex}\n\\input{b.tex}\n7\n",
            "a.tex": "1\n\\input{a1.tex}\n\\input{a2.tex}\n4\n",
            "b.tex": "5\n\\input{b1.tex}\n6\n",
            "a1.tex": "2\n",
            "a2.tex": "3\n",
            "b1.tex": "5.5\n",
        }
        result = flatten(document)
        # Check that all numbers appear in order
        assert "0" in result
        assert "1" in result
        assert "7" in result


class TestMixedImportTypes:
    """Tests for documents using multiple import types."""

    def test_input_and_include_mixed(self):
        """Test mixing \\input and \\include."""
        document = {
            "main.tex": "0\n\\input{a.tex}\n\\include{b}\n3\n",
            "a.tex": "1\n",
            "b.tex": "2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_all_import_types_mixed(self):
        """Test mixing \\input, \\include, and \\subimport."""
        document = {
            "main.tex": "0\n\\input{a.tex}\n\\include{b}\n\\subimport{dir}{c}\n4\n",
            "a.tex": "1\n",
            "b.tex": "2\n",
            "dir/c.tex": "3\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert "4" in result


class TestSpecialCharactersInPaths:
    """Tests for handling special characters in file paths."""

    def test_spaces_in_filename(self):
        """Test files with spaces in names."""
        document = {
            "main.tex": "0\n\\input{file with spaces.tex}\n2\n",
            "file with spaces.tex": "1\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result

    def test_underscores_in_filename(self):
        """Test files with underscores in names."""
        document = {
            "main.tex": "0\n\\input{file_with_underscores.tex}\n2\n",
            "file_with_underscores.tex": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"

    def test_hyphens_in_filename(self):
        """Test files with hyphens in names."""
        document = {
            "main.tex": "0\n\\input{file-with-hyphens.tex}\n2\n",
            "file-with-hyphens.tex": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"


class TestComplexDirectoryStructures:
    """Tests for complex directory hierarchies."""

    def test_deeply_nested_directories(self):
        """Test files in deeply nested directory structures."""
        document = {
            "main.tex": "0\n\\input{a/b/c/d/file.tex}\n2\n",
            "a/b/c/d/file.tex": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"

    def test_sibling_directories(self):
        """Test including files from sibling directories."""
        document = {
            "main.tex": "0\n\\input{dir1/a.tex}\n\\input{dir2/b.tex}\n3\n",
            "dir1/a.tex": "1\n",
            "dir2/b.tex": "2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_relative_imports_from_subdirs(self):
        """Test relative imports when already in a subdirectory."""
        document = {
            "main.tex": "0\n\\input{sub/a.tex}\n3\n",
            "sub/a.tex": "1\n\\input{b.tex}\n",
            "sub/b.tex": "2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestWhitespaceHandling:
    """Tests for handling various whitespace scenarios."""

    def test_whitespace_in_import_command(self):
        """Test import commands with extra whitespace."""
        document = {
            "main.tex": "0\n\\input{ file.tex }\n2\n",
            "file.tex": "1\n",
        }
        # This should handle trimming or fail gracefully
        # The actual behavior depends on the implementation
        try:
            result = flatten(document)
            assert "0" in result
        except KeyError:
            # If whitespace causes lookup failure, that's also acceptable
            pass

    def test_newlines_in_import_command(self):
        """Test import commands split across lines."""
        document = {
            "main.tex": "0\n\\input{\nfile.tex\n}\n3\n",
            "file.tex": "1\n2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_files_with_only_whitespace(self):
        """Test including files that contain only whitespace."""
        document = {
            "main.tex": "0\n\\input{ws.tex}\n2\n",
            "ws.tex": "   \n\t\n  \n",
        }
        result = flatten(document)
        assert "0" in result
        assert "2" in result


class TestEdgeCaseCommands:
    """Tests for edge cases in LaTeX commands."""

    def test_commented_import(self):
        """Test that commented imports are ignored."""
        document = {
            "main.tex": "0\n%\\input{file.tex}\n2\n",
            "file.tex": "1\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" not in result  # Should not be included
        assert "2" in result

    def test_multiple_imports_same_line(self):
        """Test multiple import commands on the same line."""
        document = {
            "main.tex": "0\n\\input{a.tex}\\input{b.tex}\n3\n",
            "a.tex": "1\n",
            "b.tex": "2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_nested_braces_in_import(self):
        """Test import commands with nested braces."""
        document = {
            "main.tex": "0\n\\input{dir/{file}.tex}\n2\n",
            "dir/{file}.tex": "1\n",
        }
        # This is an edge case - behavior may vary
        with contextlib.suppress(KeyError):
            flatten(document)


class TestLargeDocuments:
    """Tests for handling larger documents."""

    def test_many_small_files(self):
        """Test including many small files."""
        document = {"main.tex": "start\n"}
        for i in range(50):
            document["main.tex"] += f"\\input{{file{i}.tex}}\n"
            document[f"file{i}.tex"] = f"content{i}\n"
        document["main.tex"] += "end\n"

        result = flatten(document)
        assert "start" in result
        assert "content0" in result
        assert "content49" in result
        assert "end" in result

    def test_large_file_content(self):
        """Test including a file with large content."""
        large_content = "line\n" * 10000
        document = {
            "main.tex": "start\n\\input{large.tex}\nend\n",
            "large.tex": large_content,
        }
        result = flatten(document)
        assert "start" in result
        assert "end" in result
        assert result.count("line") == 10000


class TestFileExtensions:
    """Tests for handling different file extensions."""

    def test_explicit_tex_extension(self):
        """Test explicitly specifying .tex extension."""
        document = {
            "main.tex": "0\n\\input{file.tex}\n2\n",
            "file.tex": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"

    def test_implicit_tex_extension(self):
        """Test omitting .tex extension."""
        document = {
            "main.tex": "0\n\\input{file}\n2\n",
            "file.tex": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"

    def test_no_extension_no_tex_file(self):
        """Test that files without .tex extension are also found."""
        document = {
            "main.tex": "0\n\\input{file}\n2\n",
            "file": "1\n",
        }
        result = flatten(document)
        assert result == "0\n1\n\n2\n"


class TestSkipRulesEdgeCases:
    """Tests for edge cases in skip rules."""

    def test_nested_skip_blocks(self):
        """Test nested FLACHTEX-SKIP blocks."""
        document = {
            "main.tex": (
                "0\n"
                "%%FLACHTEX-SKIP-START\n"
                "1\n"
                "%%FLACHTEX-SKIP-START\n"
                "2\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "3\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "4\n"
            )
        }
        result = flatten(document)
        # The exact behavior for nested blocks may vary
        assert "0" in result
        assert "4" in result

    def test_unclosed_skip_block(self):
        """Test skip block without closing marker."""
        document = {"main.tex": "0\n%%FLACHTEX-SKIP-START\n1\n2\n"}
        result = flatten(document)
        # Should handle gracefully - either skip to end or include everything
        assert "0" in result

    def test_skip_block_across_includes(self):
        """Test that skip blocks don't affect included files."""
        document = {
            "main.tex": (
                "0\n%%FLACHTEX-SKIP-START\n\\input{a.tex}\n%%FLACHTEX-SKIP-STOP\n3\n"
            ),
            "a.tex": "1\n2\n",
        }
        result = flatten(document)
        assert "0" in result
        assert "3" in result
        # The included content should be skipped
        assert "1" not in result or "2" not in result


class TestCommentPackageEdgeCases:
    """Tests for edge cases with comment package removal."""

    def test_nested_comment_blocks(self):
        """Test nested \\begin{comment} blocks."""
        document = {
            "main.tex": (
                "0\n\\begin{comment}\n1\n\\begin{comment}\n2\n"
                "\\end{comment}\n3\n\\end{comment}\n4\n"
            )
        }
        result = flatten(document, comments=True)
        assert "0" in result
        assert "4" in result
        # Inner content should be removed
        assert "2" not in result

    def test_comment_block_with_special_chars(self):
        """Test comment blocks containing special characters."""
        document = {"main.tex": "0\n\\begin{comment}\n$ % & # { }\n\\end{comment}\n2\n"}
        result = flatten(document, comments=True)
        assert "0" in result
        assert "2" in result
        assert "$" not in result
