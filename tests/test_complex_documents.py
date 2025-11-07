"""
Tests for complex real-world LaTeX document structures.

This test suite covers realistic academic paper and book structures
with multiple chapters, sections, figures, and bibliographies.
"""


from flachtex import FileFinder, Preprocessor, remove_comments
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


class TestAcademicPaperStructure:
    """Tests simulating typical academic paper structures."""

    def test_standard_paper_structure(self):
        """Test a standard academic paper with multiple sections."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{abstract.tex}\n"
                "\\input{intro.tex}\n"
                "\\input{methods.tex}\n"
                "\\input{results.tex}\n"
                "\\input{conclusion.tex}\n"
                "\\end{document}\n"
            ),
            "abstract.tex": "\\begin{abstract}\nAbstract text\n\\end{abstract}\n",
            "intro.tex": "\\section{Introduction}\nIntro text\n",
            "methods.tex": "\\section{Methods}\nMethods text\n",
            "results.tex": "\\section{Results}\nResults text\n",
            "conclusion.tex": "\\section{Conclusion}\nConclusion text\n",
        }
        result = flatten(document)
        assert "\\documentclass{article}" in result
        assert "Abstract text" in result
        assert "Introduction" in result
        assert "Methods" in result
        assert "Results" in result
        assert "Conclusion" in result

    def test_paper_with_nested_sections(self):
        """Test paper with sections including subsections."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{sections/intro.tex}\n"
                "\\input{sections/background.tex}\n"
                "\\end{document}\n"
            ),
            "sections/intro.tex": (
                "\\section{Introduction}\n"
                "Intro\n"
                "\\input{motivation.tex}\n"
                "\\input{contributions.tex}\n"
            ),
            "sections/motivation.tex": "\\subsection{Motivation}\nMotivation text\n",
            "sections/contributions.tex": "\\subsection{Contributions}\nContributions\n",
            "sections/background.tex": "\\section{Background}\nBackground text\n",
        }
        result = flatten(document)
        assert "Introduction" in result
        assert "Motivation" in result
        assert "Contributions" in result
        assert "Background" in result


class TestBookStructure:
    """Tests simulating book or thesis structures."""

    def test_book_with_chapters(self):
        """Test a book structure with multiple chapters."""
        document = {
            "main.tex": (
                "\\documentclass{book}\n"
                "\\begin{document}\n"
                "\\include{chapters/chapter1}\n"
                "\\include{chapters/chapter2}\n"
                "\\include{chapters/chapter3}\n"
                "\\end{document}\n"
            ),
            "chapters/chapter1.tex": "\\chapter{First Chapter}\nChapter 1 content\n",
            "chapters/chapter2.tex": "\\chapter{Second Chapter}\nChapter 2 content\n",
            "chapters/chapter3.tex": "\\chapter{Third Chapter}\nChapter 3 content\n",
        }
        result = flatten(document)
        assert "First Chapter" in result
        assert "Second Chapter" in result
        assert "Third Chapter" in result

    def test_thesis_structure(self):
        """Test a typical PhD thesis structure."""
        document = {
            "main.tex": (
                "\\documentclass{book}\n"
                "\\begin{document}\n"
                "\\input{frontmatter/title.tex}\n"
                "\\input{frontmatter/abstract.tex}\n"
                "\\input{chapters/introduction.tex}\n"
                "\\input{chapters/background.tex}\n"
                "\\input{chapters/methodology.tex}\n"
                "\\input{chapters/results.tex}\n"
                "\\input{chapters/conclusion.tex}\n"
                "\\input{backmatter/bibliography.tex}\n"
                "\\end{document}\n"
            ),
            "frontmatter/title.tex": "\\title{My Thesis}\n\\maketitle\n",
            "frontmatter/abstract.tex": "\\begin{abstract}\nAbstract\n\\end{abstract}\n",
            "chapters/introduction.tex": (
                "\\chapter{Introduction}\n"
                "\\input{motivation.tex}\n"
                "\\input{objectives.tex}\n"
            ),
            "chapters/motivation.tex": "\\section{Motivation}\nMotivation text\n",
            "chapters/objectives.tex": "\\section{Objectives}\nObjectives text\n",
            "chapters/background.tex": "\\chapter{Background}\nBackground text\n",
            "chapters/methodology.tex": "\\chapter{Methodology}\nMethodology text\n",
            "chapters/results.tex": "\\chapter{Results}\nResults text\n",
            "chapters/conclusion.tex": "\\chapter{Conclusion}\nConclusion text\n",
            "backmatter/bibliography.tex": "\\bibliography{refs}\n",
        }
        result = flatten(document)
        assert "My Thesis" in result
        assert "Introduction" in result
        assert "Motivation" in result
        assert "Objectives" in result
        assert "Background" in result


