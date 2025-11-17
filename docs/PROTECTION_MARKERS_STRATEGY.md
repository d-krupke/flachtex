# Protection Markers Strategy

## Current Situation Analysis

### What We Have
1. **Skip markers** (`%%FLACHTEX-SKIP-START/STOP`) - Remove from output
2. **Auto-detected protection** (verbatim, math) - Formatting only
3. **Manual formatting** - User calls `format_latex()` in code

### What's Missing
1. **Explicit "don't format" marker** - Keep in output, but don't reformat
2. **"Don't preprocess" marker** - Include as-is, no transformations at all
3. **CLI formatter control** - No `--format` flag in main.py!

---

## User Needs Analysis

### Need 1: Disable Formatter for Specific Regions
**Use case**: Pre-formatted tables, manual line breaks, algorithm pseudocode

**Example**:
```latex
Normal paragraph. Gets formatted.

%%FLACHTEX-NO-FORMAT-START
\begin{tabular}{ll}
Carefully & formatted \\
table     & content
\end{tabular}
%%FLACHTEX-NO-FORMAT-STOP

Another paragraph. Gets formatted.
```

**What should happen**:
- ✅ Content included in output
- ✅ Preprocessing applies (skip rules, substitution)
- ❌ Formatting does NOT apply (no sentence splitting, no indentation changes)

### Need 2: Disable ALL Transformations for Specific Regions
**Use case**: Complex LaTeX that flachtex might misinterpret

**Example**:
```latex
%%FLACHTEX-RAW-START
% This region has complex LaTeX constructs
% Don't try to interpret it, just pass through as-is
\newcommand{\complex}[2]{
  \ifthenelse{\equal{#1}{#2}}{
    % Some conditional logic
  }{
    % Other logic
  }
}
%%FLACHTEX-RAW-STOP
```

**What should happen**:
- ✅ Content included in output
- ❌ Skip rules do NOT apply
- ❌ Substitution rules do NOT apply
- ❌ Formatting does NOT apply
- = Pure passthrough

### Need 3: Control Formatter via CLI
**Use case**: Quick formatting without writing Python code

**Current limitation**: No way to format from CLI!

```bash
# Current - no formatting option
flachtex main.tex

# Desired
flachtex --format main.tex
flachtex --format --indent 2 main.tex
```

---

## Proposed Strategy: Layered Protection

### Three Levels of Protection Markers

```
Processing Pipeline:
┌─────────────────────────────────────────────────────┐
│ 1. Read files                                       │
│ 2. Apply skip rules          ← NO-PREPROCESS blocks│
│ 3. Apply substitution rules  ← NO-PREPROCESS blocks│
│ 4. Find & process imports                          │
│ 5. (Optional) Format         ← NO-FORMAT blocks    │
└─────────────────────────────────────────────────────┘

SKIP blocks → Removed at step 2
NO-PREPROCESS blocks → Skip steps 2-3, include in output
NO-FORMAT blocks → Processed through step 4, skip step 5
```

### Marker Hierarchy

| Marker | In Output? | Skip Rules? | Substitution? | Formatting? |
|--------|-----------|-------------|---------------|-------------|
| `%%FLACHTEX-SKIP-START/STOP` | ❌ No | N/A | N/A | N/A |
| `%%FLACHTEX-RAW-START/STOP` | ✅ Yes | ❌ Skip | ❌ Skip | ❌ Skip |
| `%%FLACHTEX-NO-FORMAT-START/STOP` | ✅ Yes | ✅ Apply | ✅ Apply | ❌ Skip |
| (no marker) | ✅ Yes | ✅ Apply | ✅ Apply | ✅ Apply |

---

## Implementation Complexity Analysis

### Level 1: Add `--format` CLI Flag (EASY)
**Complexity**: ⭐ Low (1-2 hours)

**Changes needed**:
1. Update `main.py`:
   ```python
   parser.add_argument("--format", action="store_true",
                       help="Format output for diff-friendly version control")
   parser.add_argument("--indent", type=int, default=0,
                       help="Indent environments (spaces per level, 0=no indent)")
   ```

