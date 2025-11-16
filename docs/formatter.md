# LaTeX Formatter for Diff-Friendly Output

The flachtex formatter makes LaTeX documents more suitable for version control by implementing "one sentence per line" formatting and optional environment indentation.

## Overview

The formatter provides two main features:

1. **Sentence-per-line**: Splits text at sentence boundaries (periods, question marks, exclamation marks)
2. **Environment indentation**: Indents nested LaTeX environments with configurable spacing

These features make diffs more readable and meaningful in version control systems like Git.

## Use Cases

### Use Case 1: Format Only (No Flattening)

Format a single LaTeX file without expanding `\input` or `\include` commands.

**Command:**
```bash
flachtex --no-expand --format --indent 2 main.tex
```

**Use this when:**
- You want to format a single file while keeping `\input` references intact
- You're working on a specific section file and don't need to see included content
- You want faster processing for large multi-file projects

**Example:**

Input file (`main.tex`):
```latex
\documentclass{article}
\begin{document}
\section{Introduction}
This is the first sentence. This is the second sentence. And a third.
\input{sections/related-work.tex}
\section{Conclusion}
Final thoughts here. More conclusions.
\end{document}
```

Output:
```latex
\documentclass{article}
\begin{document}
\section{Introduction}
This is the first sentence.
This is the second sentence.
And a third.
\input{sections/related-work.tex}
\section{Conclusion}
Final thoughts here.
More conclusions.
\end{document}
```

### Use Case 2: Full Flachtex (Flattening + Formatting)

Expand all `\input` and `\include` commands, apply other processing (comments removal, changes package, etc.), then format.

**Command:**
```bash
flachtex --format --indent 2 main.tex
```

**With additional processing:**
```bash
flachtex --comments --changes --format --indent 2 main.tex
```

**Use this when:**
- Preparing a manuscript for journal submission (single file required)
- Creating a standalone version for collaborators
- Generating diff-friendly output from a multi-file project
- Running automated checks on the complete document

**Example:**

Input files:
```latex
% main.tex
\documentclass{article}
\begin{document}
\input{intro.tex}
\input{methods.tex}
\end{document}
```

```latex
% intro.tex
\section{Introduction}
First sentence. Second sentence.
```

```latex
% methods.tex
\section{Methods}
We used approach X. Results were good.
\begin{itemize}
\item First item. Additional details.
\item Second item.
\end{itemize}
```

Output (flattened and formatted):
```latex
\documentclass{article}
\begin{document}
\section{Introduction}
First sentence.
Second sentence.
\section{Methods}
We used approach X.
Results were good.
\begin{itemize}
  \item First item.
  Additional details.
  \item Second item.
\end{itemize}
\end{document}
```

## Command-Line Options

### Formatting Options

| Option | Default | Description |
|--------|---------|-------------|
| `--format` | disabled | Enable sentence-per-line formatting |
| `--indent N` | 0 | Indent environments with N spaces (0 = disabled) |
| `--no-expand` | disabled | Don't expand `\input`/`\include` (format only) |

### Processing Options (used with flattening)

| Option | Description |
|--------|-------------|
| `--comments` | Remove LaTeX comments |
| `--changes` | Process `\usepackage{changes}` commands |
| `--changes_prefix` | Use prefixed changes commands (ch*) |
| `--todos` | Remove todo-notes |
| `--newcommand` | Substitute custom commands |

### Output Options

| Option | Description |
|--------|-------------|
| `--to_json` | Output as JSON with metadata |
| `--attach` | Attach source files to JSON output |

## Examples

### Example 1: Basic Formatting

Format with default settings (sentence-per-line, no indentation):

```bash
flachtex --no-expand --format main.tex > formatted.tex
```

### Example 2: Format with Indentation

Format with 2-space indentation:

```bash
flachtex --no-expand --format --indent 2 main.tex > formatted.tex
```

### Example 3: Indentation Only

Apply indentation without sentence splitting:

```bash
flachtex --no-expand --indent 2 main.tex > indented.tex
```

### Example 4: Full Pipeline for Submission

Flatten, remove comments, format, and indent:

```bash
flachtex --comments --format --indent 2 main.tex > submission.tex
```

### Example 5: Process Changes Package

Flatten and process track changes:

```bash
flachtex --changes --format --indent 2 main.tex > processed.tex
```

## Formatting Behavior

### Blank Line Normalization

The formatter automatically normalizes excessive blank lines that often accumulate during flattening:

**Normalized:**
- Multiple consecutive blank lines (3+) are reduced to one blank line
- Leading blank lines are removed
- Trailing blank lines are reduced to at most one newline

