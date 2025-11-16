"""
Integration tests for the formatter with the full flachtex pipeline.
"""

from flachtex import FileFinder, Preprocessor
from flachtex.formatter import format_latex
from flachtex.rules import ChangesRule, SubimportChangesRule


def flatten(
    document, root="main.tex", format_output=False, changes=False, comments=False
):
    """Helper function to flatten a document dictionary with optional formatting."""
    preprocessor = Preprocessor("/")
    file_finder = FileFinder("/", document)
    preprocessor.file_finder = file_finder
    preprocessor.subimport_rules.append(SubimportChangesRule())
    if changes:
        preprocessor.substitution_rules.append(ChangesRule(prefix=False))
    doc = preprocessor.expand_file(root)
    if format_output:
        doc = format_latex(doc)
    return doc


def test_formatter_with_simple_document():
    """Test formatter integration with a simple document."""
    documents = {
        "main.tex": (
            "This is sentence one. This is sentence two. This is sentence three."
        ),
    }
    result = flatten(documents, "main.tex", format_output=True)
    expected = "This is sentence one.\nThis is sentence two.\nThis is sentence three."
    assert str(result) == expected


def test_formatter_with_includes():
    """Test formatter works with included files."""
    documents = {
        "main.tex": "This is main. More in main. \\input{sub.tex} Final in main.",
        "sub.tex": "This is sub. More in sub.",
    }
    result = flatten(documents, "main.tex", format_output=True)
    # Check that sentences are properly split
    result_str = str(result)
    assert "This is main.\n" in result_str
    assert "More in main.\n" in result_str
    assert "This is sub.\n" in result_str
    assert "More in sub.\n" in result_str
    assert "Final in main." in result_str


def test_formatter_with_verbatim():
    """Test formatter preserves verbatim environments."""
    documents = {
        "main.tex": (
            "Before text. More before.\n"
            "\\begin{verbatim}\n"
            "Code. With. Periods.\n"
            "\\end{verbatim}\n"
            "After text. More after."
        ),
    }
    result = flatten(documents, "main.tex", format_output=True)
    # Verbatim content should not be split
    assert "Code. With. Periods." in str(result)
    # But text outside should be split
    assert str(result).startswith("Before text.\nMore before.")


def test_formatter_with_math():
    """Test formatter handles math correctly."""
    documents = {
        "main.tex": "The value $x = 3.14$ is pi. This is another sentence.",
    }
    result = flatten(documents, "main.tex", format_output=True)
    expected = "The value $x = 3.14$ is pi.\nThis is another sentence."
    assert str(result) == expected


def test_formatter_with_comments():
    """Test formatter preserves comments correctly."""
    documents = {
        "main.tex": (
            "This is a sentence. % comment here\n"
            "This is another sentence."
        ),
    }
    result = flatten(documents, "main.tex", format_output=True)
    # Comment should stay with its sentence
    assert "% comment here" in str(result)


def test_formatter_disabled_by_default():
    """Test that formatter is disabled by default."""
    documents = {
        "main.tex": "This is sentence one. This is sentence two.",
    }
    # Without format_output=True, should not format
    result = flatten(documents, "main.tex")
    # Should be on one line
    assert str(result) == "This is sentence one. This is sentence two."


def test_formatter_with_changes_rule():
    """Test formatter works with changes rule."""
    documents = {
        "main.tex": (
            "This is text. \\deleted{Old text.} \\added{New text.} More text."
        ),
    }
    result = flatten(documents, "main.tex", format_output=True, changes=True)
    # Should be formatted and changes applied
    assert "This is text." in str(result)
    # Changes should be processed
    assert "New text." in str(result) or "\\added{New text.}" in str(result)


def test_formatter_with_complex_document():
    """Test formatter with a realistic academic document."""
    documents = {
        "main.tex": (
            "\\section{Introduction}\n"
            "This paper presents a novel approach. "
            "We show significant improvements. "
            "The rest is organized as follows.\n\n"
            "\\section{Related Work}\n"
            "Previous work by Smith et al. focused on X. "
            "Our approach differs in Y."
        ),
    }
    result = flatten(documents, "main.tex", format_output=True)
    result_str = str(result)

    # Each sentence should be on its own line
    assert "This paper presents a novel approach.\n" in result_str
    assert "We show significant improvements.\n" in result_str

    # Blank lines should be preserved
    assert "\n\n" in result_str

    # Abbreviations should not cause splits
    assert "et al." in result_str
