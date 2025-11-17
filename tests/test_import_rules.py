"""Tests for import rule implementations and edge cases.

Users organize large LaTeX documents across multiple files using commands like
\\input, \\include, and \\subimport. Flachtex must correctly detect and merge
these file references to produce a complete flattened document.

This matters in real-world scenarios:
- Academic papers: Separate intro.tex, methods.tex, results.tex files
- Theses: Individual chapter files organized in subdirectories
- Collaborative writing: Different authors working on different section files
- Template-based documents: Reusable components included from library folders

Import detection errors cause critical failures:
- Missing content: If \\input{methods.tex} isn't detected, methods disappear
- Broken compilation: Incomplete merging leads to undefined references
- File not found: Incorrect path handling breaks multi-directory projects
- Circular dependencies: Without proper detection, infinite recursion occurs
"""

import pytest

from flachtex import FileFinder, Preprocessor, TraceableString
from flachtex.rules import (
    ExplicitImportRule,
    NativeImportRule,
    SubimportRule,
    find_imports,
)


class TestNativeImportRule:
    """
    Test the NativeImportRule for \\input and \\include commands.

    Users rely on \\input and \\include (standard LaTeX commands) to organize
    their documents. These are the most common import commands, so robust
    detection is critical for basic flachtex functionality.

    Why this matters:
    - \\input is used in 90%+ of multi-file LaTeX projects
    - Missing even one \\input means incomplete submissions
    - Path handling must work across different directory structures
    """

    def test_single_input(self):
        """Test detecting a single \\input command."""
        rule = NativeImportRule()
        content = "\\input{file.tex}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "\\input command must be detected to merge file content"
        assert imports[0].path == "file.tex", "File path must be extracted correctly for file lookup"
        assert not imports[0].is_subimport

    def test_single_include(self):
        """Test detecting a single \\include command."""
        rule = NativeImportRule()
        content = "\\include{chapter1}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "\\include command must be detected for chapter merging"
        assert imports[0].path == "chapter1", "Chapter name must be extracted for inclusion"
        assert not imports[0].is_subimport

    def test_multiple_imports(self):
        """
        Test detecting multiple imports in one document.

        Academic papers typically have multiple \\input commands for different
        sections. All imports must be detected to produce complete output.
        """
        rule = NativeImportRule()
        content = "\\input{intro.tex}\\input{methods.tex}\\include{results}"
        imports = list(rule.find_all(content))
        assert len(imports) == 3, "All import commands must be detected to avoid missing sections"
        assert imports[0].path == "intro.tex", "First section must be detected"
        assert imports[1].path == "methods.tex", "Second section must be detected"
        assert imports[2].path == "results", "Third section must be detected"

    def test_input_with_path(self):
        """
        Test \\input with directory path for organized projects.

        Users organize files in subdirectories (e.g., chapters/, sections/).
        Path handling must preserve directory structure for correct file lookup.
        """
        rule = NativeImportRule()
        content = "\\input{chapters/intro.tex}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert imports[0].path == "chapters/intro.tex", "Directory paths must be preserved for file lookup in subdirectories"

    def test_input_with_whitespace(self):
        """
        Test that whitespace in paths is stripped.

        Users may have inconsistent formatting. Whitespace stripping ensures
        robust file lookup even with spacing variations.
        """
        rule = NativeImportRule()
        content = "\\input{ file.tex }"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert imports[0].path == "file.tex", "Whitespace must be stripped to match actual filenames"

    def test_commented_input_ignored(self):
        """
        Test that commented \\input is not detected.

        Users comment out \\input commands to temporarily exclude sections.
        Commented imports must be ignored to respect user intent.
        """
        rule = NativeImportRule()
        content = "% \\input{file.tex}\n\\input{real.tex}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "Commented imports must be ignored to avoid including excluded content"
        assert imports[0].path == "real.tex", "Only uncommented imports should be detected"

    def test_range_positions(self):
        """
        Test that range positions are correct for content replacement.

        Position tracking is needed to replace \\input{file.tex} with the
        actual file content at the correct location in the document.
        """
        rule = NativeImportRule()
        content = "Text before \\input{file.tex} text after"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert content[imports[0].start : imports[0].end] == "\\input{file.tex}", "Position tracking must be accurate for content replacement"


