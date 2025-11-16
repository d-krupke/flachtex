# LaTeX Command Expansion and Whitespace Handling Analysis

## Overview

This document analyzes how flachtex should handle whitespace when expanding `\newcommand` definitions to match LaTeX's behavior as closely as possible.

## LaTeX's Whitespace Rules

### Rule 1: Control Sequences Swallow ONE Space

Commands made of letters (control sequences) like `\LaTeX`, `\foo`, or `\newcommand` swallow **exactly one** following space character:

```latex
\LaTeX is great     → "LaTeXis great" (space swallowed)
\LaTeX  is great    → "LaTeX is great" (first space swallowed, second remains)
\LaTeX\ is great    → "LaTeX is great" (explicit space)
\LaTeX{} is great   → "LaTeX is great" (empty braces prevent swallowing)
```

**Key points:**
- Only ONE space is swallowed
- Only the first space in a sequence of multiple spaces
- Empty braces `{}` prevent space swallowing
- Explicit space `\ ` adds a space that won't be swallowed

### Rule 2: Control Symbols Don't Swallow Spaces

Commands made of a single non-letter character (control symbols) like `\$`, `\%`, `\&` do **NOT** swallow spaces:

```latex
\$ 5        → "$ 5" (space preserved)
\%          → "%" (no space to swallow)
```

### Rule 3: Commands with Arguments

Commands with braced arguments do **NOT** swallow trailing spaces (the braces act as delimiters):

```latex
\textbf{bold} text          → "bold text" (space preserved)
\newcommand{\foo}{bar} baz  → "bar baz" (space after } preserved)
```

### Rule 4: The \xspace Package

The `\xspace` package provides intelligent space handling. When a command definition ends with `\xspace`, it automatically adds space when appropriate:

```latex
\newcommand{\latex}{LaTeX\xspace}
\latex is great             → "LaTeX is great"
\latex, it's great          → "LaTeX, it's great"
```

## Current Flachtex Implementation

### Location

The whitespace handling logic is in `src/flachtex/command_substitution.py`, lines 125-136.

### Implementation

```python
if (
    self._space_sub
    and definition.num_parameters == 0
    and not str(sub).strip().endswith("\\xspace")
):
    # The usage of a command like "\\cmd bla" is actually equivalent to
    # "\\cmd{}bla". This function tries to simulate this.
    while content[end] == " ":
        end += 1
    if end != match.end:
        sub += TraceableString("{}", None)  # add non-space separator
yield Substitution(match.start, end, sub)
```

### Current Behavior

The implementation intends to:
1. Check if this is a zero-parameter command (line 127)
2. Check if the replacement doesn't end with `\xspace` (line 128)
3. Swallow all consecutive spaces after the command (line 132)
4. Add empty braces `{}` to the replacement to prevent LaTeX from swallowing more spaces (line 135)

## The Bug

### Root Cause

**Line 132: `while content[end] == " ":`**

The bug is that `content[end]` returns a `TraceableString` object, not a string character. Therefore, the comparison `content[end] == " "` always evaluates to `False`.

```python
>>> content = TraceableString("\\cmd asd", None)
>>> content[5]
TraceableString( , [None[0:1:+5]])  # Returns TraceableString object
>>> content[5] == " "
False  # Comparison fails!
>>> str(content[5]) == " "
True   # Need to convert to string first
```

### Consequence

The while loop **never executes**, so:
- No spaces are swallowed
- No `{}` is added to the replacement
- The current behavior doesn't match LaTeX semantics

### Evidence

Test results from `tests/test_command_whitespace.py`:

```python
Input:  "\cmd text"
Output: "REPLACEMENT text"  # BUG: should be "REPLACEMENTtext" or "REPLACEMENT{}text"

Input:  "\cmd  text" (2 spaces)
Output: "REPLACEMENT  text"  # BUG: should be "REPLACEMENT text"
```

## Proposed Fixes

### Option 1: Simple String Conversion (Recommended)

Change line 132 to convert to string:

