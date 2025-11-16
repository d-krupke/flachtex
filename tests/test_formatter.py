"""
Tests for LaTeX formatter that makes documents more diff-friendly.

The formatter implements "one sentence per line" which is best practice
for version control systems, making diffs more readable.
"""

import pytest

from flachtex.formatter import format_latex
from flachtex.traceable_string import TraceableString


class TestBasicSentenceSplitting:
    """Test basic sentence splitting functionality."""

    def test_simple_sentence_splitting(self):
        """Split simple sentences at period boundaries."""
        content = TraceableString(
            "This is sentence one. This is sentence two. This is sentence three.",
            origin="test",
        )
        result = format_latex(content)
        expected = "This is sentence one.\nThis is sentence two.\nThis is sentence three."
        assert str(result) == expected

    def test_preserve_single_sentence(self):
        """Don't add unnecessary line breaks for single sentence."""
        content = TraceableString("This is a single sentence.", origin="test")
        result = format_latex(content)
        assert str(result) == "This is a single sentence."

    def test_question_and_exclamation_marks(self):
        """Split at question marks and exclamation marks too."""
        content = TraceableString(
            "Is this a question? Yes it is! This is amazing.",
            origin="test",
        )
        result = format_latex(content)
        expected = "Is this a question?\nYes it is!\nThis is amazing."
        assert str(result) == expected

    def test_preserve_existing_line_breaks(self):
        """Don't add extra line breaks if sentences already on separate lines."""
        content = TraceableString(
            "This is sentence one.\nThis is sentence two.\nThis is sentence three.",
            origin="test",
        )
        result = format_latex(content)
        expected = "This is sentence one.\nThis is sentence two.\nThis is sentence three."
        assert str(result) == expected

    def test_abbreviations_not_split(self):
        """Don't split at abbreviations like Dr., Mr., etc."""
        content = TraceableString(
            "Dr. Smith went to the store. He bought milk.",
            origin="test",
        )
        result = format_latex(content)
        expected = "Dr. Smith went to the store.\nHe bought milk."
        assert str(result) == expected

    def test_numbers_not_split(self):
        """Don't split at decimal numbers."""
        content = TraceableString(
            "The value is 3.14159 approximately. This is pi.",
            origin="test",
        )
        result = format_latex(content)
        expected = "The value is 3.14159 approximately.\nThis is pi."
        assert str(result) == expected


class TestParagraphHandling:
    """Test handling of paragraphs and blank lines."""

    def test_preserve_blank_lines(self):
        """Preserve blank lines that separate paragraphs."""
        content = TraceableString(
            "First paragraph sentence one. First paragraph sentence two.\n\n"
            "Second paragraph sentence one. Second paragraph sentence two.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "First paragraph sentence one.\nFirst paragraph sentence two.\n\n"
            "Second paragraph sentence one.\nSecond paragraph sentence two."
        )
        assert str(result) == expected

    def test_multiple_blank_lines(self):
        """Preserve multiple blank lines."""
        content = TraceableString(
            "First paragraph.\n\n\nSecond paragraph.",
            origin="test",
        )
        result = format_latex(content)
        expected = "First paragraph.\n\n\nSecond paragraph."
        assert str(result) == expected


class TestCommentsHandling:
    """Test handling of LaTeX comments."""

    def test_preserve_line_comments(self):
        """Preserve line comments as-is."""
        content = TraceableString(
            "This is a sentence. % This is a comment\nThis is another sentence.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "This is a sentence. % This is a comment\nThis is another sentence."
        )
        assert str(result) == expected

    def test_comment_at_sentence_boundary(self):
        """Handle comments that appear at sentence boundaries."""
        content = TraceableString(
            "This is sentence one.% comment\nThis is sentence two.",
            origin="test",
        )
        result = format_latex(content)
        # Comment should stay with its sentence
        expected = "This is sentence one.% comment\nThis is sentence two."
        assert str(result) == expected