class TestGraphicsAndFigures:
    """Tests for documents with graphics and figures."""

    def test_paper_with_figures(self):
        """Test paper with figure includes."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{intro.tex}\n"
                "\\input{figures/fig1.tex}\n"
                "\\input{results.tex}\n"
                "\\end{document}\n"
            ),
            "intro.tex": "\\section{Introduction}\nIntro text\n",
            "figures/fig1.tex": (
                "\\begin{figure}\n"
                "\\includegraphics{images/plot.pdf}\n"
                "\\caption{A plot}\n"
                "\\end{figure}\n"
            ),
            "results.tex": "\\section{Results}\nResults text\n",
        }
        result = flatten(document)
        assert "Introduction" in result
        assert "includegraphics" in result
        assert "A plot" in result
        assert "Results" in result

    def test_subimport_with_graphics(self):
        """Test subimport correctly handles relative graphics paths."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{figures/}{plot1}\n"
                "\\end{document}\n"
            ),
            "figures/plot1.tex": (
                "\\begin{figure}\n"
                "\\includegraphics{data.pdf}\n"
                "\\includegraphics{./local.pdf}\n"
                "\\caption{Plot}\n"
                "\\end{figure}\n"
            ),
        }
        result = flatten(document)
        # The subimport rule should adjust graphics paths
        assert "includegraphics" in result
        assert "figures/" in result or "./figures/" in result


class TestMultiFileOrganization:
    """Tests for different ways of organizing multi-file projects."""

    def test_one_file_per_section(self):
        """Test organizing with one file per section."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{sec1.tex}\n"
                "\\input{sec2.tex}\n"
                "\\input{sec3.tex}\n"
                "\\end{document}\n"
            ),
            "sec1.tex": "\\section{Section 1}\n\\input{sec1_subsec1.tex}\n",
            "sec1_subsec1.tex": "\\subsection{Subsection 1.1}\nText\n",
            "sec2.tex": "\\section{Section 2}\nText\n",
            "sec3.tex": "\\section{Section 3}\nText\n",
        }
        result = flatten(document)
        assert "Section 1" in result
        assert "Subsection 1.1" in result
        assert "Section 2" in result
        assert "Section 3" in result

    def test_directory_per_chapter(self):
        """Test organizing with a directory per chapter."""
        document = {
            "main.tex": (
                "\\documentclass{book}\n"
                "\\begin{document}\n"
                "\\input{chapter1/main.tex}\n"
                "\\input{chapter2/main.tex}\n"
                "\\end{document}\n"
            ),
            "chapter1/main.tex": (
                "\\chapter{First}\n\\input{intro.tex}\n\\input{content.tex}\n"
            ),
            "chapter1/intro.tex": "\\section{Introduction}\nIntro 1\n",
            "chapter1/content.tex": "\\section{Content}\nContent 1\n",
            "chapter2/main.tex": (
                "\\chapter{Second}\n\\input{intro.tex}\n\\input{content.tex}\n"
            ),
            "chapter2/intro.tex": "\\section{Introduction}\nIntro 2\n",
            "chapter2/content.tex": "\\section{Content}\nContent 2\n",
        }
        result = flatten(document)
        assert "First" in result
        assert "Intro 1" in result
        assert "Content 1" in result
        assert "Second" in result
        assert "Intro 2" in result
        assert "Content 2" in result


class TestCollaborativeStructures:
    """Tests for structures common in collaborative writing."""

    def test_author_based_organization(self):
        """Test organizing sections by author."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{alice/intro.tex}\n"
                "\\input{bob/methods.tex}\n"
                "\\input{alice/results.tex}\n"
                "\\input{bob/conclusion.tex}\n"
                "\\end{document}\n"
            ),
            "alice/intro.tex": "\\section{Introduction}\nIntro by Alice\n",
            "bob/methods.tex": "\\section{Methods}\nMethods by Bob\n",
            "alice/results.tex": "\\section{Results}\nResults by Alice\n",
            "bob/conclusion.tex": "\\section{Conclusion}\nConclusion by Bob\n",
        }
        result = flatten(document)
        assert "Introduction" in result
        assert "Methods" in result
        assert "Results" in result
        assert "Conclusion" in result

    def test_version_controlled_structure(self):
        """Test structure with draft and final versions."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{sections/intro_v2.tex}\n"
                "\\input{sections/methods_final.tex}\n"
                "\\end{document}\n"
            ),
            "sections/intro_v2.tex": "\\section{Introduction}\nIntro v2\n",
            "sections/methods_final.tex": "\\section{Methods}\nMethods final\n",
        }
        result = flatten(document)
        assert "Introduction" in result
        assert "Methods" in result


class TestConditionalInclusion:
    """Tests for conditional inclusion patterns."""

    def test_optional_appendix(self):
        """Test structure with optional appendix."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{main_content.tex}\n"
                "\\input{appendix.tex}\n"
                "\\end{document}\n"
            ),
            "main_content.tex": "\\section{Main}\nMain content\n",
            "appendix.tex": "\\appendix\n\\section{Extra}\nExtra content\n",
        }
        result = flatten(document)
        assert "Main" in result
        assert "Extra" in result

    def test_supplementary_material(self):
        """Test including supplementary material."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\input{paper.tex}\n"
                "\\clearpage\n"
                "\\input{supplementary/supplement.tex}\n"
                "\\end{document}\n"
            ),
            "paper.tex": "\\section{Paper}\nPaper content\n",
            "supplementary/supplement.tex": (
                "\\section{Supplementary}\n\\input{details.tex}\n"
            ),
            "supplementary/details.tex": "\\subsection{Details}\nDetails\n",
        }
        result = flatten(document)
        assert "Paper" in result
        assert "Supplementary" in result
        assert "Details" in result


class TestRealWorldPatterns:
    """Tests based on real-world LaTeX document patterns."""

    def test_ieee_conference_paper(self):
        """Test typical IEEE conference paper structure."""
        document = {
            "main.tex": (
                "\\documentclass[conference]{IEEEtran}\n"
                "\\begin{document}\n"
                "\\title{Paper Title}\n"
                "\\maketitle\n"
                "\\input{abstract.tex}\n"
                "\\input{introduction.tex}\n"
                "\\input{related_work.tex}\n"
                "\\input{approach.tex}\n"
                "\\input{evaluation.tex}\n"
                "\\input{conclusion.tex}\n"
                "\\end{document}\n"
            ),
            "abstract.tex": "\\begin{abstract}\nAbstract\n\\end{abstract}\n",
            "introduction.tex": "\\section{Introduction}\nIntro\n",
            "related_work.tex": "\\section{Related Work}\nRelated\n",
            "approach.tex": "\\section{Our Approach}\nApproach\n",
            "evaluation.tex": (
                "\\section{Evaluation}\n"
                "\\input{eval/setup.tex}\n"
                "\\input{eval/results.tex}\n"
            ),
            "eval/setup.tex": "\\subsection{Experimental Setup}\nSetup\n",
            "eval/results.tex": "\\subsection{Results}\nResults\n",
            "conclusion.tex": "\\section{Conclusion}\nConclusion\n",
        }
        result = flatten(document)
        assert "Paper Title" in result
        assert "Abstract" in result
        assert "Introduction" in result
        assert "Related Work" in result
        assert "Evaluation" in result
        assert "Experimental Setup" in result

    def test_arxiv_preprint_structure(self):
        """Test typical arXiv preprint structure."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\usepackage{arxiv}\n"
                "\\begin{document}\n"
                "\\input{metadata.tex}\n"
                "\\input{content/main_content.tex}\n"
                "\\end{document}\n"
            ),
            "metadata.tex": (
                "\\title{Title}\n"
                "\\author{Authors}\n"
                "\\maketitle\n"
                "\\begin{abstract}\nAbstract\n\\end{abstract}\n"
            ),
            "content/main_content.tex": (
                "\\input{intro.tex}\n"
                "\\input{method.tex}\n"
                "\\input{experiments.tex}\n"
                "\\input{conclusion.tex}\n"
            ),
            "content/intro.tex": "\\section{Introduction}\nIntro\n",
            "content/method.tex": "\\section{Method}\nMethod\n",
            "content/experiments.tex": "\\section{Experiments}\nExperiments\n",
            "content/conclusion.tex": "\\section{Conclusion}\nConclusion\n",
        }
        result = flatten(document)
        assert "Title" in result
        assert "Abstract" in result
        assert "Introduction" in result
        assert "Method" in result
        assert "Experiments" in result
        assert "Conclusion" in result


