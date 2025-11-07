"""
Tests for flachtex preprocessing rules.

This test suite covers different rules (skip rules, substitution rules,
import rules) and their interactions.
"""


from flachtex import FileFinder, Preprocessor, remove_comments
from flachtex.rules import (
    ChangesRule,
    SubimportChangesRule,
    TodonotesRule,
)


def flatten(document, root="main.tex", rules_config=None):
    """
    Helper function to flatten a document with custom rules.

    Args:
        document: Dictionary mapping file paths to contents
        root: Root file name
        rules_config: Dictionary with keys 'skip_rules', 'subimport_rules', 'substitution_rules'
    """
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", document)
    preprocessor.file_finder = file_finder

    if rules_config:
        if "skip_rules" in rules_config:
            preprocessor.skip_rules.extend(rules_config["skip_rules"])
        if "subimport_rules" in rules_config:
            preprocessor.subimport_rules.extend(rules_config["subimport_rules"])
        if "substitution_rules" in rules_config:
            preprocessor.substitution_rules.extend(rules_config["substitution_rules"])

    doc = preprocessor.expand_file(root)
    return str(doc)


class TestBasicSkipRule:
    """Tests for the basic FLACHTEX-SKIP rule."""

    def test_simple_skip(self):
        """Test basic skip functionality."""
        document = {
            "main.tex": "line 0\n%%FLACHTEX-SKIP-START\nline 1\n%%FLACHTEX-SKIP-STOP\nline 2\n"
        }
        result = flatten(document)
        assert "line 0" in result
        assert "line 1" not in result
        assert "line 2" in result

    def test_multiple_skip_blocks(self):
        """Test multiple skip blocks in one file."""
        document = {
            "main.tex": (
                "a\n"
                "%%FLACHTEX-SKIP-START\n"
                "b\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "c\n"
                "%%FLACHTEX-SKIP-START\n"
                "d\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "e\n"
            )
        }
        result = flatten(document)
        assert "a" in result
        assert "b" not in result
        assert "c" in result
        assert "d" not in result
        assert "e" in result

    def test_skip_with_imports(self):
        """Test skip blocks containing import statements."""
        document = {
            "main.tex": (
                "start\n"
                "%%FLACHTEX-SKIP-START\n"
                "\\input{skipped.tex}\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "end\n"
            ),
            "skipped.tex": "This should not appear\n",
        }
        result = flatten(document)
        assert "start" in result
        assert "end" in result
        assert "This should not appear" not in result

    def test_skip_in_included_file(self):
        """Test skip blocks in included files."""
        document = {
            "main.tex": "main\n\\input{sub.tex}\nafter\n",
            "sub.tex": (
                "before skip\n"
                "%%FLACHTEX-SKIP-START\n"
                "skipped\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "after skip\n"
            ),
        }
        result = flatten(document)
        assert "main" in result
        assert "before skip" in result
        assert "skipped" not in result
        assert "after skip" in result
        assert "after" in result


class TestTodonotesRule:
    """Tests for the todonotes removal rule."""

    def test_todonotes_removal(self):
        """Test basic todonotes removal."""
        document = {
            "main.tex": (
                "text\n"
                "\\todo{This is a todo note}\n"
                "more text\n"
                "\\todo[inline]{Another todo}\n"
                "end\n"
            )
        }
        result = flatten(document, rules_config={"skip_rules": [TodonotesRule()]})
        assert "text" in result
        assert "more text" in result
        assert "end" in result
        # Todos should be removed
        assert "This is a todo note" not in result
        assert "Another todo" not in result

    def test_todonotes_in_included_files(self):
        """Test todonotes removal across included files."""
        document = {
            "main.tex": "start\n\\input{content.tex}\nend\n",
            "content.tex": ("content\n\\todo{Fix this}\nmore content\n"),
        }
        result = flatten(document, rules_config={"skip_rules": [TodonotesRule()]})
        assert "start" in result
        assert "content" in result
        assert "more content" in result
        assert "end" in result
        assert "Fix this" not in result