class TestVerbatimEnvironments:
    """Test that verbatim environments are not reformatted."""

    def test_verbatim_environment_preserved(self):
        """Content inside verbatim environment should not be reformatted."""
        content = TraceableString(
            "This is before. This is also before.\n"
            "\\begin{verbatim}\n"
            "This. Has. Many. Periods. But should not be split.\n"
            "\\end{verbatim}\n"
            "This is after. This is also after.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "This is before.\nThis is also before.\n"
            "\\begin{verbatim}\n"
            "This. Has. Many. Periods. But should not be split.\n"
            "\\end{verbatim}\n"
            "This is after.\nThis is also after."
        )
        assert str(result) == expected

    def test_lstlisting_environment_preserved(self):
        """lstlisting environment should not be reformatted."""
        content = TraceableString(
            "Before text. More before text.\n"
            "\\begin{lstlisting}\n"
            "code.with(). many(). calls();\n"
            "\\end{lstlisting}\n"
            "After text. More after text.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Before text.\nMore before text.\n"
            "\\begin{lstlisting}\n"
            "code.with(). many(). calls();\n"
            "\\end{lstlisting}\n"
            "After text.\nMore after text."
        )
        assert str(result) == expected

    def test_minted_environment_preserved(self):
        """minted environment should not be reformatted."""
        content = TraceableString(
            "Before text. More before text.\n"
            "\\begin{minted}{python}\n"
            "print('Hello. World.')\n"
            "\\end{minted}\n"
            "After text. More after text.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Before text.\nMore before text.\n"
            "\\begin{minted}{python}\n"
            "print('Hello. World.')\n"
            "\\end{minted}\n"
            "After text.\nMore after text."
        )
        assert str(result) == expected

    def test_nested_verbatim_like_environments(self):
        """Test multiple verbatim-like environments."""
        content = TraceableString(
            "Text one. Text two.\n"
            "\\begin{verbatim}\n"
            "Verbatim. Content.\n"
            "\\end{verbatim}\n"
            "Middle text. More middle.\n"
            "\\begin{lstlisting}\n"
            "Code. Content.\n"
            "\\end{lstlisting}\n"
            "End text. Final text.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Text one.\nText two.\n"
            "\\begin{verbatim}\n"
            "Verbatim. Content.\n"
            "\\end{verbatim}\n"
            "Middle text.\nMore middle.\n"
            "\\begin{lstlisting}\n"
            "Code. Content.\n"
            "\\end{lstlisting}\n"
            "End text.\nFinal text."
        )
        assert str(result) == expected


class TestMathEnvironments:
    """Test handling of math environments."""

    def test_inline_math_not_split(self):
        """Don't split sentences with inline math."""
        content = TraceableString(
            "The value $x = 3.14$ is approximate. This is another sentence.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "The value $x = 3.14$ is approximate.\nThis is another sentence."
        )
        assert str(result) == expected

    def test_display_math_preserved(self):
        """Display math should be preserved."""
        content = TraceableString(
            "Before equation. Here it is:\n"
            "\\[\n"
            "x = 3.14\n"
            "\\]\n"
            "After equation. More text.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Before equation.\nHere it is:\n"
            "\\[\n"
            "x = 3.14\n"
            "\\]\n"
            "After equation.\nMore text."
        )
        assert str(result) == expected

    def test_equation_environment_preserved(self):
        """Equation environment should be preserved."""
        content = TraceableString(
            "Before. Here is equation:\n"
            "\\begin{equation}\n"
            "E = mc^2\n"
            "\\end{equation}\n"
            "After. More text.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Before.\nHere is equation:\n"
            "\\begin{equation}\n"
            "E = mc^2\n"
            "\\end{equation}\n"
            "After.\nMore text."
        )
        assert str(result) == expected


class TestLaTeXCommands:
    """Test handling of LaTeX commands."""

    def test_command_with_arguments(self):
        """Commands should not be broken across lines."""
        content = TraceableString(
            "This is \\textbf{bold text}. This is normal.",
            origin="test",
        )
        result = format_latex(content)
        expected = "This is \\textbf{bold text}.\nThis is normal."
        assert str(result) == expected

    def test_cite_commands(self):
        """Citations should stay with their sentences."""
        content = TraceableString(
            "This was proven by Smith\\cite{smith2020}. This is another fact.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "This was proven by Smith\\cite{smith2020}.\nThis is another fact."
        )
        assert str(result) == expected

    def test_ref_commands(self):
        """References should stay with their sentences."""
        content = TraceableString(
            "See Section~\\ref{sec:intro}. This is important.",
            origin="test",
        )
        result = format_latex(content)
        expected = "See Section~\\ref{sec:intro}.\nThis is important."
        assert str(result) == expected


