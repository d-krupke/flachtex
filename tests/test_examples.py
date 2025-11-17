"""
Tests for documentation examples.

This module contains realistic, real-world examples that are used in documentation.
Each test verifies that the example works correctly, ensuring our documentation
shows accurate, working examples focused on actual flachtex use cases.
"""

from pathlib import Path

import pytest

from flachtex.comments import remove_comments
from flachtex.formatter import format_latex
from flachtex.preprocessor import Preprocessor
from flachtex.rules import TodonotesRule
from flachtex.traceable_string import TraceableString


class TestExcludeMarkerExamples:
    r"""
    ExampleExamples for %%FLACHTEX-EXCLUDE-START/STOP markers.

    These markers remove content from the final output during flattening.
    Use for draft notes, work-in-progress sections, or temporary content.
    """

    def test_example_excluding_draft_sections(self, tmp_path):
        r"""
        ExampleExample: Exclude work-in-progress sections from journal submission.

        Use case: You have sections that are incomplete and should not
        appear in the version sent to reviewers or journals.
        """
        main_file = tmp_path / "paper.tex"
        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Introduction}
This paper presents a novel approach to the problem.

\section{Methods}
We use standard techniques from the literature.

%%FLACHTEX-EXCLUDE-START
\section{Advanced Analysis}
This section is still being written and contains incomplete arguments.
We need to add proofs and more detailed explanations.
%%FLACHTEX-EXCLUDE-STOP

\section{Conclusion}
Our results demonstrate the effectiveness of our approach.

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # WIP section is excluded
        assert "Advanced Analysis" not in str(result)
        assert "incomplete arguments" not in str(result)

        # Complete sections are preserved
        assert "Introduction" in str(result)
        assert "Methods" in str(result)
        assert "Conclusion" in str(result)

    def test_example_excluding_include_directives(self, tmp_path):
        r"""
        ExampleExample: Exclude certain \input files from flattening.

        Use case: You have multiple versions (appendix, supplementary material)
        and want to exclude some from the main submission.
        """
        main_file = tmp_path / "paper.tex"
        appendix_file = tmp_path / "appendix.tex"
        supplement_file = tmp_path / "supplement.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Main Content}
Here is the main paper content.

\input{appendix.tex}

%%FLACHTEX-EXCLUDE-START
\input{supplement.tex}
%%FLACHTEX-EXCLUDE-STOP

\end{document}
"""
        )

        appendix_file.write_text(
            r"""\section{Appendix}
Additional proofs and details.
"""
        )

        supplement_file.write_text(
            r"""\section{Supplementary Material}
This is only for the extended version.
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Appendix is included (flattened)
        assert "Additional proofs" in str(result)

        # Supplement is excluded (entire \input directive removed)
        assert "Supplementary Material" not in str(result)
        assert "extended version" not in str(result)


class TestRawMarkerExamples:
    r"""
    ExampleExamples for %%FLACHTEX-RAW-START/STOP markers.

    These markers bypass ALL preprocessing. Use when flachtex might misinterpret
    complex \newcommand definitions or you want to preserve \input unexpanded.
    """

    def test_example_complex_newcommand_with_parameters(self, tmp_path):
        r"""
        ExampleExample: Protect complex \newcommand that uses parameter substitution.

        Use case: You have a \newcommand with multiple parameters and
        complex expansion that --newcommand might misprocess.
        """
        main_file = tmp_path / "paper.tex"
        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-RAW-START
