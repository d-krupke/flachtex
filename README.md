# flachtex

Tools (e.g. [cktex](https://www.nongnu.org/chktex/),
[YaLafi](https://github.com/matze-dd/YaLafi),
[TeXtidote](https://github.com/sylvainhalle/textidote)) for analyzing LaTeX-documents
often only work on single files, making them tedious
to use for complex documents. The purpose of
*flachtex* is to preprocess even complicated LaTeX-documents such that they can be
easily analyzed as a single document. The important part is that it also provides
a data structure to reverse that process and get the origin of a specific part
(allowing to trace issues back to their source). While there are other tools to flatten
LaTeX, they all are neither capable of dealing with complex imports nor do they allow
you to trace back to the origins.

Noteable features of *flachtex* are:

* Flattening of LaTeX-documents with various rules (`\include`, `\input`, `\subimport`
  ,`%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]`...).
* Any character in the output can be traced back to its origin.
* Remove comments.
* Remove `\todo{...}`.
* Remove highlights of `\usepackage{changes}`. (This substitution is actually more robust
  than the one supplied with the package.)
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

## Usage

### CLI

*flachtex* comes with a simple CLI, if you don't want to use it via Python.

```
usage: flachtex [-h] [--to_json] [--comments] [--attach] [--changes]
              [--changes_prefix] [--todos] [--newcommand]
              path

flachtex: Traceable LaTeX flattening.

positional arguments:
  path              Path to main.tex

options:
  -h, --help        show this help message and exit
  --to_json         Return a json.
  --comments        Remove comments.
  --attach          Attach sources to json.
  --changes         Replace the commands of the changes package.
  --changes_prefix  Use the prefix option in changes.
  --todos           Remove todo-notes.
  --newcommand      Automatically substitute custom commands.
```

### Python

```python
from flachtex import Preprocessor, remove_comments
from flachtex.rules import TodonotesRule

# basic usage
preprocessor = Preprocessor("/path/to/latex_document/")
preprocessor.skip_rules.append(TodonotesRule())  # remove todos
doc = preprocessor.expand_file("main.tex")

# remove the comments (optional)
doc = remove_comments(doc)

# The document can be read as a string (but contains also further information)
print(f"The process LaTeX-document is {doc}")

# Get the used files
for f, data in preprocessor.structure.items():
    print(f"Used file {f} which contains the content '{data['content']}' and includes"
          f" the files {data['includes']}.")

# query origin
origin_file, pos = doc.get_origin_of_line(line=3, col=6)
print(f"The seventh character of the fourth line origins from file {origin_file}:{pos}.")
origin_file, pos = doc.get_origin(5)
print(f"The sixth character  origins from file {origin_file}:{pos}.")
```

## Features

### Flatten LaTeX-documents

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

### Path Resolution

*flachtex* will first try to resolve the inclusion relative to the calling file.
If no file is found (also trying with additional ".tex"), it tries the document folder
(cwd) and the folder of the root tex-file. Afterwards, it tries the parent directories.

If this is not sufficient, try to use the `%%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]`
option.

### Extending the tool

*flachtex* has a modular structure that allows it to receive
additional rules or replace existing ones. You can find the current rules in
[./flachtex/rules](./flachtex/rules).

It is important that the matches do not overlap for SkipRules and ImportRules.
For efficiency, *flachtex* will first find the matches and only then includes the
files. Overlapping matches would need a complex resolution and my result in unexpected
output. (It would not be too difficult to add some simple resolution rules instead of
simply throwing an exception).

### Usage for cleaning 'changes' of '\usepackage{changes}'

The [changes-package](https://ctan.org/pkg/changes?lang=en) is helpful for highlighting
the changes, which is a good practice, e.g., when writing journal papers (which
usually have to go through one or two reviewing iterations). These can of course
disturb automatic language checkers and they have to be removed in the end. The script
that is attached to the original package unfortunately is not compatible with some
usages (e.g., comments can lead it astray).
*flachtex* is capable of removing the highlights done with *changes* in a robust way.
There are some nasty ways to trick it, but if you use brackets, it should work fine and
independent of escaped symbols, comments, or line breaks.

### Substitution of \newcommand

It is reasonably common to create your own commands with `\newcommand', e.g., for some
terms which you may want to change later. If you want to analyze the tex-document, this
can become cumbersome. Thus, *flachtex* gives you the option to automatically substitute
such commands.

The primary reason I added this functionality to this tool (and not some higher level
tool)
is that I also saw that some people define their own \input/\include commands, which
could not be imported easily without this feature.

## Changelog

### 0.3.4

* Dealing with `\xspace` in command substitution.

### 0.3.3

* `FileFinder` now has a default and allows to set a new root.
* Command substitution for commands without parameters made more accurate.
* `from_json` for `TraceableString`

**This tool is still work in progress.**