r"""
Tests for recursive/iterative RAW block processing.

Currently, RAW blocks are extracted before UNCOMMENT processing, which means
UNCOMMENT cannot reveal RAW blocks. This module tests iterative processing
where RAW extraction happens in a loop to handle revealed RAW blocks.

Use cases:
- UNCOMMENT revealing RAW blocks for version-specific complex macros
- Multiple levels of UNCOMMENT revealing RAW blocks
- Ensuring convergence (no infinite loops)
"""

from pathlib import Path

import pytest

from flachtex.preprocessor import Preprocessor


class TestUncommentRevealingRawBlocks:
    r"""Test that UNCOMMENT can reveal RAW blocks after iterative processing."""

    def test_uncomment_reveals_raw_block(self, tmp_path):
        r"""
        Test UNCOMMENT revealing a RAW block.

        Use case: Alternative version needs to protect a complex macro.
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-EXCLUDE-START
% Simple version for multi-file
\newcommand{\mycmd}{Simple}
%%FLACHTEX-EXCLUDE-STOP

%%FLACHTEX-UNCOMMENT-START
% % Complex version for flattened (needs RAW protection)
% %%FLACHTEX-RAW-START
% \newcommand{\mycmd}[2]{Complex: #1 and #2}
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

\begin{document}
Test: \mycmd
\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Simple version excluded
        assert "Simple version for multi-file" not in str(result)

        # Complex version uncommented
        assert "Complex version for flattened" in str(result)

        # RAW block should be preserved (with markers, as they're comments)
        assert "FLACHTEX-RAW-START" in str(result)
        assert "FLACHTEX-RAW-STOP" in str(result)
        assert r"\newcommand{\mycmd}[2]{Complex: #1 and #2}" in str(result)

        # The #1 and #2 should NOT be substituted (RAW protection working)
        assert "#1" in str(result)
        assert "#2" in str(result)

    def test_uncomment_reveals_raw_protects_content(self, tmp_path):
        r"""
        Test that RAW block revealed by UNCOMMENT protects content.

        Content in revealed RAW blocks should not be processed by skip rules.
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% %%FLACHTEX-EXCLUDE-START
% This should NOT be excluded (protected by RAW)
% %%FLACHTEX-EXCLUDE-STOP
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

