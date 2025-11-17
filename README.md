# flachtex

Tools (e.g. [cktex](https://www.nongnu.org/chktex/),
[YaLafi](https://github.com/matze-dd/YaLafi),
[TeXtidote](https://github.com/sylvainhalle/textidote)) for analyzing
LaTeX-documents often only work on single files, making them tedious to use for
complex documents. The purpose of _flachtex_ is to preprocess even complicated
LaTeX-documents such that they can be easily analyzed as a single document. The
important part is that it also provides a data structure to reverse that process
and get the origin of a specific part (allowing to trace issues back to their
source). While there are other tools to flatten LaTeX, they all are neither
capable of dealing with complex imports nor do they allow you to trace back to
the origins.

Notable features of _flachtex_ are:

- Flattening of LaTeX-documents with various rules (`\include`, `\input`,
  `\subimport` ,`%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]`...).
- Any character in the output can be traced back to its origin.
- **Diff-friendly formatter** for version control (one sentence per line, environment indentation).
- Remove comments.
- Remove `\todo{...}`.
- Remove highlights of `\usepackage{changes}`. (This substitution is actually
  more robust than the one supplied with the package.)
- Substitute commands defined by `\newcommand`.
- A modular design that allows to add additional rules.

## Installation

_flachtex_ is available via pip: `pip install flachtex`.

## Example

Let us look on a quick example that shows the power of the tool. We have a
LaTeX-document consisting of three files.

_main.tex_

```tex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts,amsthm}
\usepackage{todonotes}
\usepackage{xspace}

\newcommand{\importantterm}{\emph{ImportantTerm}\xspace}

%%FLACHTEX-EXCLUDE-START
Technicalities (e.g., configuration of Journal-template) that we want to exclude.
%%FLACHTEX-EXCLUDE-STOP

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

_part_a.tex_

```tex
\subsection{Part A}

This is Part A. We can also use \importantterm here.
```

_part_b.tex_

```tex
\subsection{Part B}
And Part B.
```

_flachtex_ can create the following output for us that is much easier to
analyze.

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

(currently, _flachtex_ will actually add some redundant empty lines, but those
usually do no harm and could be easily eliminated by some simple
postprocessing.)

## Usage

### CLI

_flachtex_ provides a comprehensive command-line interface for flattening, formatting, and preprocessing LaTeX documents.

**Quick Start:**

```bash
# Basic flattening (multi-file → single file)
flachtex main.tex > output.tex

# Format for version control (recommended)
flachtex --format --indent 2 main.tex > output.tex

# Clean for submission (remove comments, TODOs)
flachtex --comments --todos main.tex > submission.tex
```

**Common Workflows:**

```bash
# arXiv submission (flatten only)
flachtex main.tex > arxiv_submission.tex

# Journal submission (flatten + clean)
flachtex --comments --todos main.tex > journal_submission.tex

# Version control (format without flattening)
flachtex --no-expand --format --indent 2 main.tex

# Full pipeline (flatten, format, clean)
flachtex --format --indent 2 --comments --todos main.tex > clean.tex
```

**Available Options:**

Run `flachtex --help` for full documentation. Key option groups:

- **Processing:** `--no-expand`, `--newcommand`, `--changes`
- **Filtering:** `--comments`, `--todos`
- **Formatting:** `--format`, `--indent N`
- **Output:** `--to_json`, `--attach`

See [docs/formatter.md](docs/formatter.md) for complete formatter documentation.

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
    print(
        f"Used file {f} which contains the content '{data['content']}' and includes"
        f" the files {data['includes']}."
    )

# query origin
origin_file, pos = doc.get_origin_of_line(line=3, col=6)
print(
    f"The seventh character of the fourth line origins from file {origin_file}:{pos}."
)
origin_file, pos = doc.get_origin(5)
print(f"The sixth character  origins from file {origin_file}:{pos}.")
```

## Features

### Diff-Friendly Formatter

_flachtex_ includes an optional formatter that makes LaTeX documents more suitable for version control:

**One sentence per line:**
- Splits text at sentence boundaries (periods, question marks, exclamation marks)
- Intelligently handles abbreviations (Dr., et al., i.e., etc.)
- Preserves decimal numbers (3.14)
- Keeps comments with their sentences

**Environment indentation:**
- Configurable indentation (default: 2 spaces)
- Progressive indentation for nested environments
- Excludes verbatim-like environments (verbatim, lstlisting, minted)
- Document-level environments (document, abstract) don't cause indentation

**Blank line normalization:**
- Reduces excessive blank lines (3+) to one blank line
- Removes leading/trailing blank lines
- Preserves paragraph structure

**Two main use cases:**

1. **Format only** (without flattening):
   ```bash
   flachtex --no-expand --format --indent 2 main.tex
   ```
   Keeps `\input` commands intact, formats a single file.

2. **Full pipeline** (flattening + formatting):
   ```bash
   flachtex --format --indent 2 main.tex
   ```
   Expands all includes, then formats the result.

See [docs/formatter.md](docs/formatter.md) for detailed documentation.

### Protection Markers

_flachtex_ provides four types of comment-based markers to control processing:

| Marker | Purpose | Use Case |
|--------|---------|----------|
| `%%FLACHTEX-EXCLUDE-START/STOP` | Remove content from output | Draft notes, WIP sections, supplementary material |
| `%%FLACHTEX-UNCOMMENT-START/STOP` | Activate commented content | Path fixes, version swapping, conditional content |
| `%%FLACHTEX-RAW-START/STOP` | Bypass ALL preprocessing | Complex `\newcommand` definitions |
| `%%FLACHTEX-NO-FORMAT-START/STOP` | Skip formatting only | Manually formatted tables, equations |

**Examples:**

```latex
% Exclude work-in-progress sections
%%FLACHTEX-EXCLUDE-START
\section{Future Work}
This section is incomplete.
%%FLACHTEX-EXCLUDE-STOP

% Activate alternative content (e.g., fix paths after flattening)
%%FLACHTEX-EXCLUDE-START
\graphicspath{{chapters/figures/}}  % Multi-file version
%%FLACHTEX-EXCLUDE-STOP
%%FLACHTEX-UNCOMMENT-START
% \graphicspath{{figures/}}  % Flattened version
%%FLACHTEX-UNCOMMENT-STOP

% Protect complex macros
%%FLACHTEX-RAW-START
\newcommand{\mycite}[2]{\cite{#1}\footnote{#2}}
%%FLACHTEX-RAW-STOP

% Preserve table formatting
%%FLACHTEX-NO-FORMAT-START
\begin{tabular}{lrr}
Method    & Acc   & Time \\
Baseline  & 87\%  & 10s  \\
\end{tabular}
%%FLACHTEX-NO-FORMAT-STOP

% Combine UNCOMMENT with RAW for version-specific complex macros
%%FLACHTEX-UNCOMMENT-START
% %%FLACHTEX-RAW-START
% \newcommand{\complexmacro}[2]{#1 and #2}  % Protected from preprocessing
% %%FLACHTEX-RAW-STOP
%%FLACHTEX-UNCOMMENT-STOP
```

**Iterative Processing:** RAW extraction and UNCOMMENT processing happen in a loop, allowing UNCOMMENT to reveal RAW blocks. This enables version swapping where alternative versions include RAW-protected complex macros.

**📘 Complete tested examples:**
- `tests/test_examples.py` - 10 real-world examples (multi-file flattening, arXiv/journal workflows)
- `tests/test_uncomment.py` - 17 comprehensive UNCOMMENT tests (path fixing, version swapping, grammar checker support)
- `tests/test_raw_recursive.py` - 9 iterative processing tests (UNCOMMENT revealing RAW blocks, nested processing)

Run `pytest tests/test_examples.py tests/test_uncomment.py tests/test_raw_recursive.py -v` to verify all examples work.

### Flatten LaTeX-documents

Currently, _flachtex_ supports file inclusions of the following form:

```
% native includes/inputs
\include{path/file.tex}
\input{path/file.tex}

% subimport
\subimport{path}{file}
\subimport*{path}{file}

% manual import
%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]
%%FLACHTEX-EXCLUDE-START
Complex import logic that cannot be parsed by flachtex.
%%FLACHTEX-EXCLUDE-STOP
```

### Path Resolution

_flachtex_ will first try to resolve the inclusion relative to the calling file.
If no file is found (also trying with additional ".tex"), it tries the document
folder (cwd) and the folder of the root tex-file. Afterwards, it tries the
parent directories.

If this is not sufficient, try to use the
`%%FLACHTEX-EXPLICIT-IMPORT[path/file.tex]` option.

### Extending the tool

_flachtex_ has a modular structure that allows it to receive additional rules or
replace existing ones. You can find the current rules in
[./flachtex/rules](./flachtex/rules).

It is important that the matches do not overlap for SkipRules and ImportRules.
For efficiency, _flachtex_ will first find the matches and only then includes
the files. Overlapping matches would need a complex resolution and my result in
unexpected output. (It would not be too difficult to add some simple resolution
rules instead of simply throwing an exception).

### Usage for cleaning 'changes' of '\usepackage{changes}'

The [changes-package](https://ctan.org/pkg/changes?lang=en) is helpful for
highlighting the changes, which is a good practice, e.g., when writing journal
papers (which usually have to go through one or two reviewing iterations). These
can of course disturb automatic language checkers and they have to be removed in
the end. The script that is attached to the original package unfortunately is
not compatible with some usages (e.g., comments can lead it astray). _flachtex_
is capable of removing the highlights done with _changes_ in a robust way. There
are some nasty ways to trick it, but if you use brackets, it should work fine
and independent of escaped symbols, comments, or line breaks.

### Substitution of \newcommand

It is reasonably common to create your own commands with `\newcommand', e.g.,
for some terms which you may want to change later. If you want to analyze the
tex-document, this can become cumbersome. Thus, _flachtex_ gives you the option
to automatically substitute such commands.

The primary reason I added this functionality to this tool (and not some higher
level tool) is that I also saw that some people define their own \input/\include
commands, which could not be imported easily without this feature.

## Changelog

- **1.0.0** Major release with UNCOMMENT markers and iterative processing
  - Added `%%FLACHTEX-UNCOMMENT-START/STOP` markers to activate commented content
  - Implemented iterative RAW/UNCOMMENT processing (UNCOMMENT can reveal RAW blocks)
  - Improved CLI interface with organized argument groups and comprehensive examples
  - Fixed blank line normalization after comment removal
  - Added 29 new tests (17 UNCOMMENT tests + 12 recursive tests)
  - Enhanced documentation with complete tested examples
- **0.7.0** Adding formatter
- **0.6.0** Significant refactoring.
- **0.5.0** Now will only replace `\input` and `\include` commands for which the
  file exists. Otherwise, it will leave the command as is. This allows you to
  use `\input` and `\include` commands for files that are not part of the
  document, e.g., for some automatically generated files.
- **0.4.0** Support for the `comments` package.
- **0.3.15** Fixes [Issue #8](https://github.com/d-krupke/flachtex/issues/8)
- **0.3.14** Bugfix by Nutron2112
- **0.3.13** improves robustness of command parsing (of potentially faulty LaTeX
  code)
- **0.3.12** Made parsing of non utf-8 encodings more robust. Some templates you
  get have very strange file encodings. You don't always convert them manually
  to utf-8.
- **0.3.11** `newcommand` should work reliably with multiple arguments now
  (hopefully).
- **0.3.10** Support for `newcommand*` substitution
- **0.3.9**: PEP compliance which may have created problems in environments
  without setuptools
- **0.3.8**: Substituting newcommands is no longer enabled by default.
- **0.3.7**: Versions got slightly mixed up. Should be fixed now.
- **0.3.6** bugfix: Using findall instead of finditer.
- **0.3.4** Dealing with `\xspace` in command substitution.
- **0.3.3**
  - `FileFinder` now has a default and allows to set a new root.
  - Command substitution for commands without parameters made more accurate.
  - `from_json` for `TraceableString`

**This tool is still work in progress.**
