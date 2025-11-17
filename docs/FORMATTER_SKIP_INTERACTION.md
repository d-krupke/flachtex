# Formatter and Skip Rules Interaction

## Overview

This document explains how the **formatter** and **skip rules** interact in flachtex, answering the critical question: *What happens when users want both formatted output AND selective content removal?*

## TL;DR - What Users Should Know

**Standard Workflow (Recommended):**
1. Flatten document with `flachtex` → skip rules apply automatically during preprocessing
2. Call `format_latex()` on the result → get formatted, clean output
3. **Result**: Efficient (skip content never gets formatted), clean (no skip markers in output)

**Key Behaviors:**
- ✅ Skip rules apply **BEFORE** formatting (during flattening)
- ✅ Skip markers (`%%FLACHTEX-SKIP-START/STOP`) are preserved during formatting (they're comments)
- ✅ Blank lines left by removed skip blocks are normalized by the formatter
- ✅ Both workflows work: skip→format (efficient) or format→skip (flexible)

---

## Detailed Analysis

### 1. When Do Skip Rules Apply?

**During Preprocessing (Standard Path):**

Skip rules are applied in `Preprocessor.read_file()`:

```python
def read_file(self, file_path):
    content = TraceableString(self.file_finder.read(file_path), origin=file_path)
    content = apply_skip_rules(content, self.skip_rules)  # ← Skip rules apply here
    return apply_substitution_rules(content, self.substitution_rules)
```

This means:
- Skip rules run **during flattening**, before formatting
- Content inside `%%FLACHTEX-SKIP-START/STOP` blocks is removed immediately
- The formatter never sees skipped content

**Timeline:**
```
User has document with skip markers
    ↓
Preprocessor.expand_file() called
    ↓
For each file:
  1. Read file
  2. Apply skip rules ← REMOVED HERE
  3. Apply substitution rules
  4. Find imports
  5. Recursively process included files
    ↓
Return flattened document (skip blocks already gone)
    ↓
(Optional) Call format_latex() ← Skip markers already removed
    ↓
Final output: formatted, without skip blocks
```

### 2. What Users Expect vs. What Happens

#### Expectation 1: "Skipped content won't appear in my formatted output"
✅ **WORKS AS EXPECTED**

```latex
This is sentence one. This is sentence two.
%%FLACHTEX-SKIP-START
This should not appear. Neither should this.
%%FLACHTEX-SKIP-STOP
This is sentence three.
```

After flatten + format:
```latex
This is sentence one.
This is sentence two.
This is sentence three.
```

**Why**: Skip rules remove the block during flattening, before formatting runs.

#### Expectation 2: "Blank lines left by skip blocks will be cleaned up"
✅ **WORKS AS EXPECTED**

```latex
First paragraph.

%%FLACHTEX-SKIP-START
Skip this paragraph.
%%FLACHTEX-SKIP-STOP

Second paragraph.
```

After flatten → becomes:
```latex
First paragraph.


Second paragraph.
```

After format → becomes:
```latex
First paragraph.

Second paragraph.
```

**Why**: Formatter's blank line normalization reduces excessive newlines.

#### Expectation 3: "Skip markers won't interfere with formatting"
✅ **WORKS AS EXPECTED**

Skip markers are comments (`%%`), so:
- `CommentDetector` identifies them as protected ranges
- They don't get reformatted (stay on their own lines)
- They can still be found by skip rules if applied after formatting

#### Expectation 4: "I can format first, then decide what to skip"
✅ **WORKS**, but less efficient

```python
# Format first
formatted = format_latex(content)  # Skip markers preserved (they're comments)

# Then skip
result = apply_skip_rules(formatted, [BasicSkipRule()])
```

This works because skip markers are preserved during formatting, but it's inefficient (formats content that will be removed).

#### Expectation 5: "Indentation will work correctly after skip blocks are removed"
✅ **WORKS AS EXPECTED**

```latex
\begin{itemize}
%%FLACHTEX-SKIP-START
\item Skip this
%%FLACHTEX-SKIP-STOP
\item Keep this
\end{itemize}
```

After flatten + format with indent=2:
```latex
\begin{itemize}
  \item Keep this
\end{itemize}
```

**Why**: Skip rules run before indentation, so environment tracking sees the correct structure.

### 3. Edge Cases and Gotchas

#### Gotcha 1: Manual formatting doesn't apply skip rules
```python
# This ONLY formats, does NOT skip
result = format_latex(my_content)
# Skip markers will still be present in output!
```

**Solution**: Use the preprocessor to flatten first, which applies skip rules automatically.

#### Gotcha 2: Skip markers must be on their own lines

**This works:**
```latex
Text before.
%%FLACHTEX-SKIP-START
Content to skip.
%%FLACHTEX-SKIP-STOP
Text after.
```

**This does NOT work:**
```latex
Text %%FLACHTEX-SKIP-START inline content %%FLACHTEX-SKIP-STOP more text
```

The regex requires `^\\s*%%FLACHTEX-SKIP` (start of line).

#### Gotcha 3: Formatting skipped content is wasted work

If you format **then** skip:
```python
formatted = format_latex(content)  # Formats EVERYTHING, including skip blocks
result = apply_skip_rules(formatted, [BasicSkipRule()])  # Removes formatted skip blocks
```

The content inside skip blocks gets formatted, then immediately removed. Inefficient!

**Better**: Let preprocessor handle it:
```python
flattened = preprocessor.expand_file("main.tex")  # Skip rules already applied
formatted = format_latex(flattened)  # Only formats content that stays
```

### 4. Recommended Workflows

#### Workflow A: Journal Submission (Most Common)

**Goal**: Flatten multi-file project, remove draft notes, format for diff-friendly version control.

```python
from flachtex import Preprocessor, format_latex

# 1. Set up preprocessor with skip rules (already included by default)
preprocessor = Preprocessor(".")
# BasicSkipRule is in preprocessor.skip_rules by default

# 2. Flatten (skip rules apply automatically)
flattened = preprocessor.expand_file("main.tex")

# 3. Format for readability
formatted = format_latex(flattened, sentence_per_line=True, indent=2)

# 4. Output
with open("submission.tex", "w") as f:
    f.write(str(formatted))
```

**Result**:
- Multi-file project → single file
- Draft notes removed
- One sentence per line (git-friendly)
- Properly indented environments

#### Workflow B: Manual Format Then Skip (Advanced)

**Goal**: Format LaTeX source manually, then apply skip rules.

```python
from flachtex import TraceableString, format_latex
from flachtex.rules import BasicSkipRule, apply_skip_rules

# 1. Read content
with open("document.tex") as f:
    content = TraceableString(f.read(), "document.tex")

# 2. Format first
formatted = format_latex(content)  # Skip markers preserved

# 3. Then apply skip rules
result = apply_skip_rules(formatted, [BasicSkipRule()])

# 4. Output
with open("output.tex", "w") as f:
    f.write(str(result))
```

**Use when**:
- Working with single-file documents
- Need to see formatted output before deciding what to skip
- Skip markers are already in formatted source

### 5. Performance Considerations

**Skip → Format (Efficient):**
- Skip blocks removed: O(n) where n = document size
- Formatting: O(m) where m = remaining content (m < n)
- **Total**: O(n + m)

**Format → Skip (Less Efficient):**
- Formatting: O(n) where n = entire document (including skip blocks)
- Skip blocks removed: O(n)
- **Total**: O(2n)

**Difference**: Formatting skipped content is wasted work. For large skip blocks (e.g., removing entire draft sections), the difference can be significant.

### 6. Implementation Details

**Why Skip Markers Are Preserved During Formatting:**

1. Skip markers start with `%%` (LaTeX comments)
2. `CommentDetector` identifies them:
   ```python
   # In formatter/detectors.py
   class CommentDetector:
       def find_all(self, content: str) -> list[Range]:
           for match in re.finditer(r'(?<!\\)%.*', content):
               ranges.append(Range(match.start(), match.end()))
   ```
3. Comments are added to `protected_ranges`
4. Sentence splitter and other formatters skip protected ranges
5. Skip markers remain intact, on their own lines

**Why This Design Makes Sense:**
- Flexibility: Users can format→skip or skip→format
- Robustness: Skip markers work even if formatting happens first
- Simplicity: Skip markers are just special comments, treated uniformly

### 7. Testing

See `tests/test_formatter_skip_interaction.py` for comprehensive tests covering:
- ✅ Skip during flatten, then format (standard workflow)
- ✅ Format first, then skip (alternative workflow)
- ✅ Blank line normalization after skip blocks
- ✅ Indentation with skip blocks
- ✅ Skip markers preserved during formatting
- ✅ Multiple skip blocks
- ✅ Empty skip blocks

All 12 tests pass, confirming correct behavior.

---

## Summary

**What works well:**
1. ✅ Standard workflow (flatten→format) is efficient and clean
2. ✅ Skip markers are preserved during formatting (flexible)
3. ✅ Blank lines normalized automatically
4. ✅ Both operation orders work correctly

**What users should know:**
1. ⚠️ Skip rules apply during flattening (before formatting) by default
2. ⚠️ Manual formatting doesn't automatically skip - use preprocessor for that
3. ⚠️ Format→skip works but is less efficient
4. ⚠️ Skip markers must be on their own lines

**Best practice:**
Use `Preprocessor.expand_file()` to flatten (applies skip rules), then `format_latex()` to format. This is the most efficient and predictable workflow.