**Preserved:**
- Single blank lines (paragraph separators)
- Blank lines within verbatim environments

This prevents the excessive newlines that flachtex may create when combining multiple files, while maintaining proper paragraph structure.

### Sentence Splitting

The formatter splits text at sentence boundaries while being intelligent about:

**Handled correctly:**
- Abbreviations: `Dr.`, `Mr.`, `Mrs.`, `Prof.`, `et al.`, `i.e.`, `e.g.`, etc.
- Decimal numbers: `3.14`, `0.5`
- Escaped periods: `e\.g\.`
- Ellipsis: `...`
- Comments: Kept with their sentence

**Preserved as-is:**
- Blank lines (paragraph separators)
- Existing line breaks
- LaTeX commands and their arguments

### Indentation

**Indented environments:**
- All standard environments: `itemize`, `enumerate`, `figure`, `table`, etc.
- Math environments: `equation`, `align`, `gather`, etc.
- Custom environments

**Not indented (preserved as-is):**
- **Verbatim-like**: `verbatim`, `lstlisting`, `minted`, `algorithmic`
- **Document-level**: `document`, `abstract`

**Nesting:**
Progressive indentation for nested environments:
```latex
\begin{itemize}
  \item Level 1
  \begin{enumerate}
    \item Level 2
    \begin{itemize}
      \item Level 3
    \end{itemize}
  \end{enumerate}
\end{itemize}
```

## Integration with Git

### Pre-commit Hook

Format files before committing:

```bash
#!/bin/bash
# .git/hooks/pre-commit

for file in $(git diff --cached --name-only --diff-filter=ACM | grep '\.tex$'); do
    flachtex --no-expand --format --indent 2 "$file" > "${file}.formatted"
    mv "${file}.formatted" "$file"
    git add "$file"
done
```

### Diff Tool Configuration

Configure git to use formatted output for diffs:

```bash
# .gitattributes
*.tex diff=latex

# .git/config
[diff "latex"]
    textconv = flachtex --no-expand --format --indent 2
```

## Programmatic Usage

### Python API

```python
from flachtex import FileFinder, Preprocessor
from flachtex.formatter import format_latex
from flachtex.traceable_string import TraceableString

# Option 1: Format only (no flattening)
with open("main.tex", "r") as f:
    content = f.read()
doc = TraceableString(content, origin="main.tex")
formatted = format_latex(doc, indent=2, sentence_per_line=True)
print(str(formatted))

# Option 2: Flatten then format
preprocessor = Preprocessor("./")
doc = preprocessor.expand_file("main.tex")
formatted = format_latex(doc, indent=2, sentence_per_line=True)
print(str(formatted))

# Option 3: Indentation only (no sentence splitting)
formatted = format_latex(doc, indent=2, sentence_per_line=False)
```

## Best Practices

### For Version Control

1. **Commit formatted files**: Use `--format --indent 2` before committing
2. **Consistent formatting**: Apply to all files in the repository
3. **CI/CD integration**: Check formatting in continuous integration

### For Collaboration

1. **Single file for submission**: Use full flattening with `--format --indent 2`
2. **Review drafts**: Use `--no-expand --format` to review specific sections
3. **Track changes**: Combine with `--changes` for collaborative editing

### For Large Projects

1. **Format individual files**: Use `--no-expand` for faster processing
2. **Flatten for final version**: Use full flattening only when needed
3. **Selective processing**: Combine options based on needs

## Troubleshooting

### Issue: Incorrect indentation

**Problem**: Some environments are indented when they shouldn't be (or vice versa)

**Solution**: Check if the environment should be in the `DOCUMENT_LEVEL_ENVIRONMENTS` or `VERBATIM_ENVIRONMENTS` lists in `formatter.py`

### Issue: Sentences split incorrectly

**Problem**: Abbreviations or special cases cause unwanted splits

**Solution**: Add the abbreviation to the `abbreviations` list in `_find_sentence_boundaries()`

### Issue: Output is garbled

**Problem**: Very rare, usually related to complex origin tracking

**Solution**: File a bug report with a minimal example

## Performance

- **Format only**: Very fast, processes single file
- **Full flattening**: Depends on number and size of included files
- **Large documents**: Consider using `--no-expand` for iterative work

Typical processing times:
- Small document (<100 lines): <1 second
- Medium document (1000 lines): <2 seconds
- Large document (10000 lines): <10 seconds

## Related Documentation

- [Main README](../README.md)
- [Flachtex Documentation](https://github.com/d-krupke/flachtex)
- [LaTeX Best Practices for Version Control](https://github.com/dspinellis/latex-advice)
