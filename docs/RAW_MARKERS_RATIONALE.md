# RAW Markers: User Escape Hatch for Flachtex Edge Cases

## The Real Problem

**LaTeX is incredibly complex**, and flachtex does aggressive preprocessing:
- Skip rules with regex patterns
- Command substitution with pattern matching
- Import detection with multiple strategies

**Users will encounter edge cases** where flachtex:
- Misinterprets complex LaTeX constructs
- Breaks on unusual command definitions
- Fails with certain package interactions
- Over-aggressively matches patterns in unexpected contexts

## Use Cases for RAW Markers

### Case 1: Complex Command Definitions That Break Substitution

```latex
%%FLACHTEX-RAW-START
\newcommand{\complexcmd}[2]{%
  \ifthenelse{\equal{#1}{#2}}{%
    % Flachtex might misinterpret the conditional
    \textbf{#1}%
  }{%
    \textit{#1} vs \textit{#2}%
  }%
}
%%FLACHTEX-RAW-STOP
```

**Why RAW needed**: Conditional logic inside command definitions might confuse command substitution rules.

### Case 2: Unusual Package Syntax

```latex
%%FLACHTEX-RAW-START
% Some packages use % in unusual ways
\usepackage[option=value%
  ,otheroption=value2%
  ]{complexpackage}
%%FLACHTEX-RAW-STOP
```

**Why RAW needed**: Comment detection might break on unusual % usage in package options.

### Case 3: Skip Rules False Positives

```latex
%%FLACHTEX-RAW-START
% This comment has the word "SKIP" in it:
% Please SKIP to page 5 for details
% But it's not a skip marker!
%%FLACHTEX-RAW-STOP
```

**Why RAW needed**: Regex patterns might have false positives that break content.

### Case 4: Verbatim-Like Content That Isn't Verbatim

```latex
%%FLACHTEX-RAW-START
% This looks like code but isn't in verbatim
% Don't try to process it
\def\macro{%
  % Comments inside macro definition
  Content with special % characters
}
%%FLACHTEX-RAW-STOP
```

**Why RAW needed**: Content looks like it should be protected but isn't in verbatim environment.

### Case 5: Nested Environments That Confuse Detection

```latex
%%FLACHTEX-RAW-START
\newenvironment{custom}{%
  \begin{itemize}%
}{%
  \end{itemize}%
}
%%FLACHTEX-RAW-STOP
```

**Why RAW needed**: Environment tracking for indentation might get confused by environment definitions.

---

## Revised Priority: RAW Markers Are Important

### Why RAW Markers Should Be Prioritized

1. **User Trust**: When flachtex breaks, users need an immediate workaround
2. **LaTeX Complexity**: Impossible to handle all edge cases perfectly
3. **Graceful Degradation**: Better to let users exclude problem regions than fail
4. **Support Burden**: Reduces "flachtex breaks on my document" issues

### Proposed Implementation Strategy

Instead of trying to protect RAW blocks from ALL preprocessing (complex), use a simpler approach:

**Option A: RAW = Detect Early, Remove, Re-insert**
1. Before preprocessing: Find all RAW blocks, extract them
2. Replace RAW blocks with placeholders (`%%FLACHTEX-RAW-PLACEHOLDER-1%%`)
3. Run normal preprocessing pipeline (skip rules, substitution, formatting)
4. After processing: Re-insert RAW blocks at placeholder positions

**Benefits**:
- Simple: No changes to existing skip/substitution rules
- Clean: RAW blocks never see any processing
- Safe: Placeholders won't match any real LaTeX patterns

**Drawbacks**:
- Need to handle imports inside RAW blocks (probably disallow them)
- Placeholder collision risk (can use UUID)

---

## Implementation Plan (Revised)

### Phase 1: Quick Wins (Still Important)
**Priority: HIGH**
- ✅ Add `--format` CLI flag (~2 hours)
- ✅ Add `%%FLACHTEX-NO-FORMAT-START/STOP` (~2 hours)

**Rationale**: Users need formatting control immediately, easy to implement.

### Phase 2: RAW Markers (NOW HIGHER PRIORITY)
**Priority: HIGH** (was MEDIUM)
- ✅ Add `%%FLACHTEX-RAW-START/STOP` (~6-8 hours)

**Rationale**:
- Users WILL hit edge cases where flachtex breaks
- RAW markers provide escape hatch
- Better than forcing users to manually edit flattened output

### Implementation Approach for RAW

