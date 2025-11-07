# TraceableString Analysis: Pydantic vs. Alternatives

## Current State

`TraceableString` is a fundamental class used **61 times** across the codebase. It:

1. **Wraps strings with origin tracking** - crucial for error reporting and source tracing
2. **Performs heavy slicing/concatenation** - during file processing and import resolution
3. **Implements custom string-like behavior** - `__getitem__`, `__add__`, `__str__`
4. **Has lazy computation** - line index only computed when needed
5. **Supports serialization** - `to_json()` and `from_json()`

## Issues with Current Implementation

1. ❌ **No type hints** - on `__init__`, methods, or `OriginOfRange`
2. ❌ **Manual validation** - in `from_json()` with try/except
3. ❌ **Poor documentation** - methods lack docstrings
4. ❌ **Mutable state** - `origins` list can be modified, `_line_index` cache
5. ❌ **Type safety** - `origin` is `typing.Any`

## Should We Use Pydantic?

### ❌ Arguments AGAINST Pydantic

**1. Performance Overhead**
- Pydantic adds ~2-5x overhead on instantiation due to validation
- `TraceableString` is created/sliced frequently in hot paths
- Every slice operation creates a new instance
- Processing large documents could see significant slowdown

**2. Behavioral Mismatch**
- Pydantic models are **immutable by default** (with `frozen=True`)
- TraceableString needs **mutable operations**: slicing, concatenation, origin manipulation
- Pydantic is designed for **data validation**, not data structures with complex behavior
- `__getitem__`, `__add__` don't fit Pydantic's paradigm well

**3. String-like Interface**
- Acts like a string (slicing, indexing, concatenation)
- Pydantic models are dictionaries, not strings
- Would lose the natural string-like API

**4. Lazy Computation**
- `_line_index` is computed lazily for performance
- Pydantic's validation happens eagerly at instantiation
- Doesn't align with lazy computation patterns

**5. Complex State Management**
- `origins` list is mutated after construction in slicing
- Pydantic prefers immutable, validated-at-construction models

### ✅ What Pydantic WOULD Give Us

1. Runtime validation of types
2. Automatic `dict()` / JSON serialization
3. Better error messages for invalid data
4. Field validation and constraints

## Recommended Approach

### Option 1: Modern Python with Dataclasses (RECOMMENDED)

Use **dataclasses for `OriginOfRange`** (simple, immutable data) and **typed class for `TraceableString`** (complex behavior):

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True, slots=True)
class OriginOfRange:
    """Immutable range tracking original source location."""
    begin: int
    end: int
    origin: str | None
    offset: int = 0

    def __len__(self) -> int:
        return self.end - self.begin

    def cut_front(self, n: int) -> OriginOfRange | None:
        """Cut off indices < n."""
        if self.end <= n:
            return None
        if self.begin <= n < self.end:
            offset = self.offset + (n - self.begin)
        else:
            offset = self.offset
        return OriginOfRange(
            max(0, self.begin - n),
            self.end - n,
            self.origin,
            offset
        )
    # ... other methods

class TraceableString:
    """String wrapper that tracks origin information for each character."""

    __slots__ = ('content', 'origins', '_line_index')

    def __init__(
        self,
        content: str,
        origin: str | None,
        offset: int = 0
    ) -> None:
        self.content = content
        self.origins: list[OriginOfRange] = [
            OriginOfRange(0, len(content), origin, offset)
        ]
        self._line_index: list[int] | None = None
```

**Benefits:**
- ✅ `frozen=True` makes `OriginOfRange` immutable and hashable
- ✅ `slots=True` reduces memory overhead (~40% reduction)
- ✅ `__slots__` on `TraceableString` also saves memory
- ✅ Full type hints with modern syntax
- ✅ No performance overhead from validation
- ✅ Maintains string-like API
- ✅ Clean, readable code

### Option 2: attrs Library

Similar to dataclasses but with more features:

```python
import attrs

@attrs.frozen(slots=True, auto_attribs=True)
class OriginOfRange:
    begin: int
    end: int
    origin: str | None
    offset: int = 0

    @begin.validator
    def _check_begin(self, attribute, value):
        if value < 0:
            raise ValueError("begin must be >= 0")
```

**Benefits:**
- ✅ More validation options than dataclasses
- ✅ Still minimal overhead
- ✅ Better defaults and converters
- ✅ Evolve() for immutable updates

### Option 3: Hybrid Approach (attrs + Validation)

For `from_json()` validation, use a schema library separately:

```python
from typing import TypedDict

class OriginDict(TypedDict):
    begin: int
    end: int
    origin: str
    offset: int

def from_json(data: dict[str, Any]) -> TraceableString:
    """Load with validation."""
    if not isinstance(data.get("content"), str):
        raise ValueError("content must be a string")

    ts = TraceableString(data["content"], None)
    ts.origins = [
        OriginOfRange(
            begin=int(o["begin"]),
            end=int(o["end"]),
            origin=o["origin"],
            offset=int(o.get("offset", 0))
        )
        for o in data["origins"]
    ]
    return ts
```

## Performance Comparison

Rough estimates for creating 10,000 instances:

| Approach | Time | Memory | Overhead |
|----------|------|--------|----------|
| Current (no types) | 1.0x | 1.0x | baseline |
| Dataclasses | ~1.05x | ~0.6x | minimal |
| attrs | ~1.1x | ~0.6x | minimal |
| **Pydantic** | ~3-5x | ~1.2x | **significant** |

## Recommendation

**Use dataclasses for `OriginOfRange` and typed class for `TraceableString`**

### Reasons:
1. **Performance**: No validation overhead in hot paths
2. **Memory**: `slots=True` reduces memory by ~40%
3. **Immutability**: `frozen=True` for `OriginOfRange` prevents bugs
4. **Type Safety**: Full type hints + mypy catches errors
5. **Simplicity**: Standard library, no dependencies
6. **API Preservation**: Keeps string-like interface
7. **Lazy Computation**: Supports `_line_index` caching

### When to Consider Pydantic

Only if you need:
- Complex validation rules
- API input validation (not internal processing)
- OpenAPI/JSON Schema generation
- External data parsing (not internal data structures)

For `TraceableString`, the overhead isn't worth the benefits.

## Additional Improvements

1. **Add `__hash__`** to make instances hashable (if frozen)
2. **Add property validators** for critical invariants
3. **Use `__slots__`** to reduce memory
4. **Add comprehensive docstrings**
5. **Consider `@final`** decorator to prevent subclassing
6. **Add `__match_args__`** for pattern matching (Python 3.10+)

## Implementation Priority

1. ✅ Add type hints to both classes
2. ✅ Convert `OriginOfRange` to frozen dataclass with slots
3. ✅ Add `__slots__` to `TraceableString`
4. ✅ Add comprehensive docstrings
5. ✅ Improve `from_json` validation
6. ⚠️ Consider attrs if more features needed
7. ❌ Skip Pydantic (wrong tool for this job)
