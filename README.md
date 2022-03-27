# flachtex

A simple Python-library to flatten LaTeX, thus it creates a single LaTeX-file out of a 
complex multi-file LaTeX-document. It is slower than comparable tools but has some
important features, such as:
1. Allows skipping parts enclosed by LaTeX-comments
2. Allows explicit includes in case the include can not directly be deduced from the source (e.g., because it is done by an evaluation)
3. Supports subimport
4. Remembers where every part comes from and allows exporting this information as json.
5. Can remove comments.

You can use it directly as Python-module or use its CLI.

```python
usage: flachtex [-h] [--to_json] [--remove_comments] path

flachtex: Traceable LaTeX flattening.

positional arguments:
  path               Path to main.tex

optional arguments:
  -h, --help         show this help message and exit
  --to_json          Return a json.
  --remove_comments  Remove comments.
```

You can easily add additional rules. Just check out the `rules.py` to see the current
rules. They are all implemented as regular expressions but also other methods are
supported.

To skip some parts, use
```latex
%%FLACHTEX-SKIP-START
This part is ignored and will not be part of the output.
%%FLACHTEX-SKIP-STOP
```

To import some explicit file, use
```latex
%%FLACHTEX-EXPLICIT-IMPORT[path/to/file]
%%FLACHTEX-SKIP-START
Complex import logic that cannot be parsed by flachtex.
%%FLACHTEX-SKIP-STOP
```

**This tool is still work in progress.**