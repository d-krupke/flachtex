# flachtex

A tool to flatten complex LaTeX-documents, i.e., create a single file out of a complex
document structure.
Its primary feature is that it remembers from which file (and position within the file)
each character came. Additionally, it has some extra commands that allow to explicitly
tell *flachtex* what to do, even in complicated scenarios.

There are many other tools to flatten LaTeX, but I did not find a tool that could handle
my dissertation (that uses *subimport* and has some logic involved) and also was capable
of telling you where each word came from. The second part is important for automated 
spell, grammar, and code checker: For long documents, you do not want to search where
this error was made (in general, no auto-fix is possible). *flachtex* solves this problem
but is slower than other tools because of the additional bookkeeping. There is still
room to improve the performance, but it is fast enough for me.

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

## Installation

*flachtex* is available via pip: `pip install flachtex`.

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


**This tool is still work in progress.**