% Complex macro with nested parameter substitution
\newcommand{\mycite}[2]{%
  \cite{#1}%
  \footnote{#2}%
}
%%FLACHTEX-RAW-STOP

\begin{document}
We refer to important work\mycite{smith2020}{See page 42}.
\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # RAW block preserved exactly with markers (they're comments)
        assert r"\newcommand{\mycite}" in str(result)
        assert "#1" in str(result)
        assert "#2" in str(result)
        assert "FLACHTEX-RAW-START" in str(result)  # Markers preserved



class TestNoFormatMarkerExamples:
    r"""
    ExampleExamples for %%FLACHTEX-NO-FORMAT-START/STOP markers.

    These markers skip sentence-per-line formatting while allowing other
    preprocessing. Use for tables or content where you want to preserve
    exact line breaks.
    """

    def test_example_preserving_table_alignment(self):
        r"""
        ExampleExample: Preserve manual alignment in tabular outside protected environment.

        Use case: You have a manually aligned table and want sentence-per-line
        formatting for prose, but not for the table.
        """
        content = TraceableString(
            r"""\section{Results}

Our experiments show three key findings. First, accuracy improved significantly. Second, runtime was acceptable.

%%FLACHTEX-NO-FORMAT-START
\begin{tabular}{lrr}
Method      & Accuracy & Time \\
\hline
Baseline    & 87.3\%   & 10s  \\
Ours        & 95.1\%   & 12s  \\
\end{tabular}
%%FLACHTEX-NO-FORMAT-STOP

These results confirm our hypothesis. The improvement is statistically significant.
""",
            origin="test",
        )

        formatted = format_latex(content, sentence_per_line=True)

        # Prose is formatted (sentence-per-line)
        assert "First, accuracy improved significantly.\n" in str(formatted)
        assert "Second, runtime was acceptable.\n" in str(formatted)
        assert "These results confirm our hypothesis.\n" in str(formatted)

        # Table alignment preserved (spaces maintained)
        assert "Method      & Accuracy & Time" in str(formatted)
        assert "Baseline    & 87.3\\%   & 10s" in str(formatted)

    def test_example_preserving_equation_alignment(self):
        r"""
        ExampleExample: Preserve manual line breaks in aligned equations outside protected environment.

        Use case: You have equations with specific alignment you want to preserve
        while still formatting surrounding text.
        """
        content = TraceableString(
            r"""\section{Theory}

We derive the following result. The proof is straightforward. Consider the equations below.

%%FLACHTEX-NO-FORMAT-START
\begin{align}
f(x) &= x^2 + 2x + 1 \\
     &= (x+1)^2
\end{align}
%%FLACHTEX-NO-FORMAT-STOP

This completes the proof. The result generalizes easily.
""",
            origin="test",
        )

        formatted = format_latex(content, sentence_per_line=True)

        # Text formatted
        assert "The proof is straightforward.\n" in str(formatted)
        assert "This completes the proof.\n" in str(formatted)

        # Equation alignment preserved
        assert "f(x) &= x^2 + 2x + 1 \\\\" in str(formatted)
        assert "     &= (x+1)^2" in str(formatted)


class TestCommentAndFormattingInteraction:
    r"""
    ExampleExamples showing how comments interact with formatting.
    """

    def test_example_format_then_remove_comments(self):
        r"""
        ExampleExample: Format with sentence-per-line, then remove comments.

        Use case: You want diff-friendly formatting and clean final output.
        This is the CORRECT order: format first (so NO-FORMAT markers work),
        then remove comments.
        """
        content = TraceableString(
            r"""\section{Introduction}

Machine learning has grown rapidly. % Add citation here
Recent advances enable new applications. % Expand this

%%FLACHTEX-NO-FORMAT-START
\begin{equation}
E = mc^2 % Keep this on one line
\end{equation}
%%FLACHTEX-NO-FORMAT-STOP

Our work builds on these ideas.
""",
            origin="test",
        )

        # Step 1: Format (markers are still visible as comments)
        formatted = format_latex(content, sentence_per_line=True)

        # Sentences are split, comments stay with their sentences
        assert "Machine learning has grown rapidly. % Add citation here\n" in str(
            formatted
        )

        # NO-FORMAT markers work (equation stays on one line)
        assert "E = mc^2 % Keep this on one line" in str(formatted)

        # Step 2: Remove comments (after formatting)
        no_comments = remove_comments(formatted)

        # Sentences remain split, comments gone
        assert "Machine learning has grown rapidly.\n" in str(no_comments)
        assert "Recent advances enable new applications.\n" in str(no_comments)
        assert "Add citation" not in str(no_comments)


class TestMultiFileFlattening:
    r"""
    ExampleExamples for the primary use case: flattening multi-file LaTeX projects.
    """

    def test_example_thesis_with_chapters(self, tmp_path):
        r"""
        ExampleExample: Flatten a thesis with multiple chapter files.

        Use case: Standard multi-file LaTeX project structure where each
        chapter is in a separate file.
        """
        main_file = tmp_path / "thesis.tex"
        chapter1 = tmp_path / "chapter1.tex"
        chapter2 = tmp_path / "chapter2.tex"

        main_file.write_text(
            r"""\documentclass{book}
\begin{document}

\chapter{Preface}
This thesis presents...

\input{chapter1.tex}
\input{chapter2.tex}

\end{document}
"""
        )

        chapter1.write_text(
            r"""\chapter{Background}
The field of machine learning...
"""
        )

        chapter2.write_text(
            r"""\chapter{Methods}
We propose a novel approach...
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # All chapters flattened into one document
        assert "\\chapter{Preface}" in str(result)
        assert "\\chapter{Background}" in str(result)
        assert "The field of machine learning" in str(result)
        assert "\\chapter{Methods}" in str(result)
        assert "We propose a novel approach" in str(result)

        # No \input commands remain
        assert "\\input{chapter1.tex}" not in str(result)
        assert "\\input{chapter2.tex}" not in str(result)

    def test_example_paper_with_sections(self, tmp_path):
        r"""
        ExampleExample: Flatten a paper with separate section files.

        Use case: Conference paper where each section is in its own file
        for easier collaboration.
        """
        main_file = tmp_path / "paper.tex"
        intro = tmp_path / "intro.tex"
        methods = tmp_path / "methods.tex"
        results = tmp_path / "results.tex"

        main_file.write_text(
            r"""\documentclass{article}
\title{Our Paper}
\begin{document}
\maketitle

\input{intro}
\input{methods}
\input{results}

\section{Conclusion}
We have demonstrated our approach.

\end{document}
"""
        )

        intro.write_text(r"\section{Introduction}" + "\n" + r"Recent work has shown...")
        methods.write_text(r"\section{Methods}" + "\n" + r"Our methodology involves...")
        results.write_text(r"\section{Results}" + "\n" + r"Our experiments show...")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # All sections present in flattened document
        assert "\\section{Introduction}" in str(result)
        assert "Recent work has shown" in str(result)
        assert "\\section{Methods}" in str(result)
        assert "Our methodology involves" in str(result)
        assert "\\section{Results}" in str(result)
        assert "Our experiments show" in str(result)
        assert "\\section{Conclusion}" in str(result)


class TestCompleteWorkflowExamples:
    """
    Complete realistic workflows combining multiple features.
    """

    def test_example_arxiv_submission_workflow(self, tmp_path):
        r"""
        ExampleExample: Prepare paper for arXiv submission.

        Use case: arXiv requires a single flattened .tex file with all content.
        You want to remove TODOs and format for version control.
        """
        main_file = tmp_path / "paper.tex"
        intro = tmp_path / "intro.tex"

        main_file.write_text(
            r"""\documentclass{article}
\usepackage{todonotes}
\begin{document}

\input{intro}

\section{Methods}
Our approach uses standard techniques.
\todo{Add more detail about implementation}

\end{document}
"""
        )

        intro.write_text(
            r"""\section{Introduction}
Machine learning has grown. Deep learning enables new applications.
\todo{Expand literature review}
"""
        )

        # Simulate: flachtex --format --todos paper.tex
        preprocessor = Preprocessor(str(tmp_path))
        preprocessor.skip_rules.append(TodonotesRule())

        # 1. Flatten files and remove TODOs
        doc = preprocessor.expand_file(str(main_file))

        # 2. Format for version control
        doc = format_latex(doc, sentence_per_line=True)

        result = str(doc)

        # Files are flattened
        assert "\\input{intro}" not in result
        assert "Machine learning has grown" in result

        # TODOs removed
        assert "\\todo" not in result
        assert "Add more detail" not in result
        assert "Expand literature review" not in result

        # Text formatted (sentence-per-line)
        assert "Machine learning has grown.\n" in result
        assert "Deep learning enables new applications.\n" in result

    def test_example_journal_submission_with_comments(self, tmp_path):
        r"""
        ExampleExample: Journal submission workflow with comment removal.

        Use case: Remove all draft comments and TODOs, format for submission.
        """
        paper_file = tmp_path / "paper.tex"
        paper_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Introduction}
% NOTE: Check if this intro is strong enough
Our work addresses a critical problem. We propose a solution.

%%FLACHTEX-EXCLUDE-START
\section{Future Work}
This section is not ready for submission yet.
%%FLACHTEX-EXCLUDE-STOP

\section{Conclusion}
% TODO: Add final remarks
We have demonstrated our approach.

\end{document}
"""
        )

        # Simulate: flachtex --format --comments paper.tex
        preprocessor = Preprocessor(str(tmp_path))
        doc = preprocessor.expand_file(str(paper_file))

        # Format first (so NO-FORMAT markers would work if present)
        doc = format_latex(doc, sentence_per_line=True)

        # Remove comments last
        doc = remove_comments(doc)

        result = str(doc)

        # EXCLUDE sections removed
        assert "Future Work" not in result
        assert "not ready for submission" not in result

        # Comments removed
        assert "NOTE: Check if" not in result
        assert "TODO: Add final" not in result

        # Content preserved and formatted
        assert "Our work addresses a critical problem.\n" in result
        assert "We propose a solution.\n" in result
        assert "We have demonstrated our approach.\n" in result