class TestMixedSubimportPatterns:
    """Tests for complex subimport scenarios."""

    def test_subimport_with_nested_includes(self):
        """Test subimport that includes other files."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{chapters/}{chapter1}\n"
                "\\end{document}\n"
            ),
            "chapters/chapter1.tex": (
                "\\chapter{Chapter 1}\n\\input{section1.tex}\n\\input{section2.tex}\n"
            ),
            "chapters/section1.tex": "\\section{Section 1}\nS1\n",
            "chapters/section2.tex": "\\section{Section 2}\nS2\n",
        }
        result = flatten(document)
        assert "Chapter 1" in result
        assert "Section 1" in result
        assert "Section 2" in result

    def test_chained_subimports(self):
        """Test subimports within subimports."""
        document = {
            "main.tex": (
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "\\subimport{part1/}{main}\n"
                "\\subimport{part2/}{main}\n"
                "\\end{document}\n"
            ),
            "part1/main.tex": ("\\section{Part 1}\n\\subimport{sub/}{content}\n"),
            "part1/sub/content.tex": "\\subsection{Part 1 Sub}\nContent 1\n",
            "part2/main.tex": ("\\section{Part 2}\n\\subimport{sub/}{content}\n"),
            "part2/sub/content.tex": "\\subsection{Part 2 Sub}\nContent 2\n",
        }
        result = flatten(document)
        assert "Part 1" in result
        assert "Content 1" in result
        assert "Part 2" in result
        assert "Content 2" in result
