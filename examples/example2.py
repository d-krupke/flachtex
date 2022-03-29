from flachtex.comments import remove_comments
from flachtex import FileFinder, expand_file_and_attach_sources

# For this example, we provide the files as dictionary. You can skip the part with the
# FileFinder if you are working on your file system.
document = {
    "main.tex":
        r"""
% This is a test document. We skip the common preamble of LaTeX.
\section{Main}
Hello!
\include{./modules/part1.tex}
\input{./modules/part2.tex}
%%FLACHTEX-EXPLICIT-IMPORT[./modules/part3.tex]
%%FLACHTEX-SKIP-START
\compleximportlogic{part3.tex}
%%FLACHTEX-SKIP-STOP
    """,
    "modules/part1.tex": "I am part1!\n",
    "modules/part2.tex": "I am part2!\n",
    "modules/part3.tex": "I am part3!\n",
}

file_finder = FileFinder("/", "main.tex", document)
flat_doc, sources = expand_file_and_attach_sources("main.tex", file_finder=file_finder)

print(remove_comments(flat_doc).to_json())
print(sources)