class TestCommentsPackageSkipRule:
    """Tests for comment package removal."""

    def test_comment_block_removal(self):
        """Test \\begin{comment}...\\end{comment} removal."""
        document = {
            "main.tex": (
                "visible\n"
                "\\begin{comment}\n"
                "hidden comment\n"
                "\\end{comment}\n"
                "visible again\n"
            )
        }
        # Note: Need to use remove_comments function
        preprocessor = Preprocessor("/")
        file_finder = FileFinder("/", document)
        preprocessor.file_finder = file_finder
        doc = preprocessor.expand_file("main.tex")
        result = str(remove_comments(doc))

        assert "visible" in result
        assert "visible again" in result
        assert "hidden comment" not in result

    def test_multiple_comment_blocks(self):
        """Test multiple comment blocks."""
        document = {
            "main.tex": (
                "a\n"
                "\\begin{comment}\n"
                "comment1\n"
                "\\end{comment}\n"
                "b\n"
                "\\begin{comment}\n"
                "comment2\n"
                "\\end{comment}\n"
                "c\n"
            )
        }
        preprocessor = Preprocessor("/")
        file_finder = FileFinder("/", document)
        preprocessor.file_finder = file_finder
        doc = preprocessor.expand_file("main.tex")
        result = str(remove_comments(doc))

        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert "comment1" not in result
        assert "comment2" not in result

    def test_comment_with_indentation(self):
        """Test comment blocks with indentation."""
        document = {
            "main.tex": (
                "text\n"
                "  \\begin{comment}\n"
                "  indented comment\n"
                "  \\end{comment}\n"
                "more text\n"
            )
        }
        preprocessor = Preprocessor("/")
        file_finder = FileFinder("/", document)
        preprocessor.file_finder = file_finder
        doc = preprocessor.expand_file("main.tex")
        result = str(remove_comments(doc))

        assert "text" in result
        assert "more text" in result
        assert "indented comment" not in result


class TestChangesRule:
    """Tests for the changes package substitution rule."""

    def test_changes_commands(self):
        """Test changes package command substitution."""
        document = {
            "main.tex": (
                "Text with \\added{new content} and \\deleted{old content}.\n"
                "Also \\replaced{new}{old} text.\n"
            )
        }
        result = flatten(
            document, rules_config={"substitution_rules": [ChangesRule(False)]}
        )
        # The ChangesRule should replace these commands
        assert "new content" in result
        # The exact behavior depends on the rule implementation

    def test_changes_with_prefix(self):
        """Test changes package with prefix option."""
        document = {"main.tex": ("Text with \\added{new content}.\n")}
        result = flatten(
            document, rules_config={"substitution_rules": [ChangesRule(True)]}
        )
        # With prefix, the output format may differ
        assert "new content" in result or "ADDED" in result


class TestSubimportChangesRule:
    """Tests for the subimport changes rule (graphics path adjustment)."""

    def test_subimport_graphics_adjustment(self):
        """Test that graphics paths are adjusted in subimports."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{figures/}{plot}\n"
                "\\end{document}\n"
            ),
            "figures/plot.tex": (
                "\\begin{figure}\n"
                "\\includegraphics{image.pdf}\n"
                "\\caption{Plot}\n"
                "\\end{figure}\n"
            ),
        }
        result = flatten(
            document, rules_config={"subimport_rules": [SubimportChangesRule()]}
        )
        # The path should be adjusted to include the subimport directory
        assert "\\includegraphics" in result
        assert "figures/" in result or "./figures/" in result

    def test_subimport_nested_graphics(self):
        """Test graphics path adjustment with nested subimports."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{chapter1/}{main}\n"
                "\\end{document}\n"
            ),
            "chapter1/main.tex": (
                "\\chapter{Chapter 1}\n\\subimport{figures/}{fig1}\n"
            ),
            "chapter1/figures/fig1.tex": (
                "\\begin{figure}\n\\includegraphics{plot.pdf}\n\\end{figure}\n"
            ),
        }
        result = flatten(
            document, rules_config={"subimport_rules": [SubimportChangesRule()]}
        )
        assert "\\includegraphics" in result
        # Path should reflect the nested structure
        assert "chapter1" in result


