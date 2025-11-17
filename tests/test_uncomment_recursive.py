r"""
Tests for UNCOMMENT interactions with recursive file imports and other markers.

This module tests critical edge cases:
- UNCOMMENT revealing \input commands
- UNCOMMENT revealing EXCLUDE markers
- UNCOMMENT revealing other markers (RAW, NO-FORMAT)
- Nested files containing UNCOMMENT blocks
- Order of operations in the preprocessing pipeline
"""

from pathlib import Path

import pytest

from flachtex.preprocessor import Preprocessor


class TestUncommentRevealingImports:
    r"""Test UNCOMMENT revealing \input commands that should be processed."""

    def test_uncomment_reveals_input_command(self, tmp_path):
        r"""Test that UNCOMMENT can reveal an \input command that gets processed."""
        main_file = tmp_path / "main.tex"
        included_file = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Main Content}
This is the main file.

%%FLACHTEX-UNCOMMENT-START
% \input{chapter.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        included_file.write_text(
            r"""\section{Chapter}
This chapter was revealed by UNCOMMENT.
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # UNCOMMENT should reveal the \input command
        assert r"\input{chapter.tex}" not in str(result)  # Command should be expanded

        # Chapter content should be included
        assert r"\section{Chapter}" in str(result)
        assert "This chapter was revealed by UNCOMMENT" in str(result)

    def test_uncomment_reveals_multiple_inputs(self, tmp_path):
        r"""Test UNCOMMENT revealing multiple \input commands."""
        main_file = tmp_path / "main.tex"
        chapter1 = tmp_path / "chapter1.tex"
        chapter2 = tmp_path / "chapter2.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% \input{chapter1.tex}
% \input{chapter2.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        chapter1.write_text(r"\section{Chapter 1}" + "\n")
        chapter2.write_text(r"\section{Chapter 2}" + "\n")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both chapters should be included
        assert r"\section{Chapter 1}" in str(result)
        assert r"\section{Chapter 2}" in str(result)

    def test_uncomment_with_nested_file_containing_uncomment(self, tmp_path):
        r"""Test UNCOMMENT revealing \input to file that also has UNCOMMENT."""
        main_file = tmp_path / "main.tex"
        nested_file = tmp_path / "nested.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% \input{nested.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        nested_file.write_text(
            r"""\section{Nested File}

%%FLACHTEX-UNCOMMENT-START
% \subsection{Uncommented Subsection}
% This was commented in the nested file.
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both levels of UNCOMMENT should work
        assert r"\section{Nested File}" in str(result)
        assert r"\subsection{Uncommented Subsection}" in str(result)
        assert "This was commented in the nested file" in str(result)


class TestUncommentRevealingMarkers:
    r"""Test UNCOMMENT revealing other flachtex markers."""

    def test_uncomment_reveals_exclude_markers(self, tmp_path):
        r"""Test UNCOMMENT revealing EXCLUDE markers that should be processed."""
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Version A}
This is the default version.

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-EXCLUDE-START
% \section{Version B}
% This version should be excluded.
% %%FLACHTEX-EXCLUDE-STOP
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Version A should be present
        assert "Version A" in str(result)
        assert "default version" in str(result)

        # Version B should be excluded (UNCOMMENT revealed EXCLUDE markers)
        assert "Version B" not in str(result)
        assert "should be excluded" not in str(result)

    def test_uncomment_cannot_reveal_raw_markers(self, tmp_path):
        r"""
        Test that UNCOMMENT cannot reveal RAW markers.

        RAW blocks are extracted BEFORE UNCOMMENT processing, so you cannot
        use UNCOMMENT to conditionally enable RAW blocks.
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% \newcommand{\test}{value}
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # RAW markers should NOT be processed (they're revealed too late)
        # The uncommented text will just be regular content
        assert "FLACHTEX-RAW-START" in str(result)  # Markers visible as comments
        assert r"\newcommand{\test}{value}" in str(result)


class TestUncommentWithExcludeCombinations:
    r"""Test combining UNCOMMENT and EXCLUDE for version control."""

    def test_exclude_default_uncomment_alternative(self, tmp_path):
        r"""
        Test standard pattern: EXCLUDE default, UNCOMMENT alternative.

        This is the primary use case for UNCOMMENT - swapping versions.
        """
        main_file = tmp_path / "main.tex"
        default_chapter = tmp_path / "chapter_default.tex"
        alt_chapter = tmp_path / "chapter_alternative.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-EXCLUDE-START
\input{chapter_default.tex}
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% \input{chapter_alternative.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        default_chapter.write_text(r"\section{Default Chapter}")
        alt_chapter.write_text(r"\section{Alternative Chapter}")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Default should be excluded
        assert "Default Chapter" not in str(result)

        # Alternative should be uncommented and included
        assert "Alternative Chapter" in str(result)

    def test_nested_file_with_exclude_uncomment_swap(self, tmp_path):
        r"""Test version swapping in a nested file."""
        main_file = tmp_path / "main.tex"
        chapter_file = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}
\input{chapter.tex}
\end{document}
"""
        )

        chapter_file.write_text(
            r"""\section{Chapter}

%%FLACHTEX-EXCLUDE-START
Default configuration: \usepackage{packageA}
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% Alternative configuration: \usepackage{packageB}
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Default excluded, alternative uncommented
        assert "packageA" not in str(result)
        assert "packageB" in str(result)
        assert "Alternative configuration" in str(result)


class TestUncommentOrderOfOperations:
    r"""Test that UNCOMMENT happens at the correct stage in the pipeline."""

    def test_uncomment_before_exclude(self, tmp_path):
        r"""
        Verify UNCOMMENT happens before EXCLUDE processing.

        If UNCOMMENT reveals EXCLUDE markers, they should be processed.
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Keep This}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-EXCLUDE-START
% \section{Remove This}
% %%FLACHTEX-EXCLUDE-STOP
%%FLACHTEX-UNCOMMENT-STOP