class TestComplexCases:
    """Test complex real-world scenarios."""

    def test_academic_paper_paragraph(self):
        """Test realistic academic paper content."""
        content = TraceableString(
            "Machine learning has revolutionized many fields. "
            "Deep learning, in particular, has shown remarkable results. "
            "However, these models require significant computational resources.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "Machine learning has revolutionized many fields.\n"
            "Deep learning, in particular, has shown remarkable results.\n"
            "However, these models require significant computational resources."
        )
        assert str(result) == expected

    def test_mixed_content(self):
        """Test mixed content with commands, math, and environments."""
        content = TraceableString(
            "This is introductory text. The formula $E=mc^2$ is famous. "
            "Einstein developed it.\n"
            "\\begin{verbatim}\n"
            "Code. Example.\n"
            "\\end{verbatim}\n"
            "This concludes the section. See \\cite{einstein1905}.",
            origin="test",
        )
        result = format_latex(content)
        expected = (
            "This is introductory text.\n"
            "The formula $E=mc^2$ is famous.\n"
            "Einstein developed it.\n"
            "\\begin{verbatim}\n"
            "Code. Example.\n"
            "\\end{verbatim}\n"
            "This concludes the section.\nSee \\cite{einstein1905}."
        )
        assert str(result) == expected

    def test_empty_content(self):
        """Handle empty content gracefully."""
        content = TraceableString("", origin="test")
        result = format_latex(content)
        assert str(result) == ""

    def test_only_whitespace(self):
        """Handle whitespace-only content."""
        content = TraceableString("   \n\n   ", origin="test")
        result = format_latex(content)
        assert str(result) == "   \n\n   "


class TestOriginTracking:
    """Test that origin tracking is preserved during formatting."""

    def test_origin_preserved_simple(self):
        """Ensure TraceableString origin tracking is maintained."""
        content = TraceableString(
            "First sentence. Second sentence.",
            origin="test.tex",
        )
        result = format_latex(content)
        # Result should still be a TraceableString
        assert isinstance(result, TraceableString)
        # Origins should be traceable
        assert result.origins is not None