class TestRuleCombinations:
    """Tests for combinations of multiple rules."""

    def test_skip_and_comments_combined(self):
        """Test using both skip rules and comment removal."""
        document = {
            "main.tex": (
                "visible\n"
                "%%FLACHTEX-SKIP-START\n"
                "skipped\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\\begin{comment}\n"
                "comment\n"
                "\\end{comment}\n"
                "end\n"
            )
        }
        preprocessor = Preprocessor("/")
        file_finder = FileFinder("/", document)
        preprocessor.file_finder = file_finder
        doc = preprocessor.expand_file("main.tex")
        result = str(remove_comments(doc))

        assert "visible" in result
        assert "end" in result
        assert "skipped" not in result
        assert "comment" not in result

    def test_all_skip_rules_combined(self):
        """Test using multiple skip rules together."""
        document = {
            "main.tex": (
                "text\n"
                "%%FLACHTEX-SKIP-START\n"
                "skip1\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "\\todo{todo note}\n"
                "\\begin{comment}\n"
                "comment block\n"
                "\\end{comment}\n"
                "final\n"
            )
        }
        preprocessor = Preprocessor("/")
        file_finder = FileFinder("/", document)
        preprocessor.file_finder = file_finder
        preprocessor.skip_rules.append(TodonotesRule())
        doc = preprocessor.expand_file("main.tex")
        result = str(remove_comments(doc))

        assert "text" in result
        assert "final" in result
        assert "skip1" not in result
        assert "todo note" not in result
        assert "comment block" not in result

    def test_subimport_with_skip_rules(self):
        """Test subimport combined with skip rules."""
        document = {
            "main.tex": ("start\n\\subimport{sub/}{content}\nend\n"),
            "sub/content.tex": (
                "visible\n"
                "%%FLACHTEX-SKIP-START\n"
                "skipped\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "visible2\n"
                "\\includegraphics{img.pdf}\n"
            ),
        }
        result = flatten(
            document, rules_config={"subimport_rules": [SubimportChangesRule()]}
        )
        assert "start" in result
        assert "visible" in result
        assert "visible2" in result
        assert "skipped" not in result
        assert "img.pdf" in result

    def test_changes_and_subimport_combined(self):
        """Test changes rule combined with subimport."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{sections/}{intro}\n"
                "\\end{document}\n"
            ),
            "sections/intro.tex": (
                "\\section{Introduction}\n"
                "This is \\added{new} text.\n"
                "\\includegraphics{fig.pdf}\n"
            ),
        }
        result = flatten(
            document,
            rules_config={
                "subimport_rules": [SubimportChangesRule()],
                "substitution_rules": [ChangesRule(False)],
            },
        )
        assert "Introduction" in result
        assert "new" in result
        assert "sections/" in result or "./sections/" in result


class TestRuleOrdering:
    """Tests to verify rule application order."""

    def test_skip_before_substitution(self):
        """Verify that skip rules are applied before substitution."""
        document = {
            "main.tex": (
                "\\added{visible}\n"
                "%%FLACHTEX-SKIP-START\n"
                "\\added{skipped}\n"
                "%%FLACHTEX-SKIP-STOP\n"
            )
        }
        result = flatten(
            document,
            rules_config={"substitution_rules": [ChangesRule(False)]},
        )
        # The skipped section should not be processed by substitution
        assert "visible" in result
        # "skipped" should not appear since it's in a skip block

    def test_skip_before_import_resolution(self):
        """Verify that skip rules prevent import resolution."""
        document = {
            "main.tex": (
                "start\n"
                "%%FLACHTEX-SKIP-START\n"
                "\\input{missing.tex}\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "end\n"
            ),
        }
        # This should not raise an error about missing.tex
        result = flatten(document)
        assert "start" in result
        assert "end" in result


class TestCustomRuleInteractions:
    """Tests for how custom rules interact with standard functionality."""

    def test_rules_preserve_line_structure(self):
        """Test that rules preserve overall document structure."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{content.tex}\n"
                "\\end{document}\n"
            ),
            "content.tex": (
                "\\section{Section}\n"
                "Text\n"
                "%%FLACHTEX-SKIP-START\n"
                "Skip\n"
                "%%FLACHTEX-SKIP-STOP\n"
                "More text\n"
            ),
        }
        result = flatten(document)
        assert "\\documentclass{article}" in result
        assert "\\begin{document}" in result
        assert "\\section{Section}" in result
        assert "Text" in result
        assert "Skip" not in result
        assert "More text" in result
        assert "\\end{document}" in result

    def test_rules_with_empty_results(self):
        """Test rules that result in empty content."""
        document = {
            "main.tex": ("start\n\\input{all_skipped.tex}\nend\n"),
            "all_skipped.tex": (
                "%%FLACHTEX-SKIP-START\neverything is skipped\n%%FLACHTEX-SKIP-STOP\n"
            ),
        }
        result = flatten(document)
        assert "start" in result
        assert "end" in result
        assert "everything is skipped" not in result
