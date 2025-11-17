# Flachtex Markers Analysis

## Current Situation

We currently have **TWO different types** of markers with **fundamentally different purposes**:

### 1. Skip Markers (Remove from Output)

**Purpose**: Remove content completely from the flattened document

**Markers**:
- `%%FLACHTEX-SKIP-START` / `%%FLACHTEX-SKIP-STOP` - Explicit removal
- `\begin{comment}` / `\end{comment}` - Comment package (if CommentsPackageSkipRule used)
- `\todo{...}` - Todonotes package (if TodonotesRule used)

**What happens**: Content is DELETED during preprocessing, never appears in output

**Use cases**:
- Draft notes that should never be published: "TODO: Add citation"
- Internal comments: "This section needs review by John"
- Disabled content: Old text you want to keep in source but not in output

**Example**:
```latex
Published text.
%%FLACHTEX-SKIP-START
This won't appear in the output at all.
%%FLACHTEX-SKIP-STOP
More published text.
```

Output:
```latex
Published text.
More published text.
```

### 2. Protected Regions (Keep in Output, Don't Reformat)

**Purpose**: Preserve content in output exactly as written (no formatting changes)

**Detection**: Automatic based on LaTeX environment detection

**Protected regions**:
- Verbatim environments: `\begin{verbatim}`, `\begin{lstlisting}`, `\begin{minted}`, `\verb|...|`
- Math environments: `$...$`, `\[...\]`, `\begin{equation}`, `\begin{align}`, etc.
- Comments: `%...` (preserved, not split)

**What happens**: Content STAYS in output but formatter doesn't touch it

**Use cases**:
- Code listings (verbatim)
- Mathematical formulas (math mode)
- Line comments (%)

**Example**:
```latex
This sentence will be split.
\begin{verbatim}
This. Won't. Be. Split. It stays exactly as written.
\end{verbatim}
Another sentence that will be split.
```

Output (with formatting):
```latex
This sentence will be split.
\begin{verbatim}
This. Won't. Be. Split. It stays exactly as written.
\end{verbatim}
Another sentence that will be split.
```

---

## The Gap You Identified

### Missing: Explicit "Don't Format" Marker

**What users might expect**: `%%FLACHTEX-FORMATTER-SKIP-START/STOP`

**Purpose**: Keep content in output but prevent formatter from touching it

**Current workaround**: Wrap in `\begin{verbatim}` but this changes LaTeX interpretation!

**Problem scenarios where this is needed**:

#### 1. Pre-formatted Tables
```latex
This paragraph should be formatted.

%%FLACHTEX-FORMATTER-SKIP-START
% This table is carefully formatted, don't touch it!
\begin{tabular}{lll}
Column1 & Column2 & Column3 \\
A       & B       & C       \\
\end{tabular}
%%FLACHTEX-FORMATTER-SKIP-STOP

This paragraph should also be formatted.
```

**Why verbatim won't work**: `\begin{verbatim}` would prevent LaTeX from interpreting `\begin{tabular}`, so the table wouldn't render.

#### 2. Manually Formatted Paragraphs
```latex
%%FLACHTEX-FORMATTER-SKIP-START
This paragraph has
specific line breaks
for poetic or stylistic reasons.
Don't reformat it.
%%FLACHTEX-FORMATTER-SKIP-STOP
```

**Why verbatim won't work**: Verbatim changes font, disables LaTeX commands, etc.

#### 3. Complex Formatting Already Done
```latex
%%FLACHTEX-FORMATTER-SKIP-START
% Already formatted by another tool or manually, leave it alone
\section{Introduction}
First sentence.
Second sentence.
Third sentence.
%%FLACHTEX-FORMATTER-SKIP-STOP
```

#### 4. Pseudocode or Algorithms (Not Code Listings)
```latex
%%FLACHTEX-FORMATTER-SKIP-START
Algorithm:
  Step 1: Initialize x = 0
  Step 2: While x < 10
    Step 3: x = x + 1
%%FLACHTEX-FORMATTER-SKIP-STOP
```

**Why verbatim won't work**: May want LaTeX commands like `\textbf{x}` to still work.

---

## Current Behavior Summary

| Scenario | Marker Type | In Output? | Reformatted? |
|----------|-------------|------------|--------------|
| Draft notes | `%%FLACHTEX-SKIP-START/STOP` | ❌ No | N/A |
| Code listing | `\begin{verbatim}` | ✅ Yes | ❌ No |
| Math formula | `$x = y$` | ✅ Yes | ❌ No (but indented) |
| Comment | `% text` | ✅ Yes | ❌ No |
| **Pre-formatted table** | **No marker available!** | ✅ Yes | ⚠️ **YES (problem!)** |
| **Manual formatting** | **No marker available!** | ✅ Yes | ⚠️ **YES (problem!)** |

---

## User Confusion Risk

Your observation is spot on. Users might think:

❌ **"I'll use `%%FLACHTEX-SKIP` to tell the formatter to skip this section"**
   - Result: Content is REMOVED from output (not what they wanted!)

✅ **What they actually want**: "Keep this in output but don't reformat it"
   - Current solution: Wrap in `\begin{verbatim}` (but changes LaTeX interpretation)
   - Better solution: Need a `%%FLACHTEX-FORMATTER-SKIP` marker

---

## Recommendation

We should add `%%FLACHTEX-FORMATTER-SKIP-START/STOP` markers:

**Purpose**: Include in output but exclude from formatting

**Behavior**:
1. During preprocessing: Marker lines are preserved (they're comments)
2. During formatting: Content between markers is added to protected_ranges
3. Result: Content appears in output exactly as written

**Implementation**: Add a new detector in `formatter/detectors.py`:

```python
class FormatterSkipDetector:
    """Detects %%FLACHTEX-FORMATTER-SKIP regions to preserve formatting."""

    def find_all(self, content: str) -> list[Range]:
        pattern = r"(?P<skip_block>%%FLACHTEX-FORMATTER-SKIP-START.*?%%FLACHTEX-FORMATTER-SKIP-STOP)"
        ranges = []
        for match in re.finditer(pattern, content, re.DOTALL | re.MULTILINE):
            ranges.append(Range(match.start("skip_block"), match.end("skip_block")))
        return ranges
```

**Usage**:
```latex
Normal text that gets formatted.

%%FLACHTEX-FORMATTER-SKIP-START
This text appears in output.
But doesn't get reformatted.
Manual line breaks preserved.
%%FLACHTEX-FORMATTER-SKIP-STOP

More normal text that gets formatted.
```

**Benefits**:
- Clear distinction between "remove" (SKIP) and "don't format" (FORMATTER-SKIP)
- Users have explicit control over formatting behavior
- No need to misuse verbatim environments
- LaTeX commands still work inside formatter-skip blocks

---

## Summary

You're absolutely correct:

1. ✅ **We have skip markers** (`%%FLACHTEX-SKIP-START/STOP`) → **removes from output**
2. ✅ **We have automatic protection** (verbatim, math, comments) → **keeps in output, no reformat**
3. ❌ **We DON'T have explicit "don't format" markers** → **GAP IN FUNCTIONALITY**

The most important marker for users is indeed **"do not touch the lines in between"** (keep in output, preserve formatting), and we're currently missing an explicit way to mark that.

Should we implement `%%FLACHTEX-FORMATTER-SKIP-START/STOP`?