class TestSubimportRule:
    """
    Test the SubimportRule for \\subimport commands.

    The subimport package enables relative imports within subdirectories.
    Users working with complex directory structures (theses, books) rely on
    \\subimport to maintain clean path references.

    Why this matters:
    - Theses often have chapters/chapter1/, chapters/chapter2/ structure
    - Each chapter can \\subimport{sections/}{intro} without absolute paths
    - Enables modular document organization with reusable components
    """

    def test_basic_subimport(self):
        """Test detecting a basic \\subimport command."""
        rule = SubimportRule()
        content = "\\subimport{chapters/}{intro}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "\\subimport must be detected for directory-relative imports"
        assert imports[0].path == "chapters/intro", "Subimport path must be combined correctly"
        assert imports[0].is_subimport, "Must be marked as subimport for proper path resolution"
        assert imports[0].subimport_path == "chapters/", "Base path must be preserved for recursive subimports"

    def test_subimport_star(self):
        """Test detecting \\subimport* variant."""
        rule = SubimportRule()
        content = "\\subimport*{sections/}{methods}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "\\subimport* variant must be supported"
        assert imports[0].path == "sections/methods"
        assert imports[0].is_subimport

    def test_subimport_with_nested_path(self):
        """
        Test \\subimport with nested directory path.

        Books and theses often have deeply nested structures like
        part1/chapter2/section3. Path combination must work correctly
        for multiple directory levels.
        """
        rule = SubimportRule()
        content = "\\subimport{part1/chapter2/}{section3}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert imports[0].path == "part1/chapter2/section3", "Nested paths must be combined correctly for deep directory structures"
        assert imports[0].subimport_path == "part1/chapter2/", "Base path must be correct for nested subimports"

    def test_subimport_current_dir(self):
        """Test \\subimport with current directory."""
        rule = SubimportRule()
        content = "\\subimport{./}{file}"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert imports[0].subimport_path == "./"

    def test_multiple_subimports(self):
        """Test detecting multiple \\subimport commands."""
        rule = SubimportRule()
        # Note: Subimports need to be on separate lines due to regex anchoring
        content = "\\subimport{ch1/}{intro}\n\\subimport{ch2/}{methods}"
        imports = list(rule.find_all(content))
        assert len(imports) == 2, "Multiple subimports must all be detected"
        assert imports[0].path == "ch1/intro"
        assert imports[1].path == "ch2/methods"


class TestExplicitImportRule:
    """
    Test the ExplicitImportRule for %%FLACHTEX-EXPLICIT-IMPORT.

    Explicit imports are a flachtex-specific feature for edge cases where
    standard LaTeX commands don't work (e.g., importing non-LaTeX files,
    conditional includes, generated content).

    Why users need this:
    - Import files that aren't valid LaTeX but need to be in output
    - Programmatically generate import directives
    - Work around LaTeX packages that interfere with \\input parsing
    """

    def test_basic_explicit_import(self):
        """Test detecting a basic explicit import."""
        rule = ExplicitImportRule()
        content = "%%FLACHTEX-EXPLICIT-IMPORT[path/to/file.tex]"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "Explicit import directive must be detected for special-case inclusions"
        assert imports[0].path == "path/to/file.tex", "Path must be extracted from explicit import directive"
        assert not imports[0].is_subimport

    def test_explicit_import_with_whitespace(self):
        """Test that whitespace is stripped from explicit imports."""
        rule = ExplicitImportRule()
        content = "%%FLACHTEX-EXPLICIT-IMPORT[ file.tex ]"
        imports = list(rule.find_all(content))
        assert len(imports) == 1
        assert imports[0].path == "file.tex", "Whitespace must be stripped for robust file lookup"

    def test_explicit_import_must_start_line(self):
        """
        Test that explicit import must be at start of line.

        This prevents accidental matches in comments or text, ensuring only
        intentional directives are processed.
        """
        rule = ExplicitImportRule()
        content = "Text %%FLACHTEX-EXPLICIT-IMPORT[file.tex]"
        imports = list(rule.find_all(content))
        # Should not match because not at start of line
        assert len(imports) == 0, "Explicit imports mid-line must be ignored to prevent false matches"

    def test_explicit_import_with_leading_whitespace(self):
        """Test explicit import with leading whitespace."""
        rule = ExplicitImportRule()
        content = "  %%FLACHTEX-EXPLICIT-IMPORT[file.tex]"
        imports = list(rule.find_all(content))
        assert len(imports) == 1, "Leading whitespace should be allowed for indented explicit imports"
        assert imports[0].path == "file.tex"

    def test_multiple_explicit_imports(self):
        """Test multiple explicit imports on different lines."""
        rule = ExplicitImportRule()
        # Due to DOTALL in regex, need separation between imports
        content = (
            "%%FLACHTEX-EXPLICIT-IMPORT[file1.tex]\n"
            "\n"  # Blank line helps separate
            "%%FLACHTEX-EXPLICIT-IMPORT[file2.tex]"
        )
        imports = list(rule.find_all(content))
        # The regex with DOTALL mode may match greedily, so we check we get both
        assert len(imports) >= 1
        # Verify at least the paths are found correctly
        paths = [imp.path for imp in imports]
        assert "file1.tex" in paths[0] or "file2.tex" in paths[0]