```python
while str(content[end]) == " ":
    end += 1
```

**Pros:**
- Minimal change
- Clear intent
- Fixes the immediate bug

**Cons:**
- Creates many small string objects during iteration

### Option 2: Slice Comparison

Use string slicing instead:

```python
while end < len(content) and str(content[end:end+1]) == " ":
    end += 1
```

**Pros:**
- Also works correctly
- Bounds checking included

**Cons:**
- Slightly more verbose
- Still creates string objects

### Option 3: Direct String Access

Access the underlying string:

```python
content_str = str(content)
while end < len(content_str) and content_str[end] == " ":
    end += 1
```

**Pros:**
- Most efficient (single string conversion)
- Clearest logic

**Cons:**
- Deviates from current pattern of using TraceableString methods

## Additional Considerations

### 1. Should We Swallow Only ONE Space or ALL Spaces?

**LaTeX behavior:** Swallows only the first space

**Current implementation (when bug is fixed):** Swallows all consecutive spaces

**Recommendation:** Change to match LaTeX more closely by swallowing only one space:

```python
if end < len(content_str) and content_str[end] == " ":
    end += 1  # Swallow only one space
    if end != match.end:
        sub += TraceableString("{}", None)
```

### 2. Should We Add `{}` or Just Remove the Space?

**Options:**
- **Remove space only:** `\cmd text` → `REPLACEMENTtext`
- **Add `{}`:** `\cmd text` → `REPLACEMENT{}text`

**Recommendation:** Add `{}` (current intent) because:
1. When flachtex outputs its result, it goes back into LaTeX
2. Without `{}`, LaTeX would swallow the next space again
3. The `{}` acts as a delimiter to prevent further space swallowing

### 3. Control Sequences vs Control Symbols

The current implementation doesn't distinguish between:
- Control sequences (letter-based): `\foo` (should swallow space)
- Control symbols (non-letter): `\$` (should NOT swallow space)

This is probably acceptable because:
1. Most `\newcommand` definitions are letter-based
2. Single-character commands are rarely defined with `\newcommand`
3. Adding this distinction would increase complexity significantly

### 4. Interaction with \xspace

Current check: `not str(sub).strip().endswith("\\xspace")`

This is correct because:
- If the replacement ends with `\xspace`, LaTeX will handle spacing intelligently
- We don't need to swallow spaces or add `{}`
- However, `strip()` removes whitespace which could affect edge cases

**Recommendation:** Use exact string matching:

```python
not str(sub).endswith("\\xspace")
```

## Implementation Strategy

### Phase 1: Fix the Bug (Minimal Change)

1. Change line 132 to: `while end < len(str(content)) and str(content)[end] == " ":`
2. Run existing tests to ensure no regressions
3. Verify new tests pass

### Phase 2: Match LaTeX Behavior More Closely (Optional)

1. Swallow only ONE space instead of all spaces
2. Update tests to reflect expected behavior
3. Document the change

### Phase 3: Advanced Improvements (Future)

1. Distinguish between control sequences and control symbols
2. Handle edge cases with tabs and other whitespace
3. Add more comprehensive tests

## Testing Strategy

Created `tests/test_command_whitespace.py` with:

1. **Current behavior tests** - Document actual behavior (including bugs)
2. **Bug documentation tests** - Explicitly demonstrate the bug
3. **Expected behavior tests** - Marked as skipped, show desired behavior after fix

This approach ensures:
- Current functionality doesn't break
- Bug is clearly documented
- Expected behavior is clearly defined
- Easy to verify when fix is implemented

## Conclusion

The whitespace handling in flachtex's command substitution has a bug that prevents it from working as intended. The fix is straightforward (string conversion in the comparison), but there are several design decisions to consider about how closely to match LaTeX's actual behavior versus what's most practical for a preprocessor tool.

**Recommendation:**
1. Fix the immediate bug (Phase 1)
2. Consider matching LaTeX's "one space" behavior more closely
3. Keep the `{}` addition for safety
4. Document any intentional deviations from LaTeX semantics
