"""
Tests for FLACHTEX-UNCOMMENT functionality.

UNCOMMENT markers remove leading '% ' from lines, allowing commented-out
content to be activated during processing. This is useful for:
- Maintaining alternative versions for external tools (grammar checkers)
- Fixing paths/imports after flattening
- Conditional content that external tools can't handle with LaTeX conditionals
"""

from pathlib import Path

import pytest

from flachtex.preprocessor import Preprocessor
from flachtex.traceable_string import TraceableString


class TestBasicUncomment:
    """Basic UNCOMMENT marker functionality."""

    def test_uncomment_simple_lines(self, tmp_path):
        """Test basic uncomment of simple commented lines."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

Normal text here.

%%FLACHTEX-UNCOMMENT-START
% \section{Uncommented Section}
% This line was commented.
% So was this one.
%%FLACHTEX-UNCOMMENT-STOP

More normal text.

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Uncommented content should be present without leading %
        assert "\\section{Uncommented Section}" in str(result)
        assert "This line was commented." in str(result)
        assert "So was this one." in str(result)

        # Should not have leading % anymore
        assert "% \\section{Uncommented Section}" not in str(result)
        assert "% This line was commented." not in str(result)

        # Normal text preserved
        assert "Normal text here." in str(result)
        assert "More normal text." in str(result)

        # Markers should be removed
        assert "FLACHTEX-UNCOMMENT-START" not in str(result)
        assert "FLACHTEX-UNCOMMENT-STOP" not in str(result)

    def test_uncomment_mixed_content(self, tmp_path):
        """Test uncomment with mixed commented and uncommented lines."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% Commented line 1
Uncommented line
% Commented line 2
Another uncommented line
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both types should be present, comments removed
        assert "Commented line 1\n" in str(result)
        assert "Uncommented line\n" in str(result)
        assert "Commented line 2\n" in str(result)
        assert "Another uncommented line\n" in str(result)

        # No leading % should remain
        assert "% Commented line 1" not in str(result)
        assert "% Commented line 2" not in str(result)

    def test_uncomment_empty_comment_lines(self, tmp_path):
        """Test uncomment with empty comment lines (% followed by newline)."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% Line 1
%
% Line 2
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Empty comment line should become empty line
        assert "Line 1\n\nLine 2\n" in str(result)

    def test_uncomment_preserves_indentation(self, tmp_path):
        """Test that content indentation after % is preserved."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% \begin{itemize}
%   \item First
%   \item Second
% \end{itemize}
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Indentation after % should be preserved
        assert "\\begin{itemize}\n" in str(result)
        assert "  \\item First\n" in str(result)
        assert "  \\item Second\n" in str(result)
        assert "\\end{itemize}\n" in str(result)

    def test_uncomment_nested_percent(self, tmp_path):
        """Test uncomment with nested % (should remove only first %)."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% % This had two percent signs
% Text % with inline comment
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # First % removed, second % (and space) preserved
        assert "% This had two percent signs\n" in str(result)
        assert "Text % with inline comment\n" in str(result)

    def test_uncomment_no_space_after_percent(self, tmp_path):
        """Test uncomment with % not followed by space."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
%No space after percent
% Space after percent
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # % without space: remove just %
        assert "No space after percent\n" in str(result)
        # % with space: remove % and space
        assert "Space after percent\n" in str(result)


class TestUncommentWithOtherMarkers:
    """Test UNCOMMENT interaction with other markers."""

    def test_uncomment_with_exclude(self, tmp_path):
        """Test UNCOMMENT combined with EXCLUDE for version swapping."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-EXCLUDE-START
\section{Version A}
This is the default version.
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% \section{Version B}
% This is the alternative version.
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Version A should be excluded
        assert "Version A" not in str(result)
        assert "default version" not in str(result)

        # Version B should be uncommented and present
        assert "\\section{Version B}" in str(result)
        assert "alternative version" in str(result)

    def test_uncomment_does_not_affect_raw_blocks(self, tmp_path):
        """Test that UNCOMMENT does not affect RAW blocks."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-RAW-START
% This comment should stay in RAW block
\newcommand{\test}{value}
%%FLACHTEX-RAW-STOP