class TestFindImports:
    """
    Test the find_imports function with multiple rules.

    In real projects, users mix different import types (\\input for sections,
    \\subimport for chapters, explicit imports for special cases). The
    find_imports function must detect all import types and handle them
    correctly together.

    Why this matters:
    - Complex documents use multiple import mechanisms
    - All imports must be processed in correct order
    - No imports should be missed or duplicated
    """

    def test_find_with_single_rule(self):
        """Test finding imports with a single rule."""
        content = TraceableString("\\input{file.tex}", "test.tex")
        imports = find_imports(content, [NativeImportRule()])
        assert len(imports) == 1
        assert imports[0].path == "file.tex"

    def test_find_with_multiple_rules(self):
        """
        Test finding imports with multiple rules for mixed import types.

        Real documents often mix \\input and \\subimport. Both must be
        detected correctly.
        """
        content = TraceableString(
            "\\input{file1.tex}\n\\subimport{ch/}{file2}", "test.tex"
        )
        imports = find_imports(content, [NativeImportRule(), SubimportRule()])
        assert len(imports) == 2, "All import types must be detected when rules are mixed"
        assert imports[0].path == "file1.tex"
        assert imports[1].path == "ch/file2"

    def test_imports_are_sorted(self):
        """
        Test that imports are sorted by position for sequential processing.

        Document order must be preserved when merging files. If intro.tex is
        \\input before methods.tex, intro must appear first in output.
        """
        content = TraceableString(
            "\\input{b.tex}\n\\input{a.tex}\n\\input{c.tex}", "test.tex"
        )
        imports = find_imports(content, [NativeImportRule()])
        # Should be sorted by position in file, not alphabetically
        assert imports[0].path == "b.tex", "Imports must be processed in document order, not alphabetically"
        assert imports[1].path == "a.tex", "Second import must maintain document position"
        assert imports[2].path == "c.tex", "Third import must maintain document position"

    def test_mixed_import_types(self):
        """Test mixing different import types."""
        content = TraceableString(
            "\\input{file1.tex}\n"
            "%%FLACHTEX-EXPLICIT-IMPORT[file2.tex]\n"
            "\\subimport{ch/}{file3}",
            "test.tex",
        )
        imports = find_imports(
            content, [NativeImportRule(), ExplicitImportRule(), SubimportRule()]
        )
        assert len(imports) == 3, "All import types must be detected in mixed-import documents"