2. Call formatter conditionally:
   ```python
   doc = preprocessor.expand_file(file_path)
   if args.format:
       doc = format_latex(doc, indent=args.indent)
   ```

**Benefits**:
- Users can format from CLI
- No breaking changes (opt-in with `--format`)
- Matches user expectation for "separate formatter command"

**Files to modify**:
- `src/flachtex/main.py` (~10 lines)

---

### Level 2: Add `%%FLACHTEX-NO-FORMAT-START/STOP` (EASY)
**Complexity**: ⭐ Low (1-2 hours)

**Changes needed**:

1. **Create detector** (`src/flachtex/formatter/detectors.py`):
   ```python
   class NoFormatDetector:
       """Detects %%FLACHTEX-NO-FORMAT regions."""

       def find_all(self, content: str) -> list[Range]:
           pattern = r"(?P<block>%%FLACHTEX-NO-FORMAT-START.*?%%FLACHTEX-NO-FORMAT-STOP)"
           ranges = []
           for match in re.finditer(pattern, content, re.DOTALL | re.MULTILINE):
               # Include the markers themselves in the protected range
               ranges.append(Range(match.start("block"), match.end("block")))
           return ranges
   ```

2. **Use detector** (`src/flachtex/formatter/core.py`):
   ```python
   def format_latex(content: TraceableString, ...) -> TraceableString:
       # ... existing code ...

       # Add no-format detector
       no_format_detector = NoFormatDetector()
       protected_ranges.extend(no_format_detector.find_all(content_str))

       # ... rest of formatting ...
   ```

3. **Add tests** (`tests/test_formatter.py`):
   - Test that NO-FORMAT blocks are preserved
   - Test that NO-FORMAT works with other formatting
   - Test that NO-FORMAT markers themselves stay in output

**Benefits**:
- Users get explicit control over formatting
- Solves the "pre-formatted table" problem
- Simple, focused implementation
- No changes to preprocessing pipeline

**Files to modify**:
- `src/flachtex/formatter/detectors.py` (~20 lines)
- `src/flachtex/formatter/core.py` (~3 lines)
- `tests/test_formatter.py` (~50 lines)

---

### Level 3: Add `%%FLACHTEX-RAW-START/STOP` (MEDIUM)
**Complexity**: ⭐⭐ Medium (4-6 hours)

**Challenges**:
1. Need to detect RAW blocks BEFORE applying skip/substitution rules
2. Need to track RAW regions through the entire pipeline
3. More complex interaction with preprocessing

**Changes needed**:

1. **Detect RAW blocks early** (`src/flachtex/preprocessor.py`):
   ```python
   def read_file(self, file_path: Path | str) -> TraceableString:
       content = TraceableString(self.file_finder.read(file_path), origin=file_path)

       # NEW: Detect RAW blocks first
       raw_ranges = self._find_raw_blocks(str(content))

       # Apply skip rules EXCEPT in RAW blocks
       content = self._apply_skip_rules_with_exceptions(content, raw_ranges)

       # Apply substitution rules EXCEPT in RAW blocks
       return self._apply_substitution_rules_with_exceptions(content, raw_ranges)
   ```

2. **Problem**: Skip rules and substitution rules don't currently support "exception ranges"
   - Would need to add this capability
   - Or: Remove RAW blocks, process rest, then re-insert RAW blocks
   - Both approaches add complexity

3. **Alternative simpler approach**:
   - RAW blocks are ONLY protected from formatting (same as NO-FORMAT)
   - Don't try to protect from preprocessing
   - If users need raw passthrough, they use verbatim

**Benefits**:
- Complete control for users
- Handles edge cases where flachtex misinterprets LaTeX

**Drawbacks**:
- More complex
- Risk of bugs in range tracking
- Interactions with import processing unclear

**Files to modify**:
- `src/flachtex/preprocessor.py` (~50 lines)
- `src/flachtex/rules/skip_rules.py` (~30 lines)
- `src/flachtex/rules/substitution_rules.py` (~30 lines)
- Tests (~100 lines)

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (Week 1)
**Goal**: Give users immediate control over formatting