%%FLACHTEX-UNCOMMENT-START
% This should be uncommented
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # RAW block comment should be preserved
        assert "% This comment should stay in RAW block" in str(result)

        # UNCOMMENT block should be processed
        assert "This should be uncommented\n" in str(result)
        assert "% This should be uncommented" not in str(result)

    def test_multiple_uncomment_blocks(self, tmp_path):
        """Test multiple UNCOMMENT blocks in same file."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""Section 1

%%FLACHTEX-UNCOMMENT-START
% Uncommented block 1
%%FLACHTEX-UNCOMMENT-STOP

Section 2

%%FLACHTEX-UNCOMMENT-START
% Uncommented block 2
%%FLACHTEX-UNCOMMENT-STOP

Section 3
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both blocks should be uncommented
        assert "Uncommented block 1\n" in str(result)
        assert "Uncommented block 2\n" in str(result)

        # No comments should remain
        assert "% Uncommented block 1" not in str(result)
        assert "% Uncommented block 2" not in str(result)


class TestUncommentRealUseCases:
    """Test real-world use cases for UNCOMMENT."""

    def test_usecase_path_fixing_after_flattening(self, tmp_path):
        """
        Real use case: Fix paths after flattening.

        When flattening changes directory structure, paths may need adjustment.
        """
        main_file = tmp_path / "main.tex"
        chapter_file = tmp_path / "chapters" / "intro.tex"
        chapter_file.parent.mkdir()

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\input{chapters/intro.tex}

%%FLACHTEX-EXCLUDE-START
% Path for multi-file structure
\graphicspath{{chapters/figures/}}
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% % Path for flattened structure
% \graphicspath{{figures/}}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        chapter_file.write_text(r"\section{Introduction}")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Multi-file path excluded
        assert "\\graphicspath{{chapters/figures/}}" not in str(result)

        # Flattened path uncommented
        assert "\\graphicspath{{figures/}}" in str(result)

        # Chapter content flattened
        assert "\\section{Introduction}" in str(result)

    def test_usecase_version_for_grammar_checker(self, tmp_path):
        """
        Real use case: Alternative version for external tool processing.

        Grammar checkers can't execute LaTeX conditionals. UNCOMMENT provides
        a simple way to maintain alternative versions.
        """
        main_file = tmp_path / "paper.tex"
        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

\section{Introduction}

The conference version provides a brief overview.

%%FLACHTEX-UNCOMMENT-START
% % Extended journal version:
% % The journal version provides comprehensive analysis with
% % detailed methodology and extensive experimental results.
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both versions present (conference + uncommented journal)
        assert "brief overview" in str(result)
        assert "comprehensive analysis" in str(result)
        assert "detailed methodology" in str(result)

    def test_usecase_package_options_after_flattening(self, tmp_path):
        """
        Real use case: Different package options for flattened version.

        Some packages behave differently in multi-file vs flattened documents.
        """
        main_file = tmp_path / "main.tex"
        section_file = tmp_path / "section.tex"

        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-EXCLUDE-START
% Multi-file structure uses subfiles package
\usepackage{subfiles}
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% % Flattened version doesn't need subfiles
% % \usepackage{standalone}
%%FLACHTEX-UNCOMMENT-STOP

\begin{document}
\input{section.tex}
\end{document}
"""
        )

        section_file.write_text(r"\section{Content}")

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Subfiles package excluded
        assert "\\usepackage{subfiles}" not in str(result)

        # Standalone package uncommented
        assert "\\usepackage{standalone}" in str(result)

        # Content flattened
        assert "\\section{Content}" in str(result)


class TestUncommentEdgeCases:
    """Test edge cases and error conditions."""

    def test_uncomment_empty_block(self, tmp_path):
        """Test UNCOMMENT with empty block."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Should not crash, just produce empty output
        assert str(result) == ""

    def test_uncomment_only_whitespace(self, tmp_path):
        """Test UNCOMMENT with only whitespace in block."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START


%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Should preserve whitespace
        assert "\n" in str(result)

    def test_uncomment_with_unclosed_block_raises_error(self, tmp_path):
        """Test that unclosed UNCOMMENT block raises error."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% Unclosed block
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        with pytest.raises(ValueError, match="Unclosed UNCOMMENT block"):
            preprocessor.expand_file(str(main_file))

    def test_uncomment_with_stop_without_start_raises_error(self, tmp_path):
        """Test that STOP without START raises error."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""% Some text
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        with pytest.raises(ValueError, match="UNCOMMENT-STOP without UNCOMMENT-START"):
            preprocessor.expand_file(str(main_file))

    def test_uncomment_nested_blocks_raise_error(self, tmp_path):
        """Test that nested UNCOMMENT blocks raise error."""
        main_file = tmp_path / "test.tex"
        main_file.write_text(
            r"""%%FLACHTEX-UNCOMMENT-START
% Outer
%%FLACHTEX-UNCOMMENT-START
% Nested (not allowed)
%%FLACHTEX-UNCOMMENT-STOP
%%FLACHTEX-UNCOMMENT-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        with pytest.raises(ValueError, match="Nested UNCOMMENT blocks"):
            preprocessor.expand_file(str(main_file))