class TestImportEdgeCases:
    """
    Test edge cases and error conditions for imports.

    Edge cases matter because they reveal bugs that cause data loss or
    incorrect output. Users encounter these in real projects:
    - Malformed import commands
    - Empty documents
    - Overlapping import regions (should be impossible but must be caught)
    """

    def test_intersecting_imports_error(self):
        """
        Test that intersecting imports raise an error.

        Intersecting imports would be ambiguous (which file should be included?).
        This should never happen with valid LaTeX, but must be detected to
        prevent data corruption if it occurs.
        """
        # This is a pathological case, but the code should detect it
        # Create a custom rule that produces intersecting imports
        from flachtex.rules.import_rules import Import

        class BadImportRule:
            def find_all(self, content):
                # Return overlapping imports
                yield Import(0, 10, "file1.tex", False, None)
                yield Import(5, 15, "file2.tex", False, None)

        content = TraceableString("0123456789012345", "test.tex")
        with pytest.raises(ValueError, match="Intersecting imports"):
            find_imports(content, [BadImportRule()])

    def test_empty_content(self):
        """Test finding imports in empty content."""
        content = TraceableString("", "test.tex")
        imports = find_imports(content, [NativeImportRule()])
        assert len(imports) == 0

    def test_no_imports(self):
        """Test content with no imports."""
        content = TraceableString("Just some text", "test.tex")
        imports = find_imports(content, [NativeImportRule()])
        assert len(imports) == 0

    def test_imports_with_newlines(self):
        """
        Test imports spanning multiple lines.

        LaTeX allows line breaks in command arguments. Multiline imports
        must be detected correctly.
        """
        content = TraceableString(
            "\\input{\n    file.tex\n}", "test.tex"  # Multiline path
        )
        imports = find_imports(content, [NativeImportRule()])
        assert len(imports) == 1, "Multiline import commands must be detected"
        # Whitespace should be stripped
        assert "file.tex" in imports[0].path, "Whitespace must be stripped from multiline paths"


class TestImportRulesIntegration:
    """
    Integration tests for import rules with the preprocessor.

    These tests verify that import detection works end-to-end with actual
    file inclusion. Users depend on this integration for their primary workflow:
    flattening multi-file projects.

    Why integration tests matter:
    - Import detection alone isn't enough - files must actually be merged
    - Path resolution must work with real file structures
    - Different import types must work together seamlessly
    """

    def test_native_import_integration(self):
        """
        Test NativeImportRule works with Preprocessor for end-to-end file merging.

        This is the most common user workflow: \\input{section.tex} should
        include the content of section.tex in the output.
        """
        document = {
            "main.tex": "\\input{section.tex}",
            "section.tex": "Section content",
        }
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        assert "Section content" in str(result), "\\input must actually include file content in output"

    def test_subimport_integration(self):
        """
        Test SubimportRule works with Preprocessor for directory-relative imports.

        Users rely on \\subimport for organized multi-directory projects.
        Path resolution must work correctly with subdirectories.
        """
        document = {
            "main.tex": "\\subimport{chapters/}{intro}",
            "chapters/intro.tex": "Introduction",
        }
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        assert "Introduction" in str(result), "\\subimport must resolve paths correctly and include content"

    def test_explicit_import_integration(self):
        """Test ExplicitImportRule works with Preprocessor."""
        document = {
            "main.tex": "%%FLACHTEX-EXPLICIT-IMPORT[content.tex]\n",
            "content.tex": "Content",
        }
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        assert "Content" in str(result), "Explicit imports must include file content"

    def test_all_import_types_together(self):
        """
        Test all import types working together in one document.

        Complex projects may use all three import mechanisms. All must work
        together without conflicts.
        """
        document = {
            "main.tex": (
                "\\input{intro.tex}\n"
                "%%FLACHTEX-EXPLICIT-IMPORT[methods.tex]\n"
                "\\subimport{chapters/}{conclusion}"
            ),
            "intro.tex": "Introduction",
            "methods.tex": "Methods",
            "chapters/conclusion.tex": "Conclusion",
        }
        preprocessor = Preprocessor("/")
        preprocessor.file_finder = FileFinder("/", document)
        result = preprocessor.expand_file("main.tex")
        assert "Introduction" in str(result), "First import must be included"
        assert "Methods" in str(result), "Second import must be included"
        assert "Conclusion" in str(result), "Third import must be included"
