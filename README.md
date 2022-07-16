# flachtex

Tools (e.g. [cktex](https://www.nongnu.org/chktex/),
[YaLafi](https://github.com/matze-dd/YaLafi), 
[TeXtidote](https://github.com/sylvainhalle/textidote)) for analyzing LaTeX-documents often only work on single files, making them tedious
to use for complex documents. The purpose of
*flachtex* is to preprocess even complicated LaTeX-documents such that they can be
easily analyzed as a single document. The important part is that it also provides
a data structure to reverse that process and get the origin of a specific part
(allowing to trace issues back to their source). While there are other tools to flatten
LaTeX, they all are neither capable of dealing with complex imports nor do they allow
you to trace back to the origins.

Noteable features of *flachtex* are:
* Flattening of LaTeX-documents with various rules (`\include`, `\input`, `\subimport`,`%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]`...).
* Any character in the output can be traced back to its origin.
* Remove comments.
* Remove `\todo{...}`.
* Remove highlights of `\usepackage{changes}`. (This substitution is actually more robust than the one supplied with the package.)
* Substitute commands defined by `\newcommand`.
* A modular design that allows to add additional rules.

## Installation

*flachtex* is available via pip: `pip install flachtex`.

## Example

Let us look on a quick example that shows the power of the tool. We have a LaTeX-document
consisting of three files.

*main.tex*
```tex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts,amsthm}
\usepackage{todonotes}
\usepackage{xspace}

\newcommand{\importantterm}{\emph{ImportantTerm}\xspace}

%%FLACHTEX-SKIP-START
Technicalities (e.g., configuration of Journal-template) that we want to skip.
%%FLACHTEX-SKIP-STOP

\begin{document}

\section{Introduction}

\todo[inline]{This TODO will not be shown because we don't want to analyze it.}

Let us use \importantterm here.

% including part_a with 'input' and without extension
\input{./part_a}

% including part_b with 'include' and with extension
\include{./part_b.tex}

\end{document}
```

*part_a.tex*
```tex
\subsection{Part A}

This is Part A. We can also use \importantterm here.
```

*part_b.tex*
```tex
\subsection{Part B}
And Part B.
```

*flachtex* can create the following output for us that is much easier to analyze.

```tex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts,amsthm}
\usepackage{todonotes}
\usepackage{xspace}

\newcommand{\importantterm}{\emph{ImportantTerm}\xspace}

\begin{document}

\section{Introduction}

Let us use \emph{ImportantTerm}\xspace here.

\subsection{Part A}

This is Part A. We can also use \emph{ImportantTerm}\xspace here.

\subsection{Part B}
And Part B.

\end{document}
```
(currently, *flachtex* will actually add some redundant empty lines, but those usually
do no harm and could be easily eliminated by some simple postprocessing.)

## Flatten LaTeX-documents

Currently, *flachtex* supports file inclusions of the following form:
```
% native includes/inputs
\include{path/file.tex}
\input{path/file.tex}

% subimport
\subimport{path}{file}
\subimport*{path}{file}

% manual import
%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]
%%FLACHTEX-SKIP-START
Complex import logic that cannot be parsed by flachtex.
%%FLACHTEX-SKIP-STOP
```



## CLI

The tool comes with a simple CLI
```
usage: flachtex [-h] [--to_json] [--remove_comments] path

flachtex: Traceable LaTeX flattening.

positional arguments:
  path               Path to main.tex

optional arguments:
  -h, --help         show this help message and exit
  --to_json          Return a json.
  --remove_comments  Remove comments.
  --attach           Attach sources to json.
```

## Python

You can also directly use it in Python.
```python

from flachtex.comments import remove_comments
from flachtex import FileFinder, expand_file

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
flat_doc = expand_file("main.tex", file_finder=file_finder)
# you can also use flat_doc.get_origin(pos)

print(remove_comments(flat_doc).to_json())
```
returns 
```json
{'content': '\n\\section{Main}\nHello!\nI am part1!\n\nI am part2!\n\nI am part3!\n\n\n    ', 
  'origins': [{'begin': 0, 'end': 1, 'origin': 'main.tex', 'offset': 0}, 
    {'begin': 1, 'end': 23, 'origin': 'main.tex', 'offset': 66}, 
    {'begin': 23, 'end': 35, 'origin': 'modules/part1.tex', 'offset': 0},
    {'begin': 35, 'end': 36, 'origin': 'main.tex', 'offset': 117},
    {'begin': 36, 'end': 48, 'origin': 'modules/part2.tex', 'offset': 0},
    {'begin': 48, 'end': 49, 'origin': 'main.tex', 'offset': 145}, 
    {'begin': 49, 'end': 61, 'origin': 'modules/part3.tex', 'offset': 0},
    {'begin': 61, 'end': 62, 'origin': 'main.tex', 'offset': 193}, 
    {'begin': 62, 'end': 67, 'origin': 'main.tex', 'offset': 267}]}
```
(the superfluous linebreaks and spaces are still an issue but not an urgent one)

## Path Resolution

*flachtex* will first try to resolve the inclusion relative to the calling file.
If no file is found (also trying with additional ".tex"), it tries the document folder
(cwd) and the folder of the root tex-file. Afterwards, it tries the parent directories.

If this is not sufficient, try to use the `%%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]`
option.

## Extending the tool

*flachtex* has a modular structure that allows it to receive
additional rules or replace existing ones. You can find the current rules in
[./flachtex/rules.py](./flachtex/rules.py). All current rules are implemented as
regular expressions.

It is important that the matches do not overlap.
For efficiency, *flachtex* will first find the matches and only then includes the 
files. Overlapping matches would need a complex resolution and my result in unexpected
output. (It would not be too difficult to add some simple resolution rules instead of
simply throwing an exception).


## Usage for cleaning 'changes' of '\usepackage{changes}'

The [changes-package](https://ctan.org/pkg/changes?lang=en) is helpful for highlighting
the changes, which is a good practice, e.g., when writing journal papers (which 
usually have to go through one or two reviewing iterations). These can of course
disturb automatic language checkers and they have to be removed in the end. The script
that is attached to the original package unfortunately is not compatible with some
usages (e.g., comments can lead it astray).
*flachtex* is capable of removing the highlights done with *changes* in a robust way.
There are some nasty ways to trick it, but if you use brackets, it should work fine and
independent of escaped symbols, comments, or line breaks.

## Substitution of \newcommand

It is reasonably common to create your own commands with `\newcommand', e.g., for some
terms which you may want to change later. If you want to analyze the tex-document, this
can become cumbersome. Thus, *flachtex* gives you the option to automatically substitute 
such commands.

The primary reason I added this functionality to this tool (and not some higher level tool)
is that I also saw that some people define their own \input/\include commands, which
could not be imported easily without this feature.


**This tool is still work in progress.**