\section{Keep This Too}

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Verify EXCLUDE was processed after UNCOMMENT revealed it
        assert "Keep This" in str(result)
        assert "Keep This Too" in str(result)
        assert "Remove This" not in str(result)

    def test_uncomment_before_import_finding(self, tmp_path):
        r"""
        Verify UNCOMMENT happens before import finding.

        If UNCOMMENT reveals \input, it should be found and processed.
        """
        main_file = tmp_path / "main.tex"
        chapter = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% \input{chapter.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        chapter.write_text(r"\section{Chapter Content}")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Verify import was found and processed after UNCOMMENT
        assert "Chapter Content" in str(result)
        assert r"\input{chapter.tex}" not in str(result)


class TestUncommentEdgeCasesWithImports:
    r"""Test edge cases involving UNCOMMENT and imports."""

    def test_uncomment_partial_input_command(self, tmp_path):
        r"""Test UNCOMMENT revealing parts of an \input command."""
        main_file = tmp_path / "main.tex"
        chapter = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\input{
%%FLACHTEX-UNCOMMENT-START
% chapter.tex
%%FLACHTEX-UNCOMMENT-STOP
}

\end{document}
"""
        )

        chapter.write_text(r"\section{Chapter}")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # The \input command should be reconstructed and processed
        assert r"\section{Chapter}" in str(result)

    def test_uncomment_in_included_file_with_exclude(self, tmp_path):
        r"""Test complex interaction: nested file has both UNCOMMENT and EXCLUDE."""
        main_file = tmp_path / "main.tex"
        chapter = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}
\input{chapter.tex}
\end{document}
"""
        )

        chapter.write_text(
            r"""\section{Chapter}

%%FLACHTEX-EXCLUDE-START
Version A content
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% Version B content
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # EXCLUDE removes Version A, UNCOMMENT reveals Version B
        assert "Version A content" not in str(result)
        assert "Version B content" in str(result)

    def test_deeply_nested_uncomment_chain(self, tmp_path):
        r"""Test multiple levels of nesting with UNCOMMENT at each level."""
        main_file = tmp_path / "main.tex"
        level1 = tmp_path / "level1.tex"
        level2 = tmp_path / "level2.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% \input{level1.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        level1.write_text(
            r"""\section{Level 1}

%%FLACHTEX-UNCOMMENT-START
% \input{level2.tex}
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        level2.write_text(
            r"""\subsection{Level 2}

%%FLACHTEX-UNCOMMENT-START
% \subsubsection{Level 2 Uncommented}
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # All levels should be processed
        assert r"\section{Level 1}" in str(result)
        assert r"\subsection{Level 2}" in str(result)
        assert r"\subsubsection{Level 2 Uncommented}" in str(result)