\begin{document}
Test
\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # RAW block should protect EXCLUDE markers from being processed
        assert "FLACHTEX-EXCLUDE-START" in str(result)
        assert "This should NOT be excluded (protected by RAW)" in str(result)

    def test_multiple_uncomment_blocks_revealing_raw(self, tmp_path):
        r"""Test multiple UNCOMMENT blocks each revealing RAW blocks."""
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% \newcommand{\cmdA}[1]{A: #1}
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% \newcommand{\cmdB}[1]{B: #1}
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

\begin{document}
Test
\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Both RAW blocks should be preserved
        assert r"\newcommand{\cmdA}[1]{A: #1}" in str(result)
        assert r"\newcommand{\cmdB}[1]{B: #1}" in str(result)

        # Both should have parameters protected
        assert str(result).count("#1") >= 2


class TestRawInImportedFiles:
    r"""Test RAW blocks in files revealed by UNCOMMENT."""

    def test_uncomment_reveals_input_containing_raw(self, tmp_path):
        r"""
        Test UNCOMMENT revealing \input to file with RAW blocks.

        This should work without iterative processing since each file
        is processed independently.
        """
        main_file = tmp_path / "main.tex"
        chapter_file = tmp_path / "chapter.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% \input{chapter.tex}
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        chapter_file.write_text(
            r"""\section{Chapter}

%%FLACHTEX-RAW-START
\newcommand{\chaptercmd}[1]{Chapter: #1}
%%FLACHTEX-RAW-STOP
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # Chapter should be included
        assert r"\section{Chapter}" in str(result)

        # RAW block from chapter should be preserved
        assert r"\newcommand{\chaptercmd}[1]{Chapter: #1}" in str(result)
        assert "#1" in str(result)


class TestIterativeProcessingEdgeCases:
    r"""Test edge cases for iterative RAW processing."""

    def test_uncomment_reveals_exclude_containing_raw(self, tmp_path):
        r"""
        Test UNCOMMENT revealing EXCLUDE block that contains RAW.

        The RAW block is inside an EXCLUDE block that's revealed by UNCOMMENT,
        so the RAW block should be excluded (not processed).
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-EXCLUDE-START
% %%FLACHTEX-RAW-START
% This RAW content is inside EXCLUDE
% %%FLACHTEX-RAW-STOP
% %%FLACHTEX-EXCLUDE-STOP
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # The EXCLUDE block (revealed by UNCOMMENT) should remove its content
        assert "This RAW content is inside EXCLUDE" not in str(result)

    def test_deeply_nested_uncomment_revealing_raw(self, tmp_path):
        r"""Test multiple levels of UNCOMMENT, with deepest revealing RAW."""
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-UNCOMMENT-START
% % %%FLACHTEX-RAW-START
% % \newcommand{\nested}[1]{Nested: #1}
% % %%FLACHTEX-RAW-STOP
% %%FLACHTEX-UNCOMMENT-STOP
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))
        result = preprocessor.expand_file(str(main_file))

        # After two levels of UNCOMMENT, RAW block should be revealed
        assert r"\newcommand{\nested}[1]{Nested: #1}" in str(result)
        assert "#1" in str(result)

    def test_convergence_no_infinite_loop(self, tmp_path):
        r"""
        Test that iterative processing converges (no infinite loop).

        Even with complex nesting, processing should stabilize after
        a few iterations.
        """
        main_file = tmp_path / "main.tex"

        # Complex but finite nesting
        main_file.write_text(
            r"""\documentclass{article}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-UNCOMMENT-START
% % %%FLACHTEX-UNCOMMENT-START
% % % %%FLACHTEX-RAW-START
% % % \newcommand{\deep}[1]{Deep: #1}
% % % %%FLACHTEX-RAW-STOP
% % %%FLACHTEX-UNCOMMENT-STOP
% %%FLACHTEX-UNCOMMENT-STOP
%%FLACHTEX-UNCOMMENT-STOP

\begin{document}
Test
\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        # This should complete without hanging
        import time

        start = time.time()
        result = preprocessor.expand_file(str(main_file))
        elapsed = time.time() - start

        # Should complete quickly (not hanging in infinite loop)
        assert elapsed < 2.0, "Processing took too long, possible infinite loop"

        # Final result should have RAW block
        assert r"\newcommand{\deep}[1]{Deep: #1}" in str(result)


class TestRawBlockValidation:
    r"""Test that RAW block validation still works with iterative processing."""

    def test_uncomment_reveals_unclosed_raw_raises_error(self, tmp_path):
        r"""Test that unclosed RAW block (revealed by UNCOMMENT) raises error."""
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% Unclosed RAW block
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        # Should raise ValueError for unclosed RAW block
        with pytest.raises(ValueError, match="Unclosed RAW block"):
            preprocessor.expand_file(str(main_file))

    def test_uncomment_reveals_raw_with_import_raises_error(self, tmp_path):
        r"""
        Test that RAW block with import (revealed by UNCOMMENT) raises error.

        RAW blocks should not contain imports, even if revealed by UNCOMMENT.
        """
        main_file = tmp_path / "main.tex"

        main_file.write_text(
            r"""\documentclass{article}
\begin{document}

%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% \input{somefile.tex}
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP

\end{document}
"""
        )

        preprocessor = Preprocessor(str(tmp_path))

        # Should raise ValueError for import in RAW block
        with pytest.raises(ValueError, match="Import commands not allowed in RAW blocks"):
            preprocessor.expand_file(str(main_file))