1. ✅ **Add `--format` CLI flag**
   - Complexity: ⭐ Low
   - Impact: 🔥 High (users can format from CLI)
   - Time: 1-2 hours

2. ✅ **Add `%%FLACHTEX-NO-FORMAT-START/STOP`**
   - Complexity: ⭐ Low
   - Impact: 🔥 High (solves pre-formatted table problem)
   - Time: 1-2 hours

**Total time**: ~4 hours
**User value**: Users can format from CLI and protect specific regions

### Phase 2: Advanced Protection (Future)
**Goal**: Handle complex edge cases

3. ⏳ **Add `%%FLACHTEX-RAW-START/STOP`** (if needed)
   - Complexity: ⭐⭐ Medium
   - Impact: 🔥 Medium (edge cases only)
   - Time: 4-6 hours
   - **Wait for user feedback**: Do users actually need this?

---

## Alternative: Simpler Two-Marker System

If we want to keep it simple:

### Option A: Just Two Markers
1. `%%FLACHTEX-SKIP-START/STOP` - Remove from output ✅ (already have)
2. `%%FLACHTEX-NO-FORMAT-START/STOP` - Include but don't format ⭐ (easy to add)

**Benefits**:
- Simple, clear mental model
- Covers 95% of use cases
- Easy to implement and maintain

**When users need "raw passthrough"**:
- Use LaTeX's `\begin{verbatim}` for code
- Use NO-FORMAT for pre-formatted LaTeX content
- This covers most cases

### Option B: Three Markers (Recommended)
1. `%%FLACHTEX-SKIP-START/STOP` - Remove from output ✅
2. `%%FLACHTEX-NO-FORMAT-START/STOP` - No formatting ⭐
3. `%%FLACHTEX-RAW-START/STOP` - No processing at all ⭐⭐ (future)

---

## User Documentation Strategy

### Clear Naming Convention

**Bad naming** (confusing):
- `%%FLACHTEX-SKIP` - What does it skip? Formatting? Output?
- `%%FLACHTEX-PROTECT` - Protect from what?

**Good naming** (clear intent):
- `%%FLACHTEX-SKIP-START` - "Skip this content" = not in output
- `%%FLACHTEX-NO-FORMAT-START` - "Don't format this" = in output, as-is
- `%%FLACHTEX-RAW-START` - "Raw passthrough" = no processing at all

### Documentation Examples

```latex
% Remove from output (skip rules)
%%FLACHTEX-SKIP-START
This won't appear in the final document.
%%FLACHTEX-SKIP-STOP

% Keep in output but don't format
%%FLACHTEX-NO-FORMAT-START
\begin{tabular}{ll}
Pre-formatted & table \\
stays         & as-is
\end{tabular}
%%FLACHTEX-NO-FORMAT-STOP

% (Future) Raw passthrough - no processing at all
%%FLACHTEX-RAW-START
Complex LaTeX that flachtex might misinterpret.
%%FLACHTEX-RAW-STOP
```

---

## Questions for User

1. **Immediate need**: Do you want `--format` CLI flag and `NO-FORMAT` markers now?
2. **RAW markers**: Do you have use cases that need complete passthrough (no skip rules, no substitution)?
3. **Naming**: Do you like `NO-FORMAT` or prefer something else (`NO-REFORMAT`, `KEEP-FORMAT`, `FORMAT-SKIP`)?
4. **Formatter defaults**: Should `--format` be opt-in (current) or opt-out (breaking change)?

---

## Summary

**Easy to implement now** (Phase 1):
- ✅ Add `--format` CLI flag (~2 hours)
- ✅ Add `%%FLACHTEX-NO-FORMAT-START/STOP` markers (~2 hours)
- Total: ~4 hours, high user value

**Medium complexity, wait for feedback** (Phase 2):
- ⏳ Add `%%FLACHTEX-RAW-START/STOP` for complete passthrough (~6 hours)
- Only implement if users have concrete use cases

**Recommended approach**:
Start with Phase 1 (quick, high value), then gather feedback before committing to Phase 2.