class TestIndentation:
    """Test indentation of environments."""

    def test_simple_environment_indentation(self):
        """Content inside environments should be indented."""
        content = TraceableString(
            "Before text.\n"
            "\\begin{itemize}\n"
            "\\item First. Second.\n"
            "\\item Third.\n"
            "\\end{itemize}\n"
            "After text.",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "Before text.\n"
            "\\begin{itemize}\n"
            "  \\item First.\n"
            "  Second.\n"
            "  \\item Third.\n"
            "\\end{itemize}\n"
            "After text."
        )
        assert str(result) == expected

    def test_nested_environment_indentation(self):
        """Nested environments should have progressive indentation."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item Outer.\n"
            "\\begin{enumerate}\n"
            "\\item Inner.\n"
            "\\end{enumerate}\n"
            "\\end{itemize}",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "\\begin{itemize}\n"
            "  \\item Outer.\n"
            "  \\begin{enumerate}\n"
            "    \\item Inner.\n"
            "  \\end{enumerate}\n"
            "\\end{itemize}"
        )
        assert str(result) == expected

    def test_custom_indent_size(self):
        """Should support custom indentation size."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item First.\n"
            "\\end{itemize}",
            origin="test",
        )
        result = format_latex(content, indent=4)
        expected = (
            "\\begin{itemize}\n"
            "    \\item First.\n"
            "\\end{itemize}"
        )
        assert str(result) == expected

    def test_no_indentation_when_disabled(self):
        """Indentation should be disabled when indent=0."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item First. Second.\n"
            "\\end{itemize}",
            origin="test",
        )
        result = format_latex(content, indent=0)
        expected = (
            "\\begin{itemize}\n"
            "\\item First.\n"
            "Second.\n"
            "\\end{itemize}"
        )
        assert str(result) == expected

    def test_verbatim_not_indented(self):
        """Verbatim environments should not be indented."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item Text.\n"
            "\\begin{verbatim}\n"
            "Code\n"
            "\\end{verbatim}\n"
            "\\end{itemize}",
            origin="test",
        )
        result = format_latex(content, indent=2)
        # Verbatim content stays as-is
        assert "\\begin{verbatim}\nCode\n\\end{verbatim}" in str(result)

    def test_equation_environment_indentation(self):
        """Math environments should be indented."""
        content = TraceableString(
            "Text before.\n"
            "\\begin{equation}\n"
            "E = mc^2\n"
            "\\end{equation}\n"
            "Text after.",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "Text before.\n"
            "\\begin{equation}\n"
            "  E = mc^2\n"
            "\\end{equation}\n"
            "Text after."
        )
        assert str(result) == expected

    def test_indentation_with_sentences(self):
        """Indentation should work with sentence splitting."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item First sentence. Second sentence. Third sentence.\n"
            "\\end{itemize}",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "\\begin{itemize}\n"
            "  \\item First sentence.\n"
            "  Second sentence.\n"
            "  Third sentence.\n"
            "\\end{itemize}"
        )
        assert str(result) == expected

    def test_multiple_environments(self):
        """Multiple environments at same level should have same indentation."""
        content = TraceableString(
            "\\begin{itemize}\n"
            "\\item One.\n"
            "\\end{itemize}\n"
            "Text between.\n"
            "\\begin{enumerate}\n"
            "\\item Two.\n"
            "\\end{enumerate}",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "\\begin{itemize}\n"
            "  \\item One.\n"
            "\\end{itemize}\n"
            "Text between.\n"
            "\\begin{enumerate}\n"
            "  \\item Two.\n"
            "\\end{enumerate}"
        )
        assert str(result) == expected

    def test_document_environment_not_indented(self):
        """Document environment should not cause indentation."""
        content = TraceableString(
            "\\begin{document}\n"
            "Text in document.\n"
            "\\begin{itemize}\n"
            "\\item Nested item.\n"
            "\\end{itemize}\n"
            "\\end{document}",
            origin="test",
        )
        result = format_latex(content, indent=2)
        expected = (
            "\\begin{document}\n"
            "Text in document.\n"
            "\\begin{itemize}\n"
            "  \\item Nested item.\n"
            "\\end{itemize}\n"
            "\\end{document}"
        )
        assert str(result) == expected


class TestEdgeCases:
    """Test edge cases and potential issues."""

    def test_escaped_period(self):
        """Escaped periods should not cause sentence splits."""
        content = TraceableString(
            "This is e\\.g\\. an example. This is another sentence.",
            origin="test",
        )
        result = format_latex(content)
        # e.g. should not be treated as sentence boundary
        expected = "This is e\\.g\\. an example.\nThis is another sentence."
        assert str(result) == expected

    def test_ellipsis(self):
        """Ellipsis should not cause multiple splits."""
        content = TraceableString(
            "This is a sentence with... ellipsis. This is another.",
            origin="test",
        )
        result = format_latex(content)
        expected = "This is a sentence with... ellipsis.\nThis is another."
        assert str(result) == expected

    def test_multiple_spaces_after_period(self):
        """Handle multiple spaces after period."""
        content = TraceableString(
            "This is sentence one.  This is sentence two.",
            origin="test",
        )
        result = format_latex(content)
        # Should normalize to single newline
        expected = "This is sentence one.\nThis is sentence two."
        assert str(result) == expected

    def test_period_at_end_of_line(self):
        """Handle period already at end of line."""
        content = TraceableString(
            "This is sentence one.\n This is sentence two.",
            origin="test",
        )
        result = format_latex(content)
        # The formatter preserves existing line breaks and whitespace
        expected = "This is sentence one.\n This is sentence two."
        assert str(result) == expected