```python
# In preprocessor.py

def _extract_raw_blocks(self, content: TraceableString) -> tuple[TraceableString, dict[str, TraceableString]]:
    """Extract RAW blocks and replace with placeholders."""
    raw_blocks = {}
    pattern = r"%%FLACHTEX-RAW-START\n(.*?)%%FLACHTEX-RAW-STOP"

    result = str(content)
    for i, match in enumerate(re.finditer(pattern, str(content), re.DOTALL)):
        placeholder = f"%%FLACHTEX-RAW-PLACEHOLDER-{uuid.uuid4()}%%"
        raw_blocks[placeholder] = content[match.start(1):match.end(1)]
        result = result[:match.start()] + placeholder + result[match.end():]

    return TraceableString(result, content.get_origin(0)), raw_blocks

def _restore_raw_blocks(self, content: TraceableString, raw_blocks: dict[str, TraceableString]) -> TraceableString:
    """Restore RAW blocks from placeholders."""
    result = content
    for placeholder, raw_content in raw_blocks.items():
        # Find placeholder and replace with original content
        result = result.replace(placeholder, raw_content)
    return result

def read_file(self, file_path: Path | str) -> TraceableString:
    content = TraceableString(self.file_finder.read(file_path), origin=file_path)

    # NEW: Extract RAW blocks before any processing
    content, raw_blocks = self._extract_raw_blocks(content)

    # Normal processing (skip rules, substitution)
    content = apply_skip_rules(content, self.skip_rules)
    content = apply_substitution_rules(content, self.substitution_rules)

    # NEW: Restore RAW blocks after processing
    content = self._restore_raw_blocks(content, raw_blocks)

    return content
```

**Complexity**: ~6-8 hours including:
- Placeholder extraction (~2 hours)
- Integration with preprocessor (~2 hours)
- Handling edge cases (nested markers, imports in RAW) (~2 hours)
- Tests (~2 hours)

---

## Important Design Decisions

### Decision 1: Can RAW blocks contain imports?

**Option A: Disallow imports in RAW blocks**
```latex
%%FLACHTEX-RAW-START
\input{file.tex}  % ERROR: Not allowed in RAW block
%%FLACHTEX-RAW-STOP
```

**Pro**: Simpler implementation, clearer semantics
**Con**: Less flexible

**Option B: Allow imports in RAW blocks**
```latex
%%FLACHTEX-RAW-START
\input{file.tex}  % Works, but file content is NOT protected
%%FLACHTEX-RAW-STOP
```

**Pro**: More flexible
**Con**: Confusing - the RAW block protects the `\input` line, but not the included file

**Recommendation**: **Disallow imports in RAW blocks** (Option A)
- If user needs to protect imported file, put RAW markers in that file
- Clearer semantics: RAW means "this exact content, nothing more"

### Decision 2: Can RAW markers be nested?

**Recommendation**: **NO** - Nesting is ambiguous and complex
```latex
%%FLACHTEX-RAW-START
Outer
%%FLACHTEX-RAW-START  % ERROR: Can't nest
Inner
%%FLACHTEX-RAW-STOP
%%FLACHTEX-RAW-STOP
```

### Decision 3: What if RAW markers are unclosed?

**Recommendation**: **Error** - Like skip markers, unclosed RAW is dangerous
- Could silently protect everything after START marker
- Better to fail loudly so user can fix

### Decision 4: Should formatting apply to RAW blocks?

**Recommendation**: **NO** - RAW means completely untouched
- RAW blocks are extracted before preprocessing
- They're also not formatted
- If user wants "skip preprocessing but allow formatting", use NO-FORMAT markers instead

---

## Final Marker Hierarchy

| Marker | In Output? | Skip Rules? | Substitution? | Formatting? | Use Case |
|--------|-----------|-------------|---------------|-------------|----------|
| `SKIP` | ❌ No | N/A | N/A | N/A | Remove draft notes |
| `RAW` | ✅ Yes | ❌ Skip | ❌ Skip | ❌ Skip | Workaround flachtex bugs |
| `NO-FORMAT` | ✅ Yes | ✅ Apply | ✅ Apply | ❌ Skip | Pre-formatted tables |
| (none) | ✅ Yes | ✅ Apply | ✅ Apply | ✅ Apply | Normal content |

---

## Documentation for Users

### When to Use Each Marker

**Use `%%FLACHTEX-SKIP-START/STOP` when**:
- You want to remove content from output
- Draft notes, TODOs, internal comments
- Content that should never be published

**Use `%%FLACHTEX-RAW-START/STOP` when**:
- Flachtex is breaking your LaTeX
- Complex command definitions that confuse substitution
- Unusual syntax that triggers false positives
- "Emergency override" - just pass it through untouched

**Use `%%FLACHTEX-NO-FORMAT-START/STOP` when**:
- You want content in output
- Preprocessing should apply (skip rules, substitution)
- But formatting should not apply (pre-formatted tables, manual line breaks)

### Example: Debugging Flachtex Issues

```latex
% Your document is breaking. Try wrapping suspicious sections:

%%FLACHTEX-RAW-START
% This complex LaTeX breaks flachtex's command substitution
\newcommand{\problematic}[2]{%
  \ifthenelse{...}{...}{...}%
}
%%FLACHTEX-RAW-STOP

% Now flachtex will pass this through untouched
```

---

## Summary

**Revised priorities based on user feedback**:

1. **Phase 1 (Still Quick Wins)**: `--format` CLI + `NO-FORMAT` markers (~4 hours)
2. **Phase 2 (NOW HIGH PRIORITY)**: `RAW` markers (~6-8 hours)

**Total effort**: ~10-12 hours for complete solution

**Key insight**: RAW markers are not just a "nice to have" - they're a **critical escape hatch** for when flachtex fails. Given LaTeX's complexity, users WILL encounter edge cases, and RAW markers let them work around issues without filing bug reports or manually editing output.

**Recommendation**: Implement both phases for complete user control:
- NO-FORMAT: "Don't format this"
- RAW: "Don't touch this at all (flachtex is breaking)"
