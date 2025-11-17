# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**flachtex** is a traceable LaTeX flattening and preprocessing tool that:
- Flattens LaTeX documents by expanding `\input`, `\include`, and `\subimport` commands
- Maintains traceability: every character in the output can be traced back to its source file and position
- Provides a diff-friendly formatter for version control (sentence-per-line, environment indentation)
- Supports various preprocessing rules (comment removal, TODO removal, `changes` package cleanup, `\newcommand` substitution)

Target: Python 3.10+

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_formatter.py

# Run specific test
pytest tests/test_formatter.py::test_function_name

# Run tests excluding integration tests
pytest -m "not integration"

# Run only integration tests
pytest -m integration
```

### Code Quality
```bash
# Run linter (ruff)
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Type checking (mypy)
mypy src/ tests/

# Run all quality checks together
ruff check src/ tests/ && mypy src/ tests/
```

### Building and Installation
```bash
# Install in development mode
pip install -e .

# Build distribution
python -m build

# Install with all dependencies
pip install -e ".[dev]"
```

### Running the CLI
```bash
# Basic flattening
flachtex path/to/main.tex

# Flatten with formatting
flachtex --format --indent 2 path/to/main.tex

# Format without flattening (keep \input commands)
flachtex --no-expand --format --indent 2 path/to/main.tex

# Full preprocessing pipeline
flachtex --comments --todos --changes --newcommand --format path/to/main.tex

# Output as JSON with source tracing
flachtex --to_json --attach path/to/main.tex
```

## Architecture

### Core Pipeline

The preprocessing pipeline follows this flow:
1. **File Reading**: `FileFinder` resolves and reads LaTeX files
2. **RAW Block Extraction**: Extract `%%FLACHTEX-RAW-START/STOP` blocks (bypass all processing)
3. **Skip Rules**: Remove marked sections (`%%FLACHTEX-SKIP-START/STOP`, TODOs, etc.)
4. **Substitution Rules**: Transform commands (`\newcommand` expansion, `changes` package cleanup)
5. **Import Finding**: Locate `\input`, `\include`, `\subimport` commands
6. **Recursive Flattening**: Recursively expand imports while maintaining traceability
7. **Subimport Path Adjustment**: Apply `SubimportSubstitutionRule` for path transformations
8. **RAW Block Restoration**: Restore RAW blocks verbatim
9. **Optional Formatting**: Apply diff-friendly formatting if requested

### Key Components

**`TraceableString`** (`src/flachtex/traceable_string.py`):
- Core data structure that wraps strings with origin information
- Every substring knows its source file and position
- Supports concatenation while preserving traceability
- Enables `get_origin()` and `get_origin_of_line()` methods

**`Preprocessor`** (`src/flachtex/preprocessor.py`):
- Main orchestrator of the preprocessing pipeline
- Manages rule collections: `skip_rules`, `substitution_rules`, `import_rules`, `subimport_rules`
- Handles recursive file expansion with cycle detection
- Builds the `structure` dict mapping files to their content and includes

**Rules System** (`src/flachtex/rules/`):
- **`ImportRule`**: Identifies file inclusion commands (e.g., `\input`, `\include`)
- **`SkipRule`**: Marks sections to remove (e.g., `FLACHTEX-SKIP`, TODOs)
- **`SubstitutionRule`**: Transforms content (e.g., `ChangesRule`, `NewCommandSubstitution`)
- **`SubimportSubstitutionRule`**: Adjusts paths after subimport processing

**`FileFinder`** (`src/flachtex/filefinder.py`):
- Resolves LaTeX file paths with fallback logic
- Tries: relative to calling file → document root → parent directories
- Handles `.tex` extension variations

**`Formatter`** (`src/flachtex/formatter/`):
- **`sentence_splitter.py`**: Splits text into one sentence per line (handles abbreviations, decimals)
- **`indentation.py`**: Adds progressive indentation for nested environments
- **`environment_tracker.py`**: Tracks LaTeX environment nesting depth
- **`normalization.py`**: Normalizes blank lines, whitespace
- **`detectors.py`**: Identifies verbatim/document-level environments

**Protection Markers**:
- `%%FLACHTEX-SKIP-START/STOP`: Exclude content from output (flattening only)
- `%%FLACHTEX-RAW-START/STOP`: Bypass ALL preprocessing (added in recent work)
- `%%FLACHTEX-FORMAT-SKIP-START/STOP`: Skip formatting while allowing other preprocessing
- `%%FLACHTEX-EXPLICIT-IMPORT[path]`: Manual import for complex cases

### Command Line Interface

Entry point: `src/flachtex/__main__.py:main()`
- Parses arguments via `parse_arguments()`
- Configures `Preprocessor` with requested rules
- Optionally bypasses expansion with `--no-expand` (format-only mode)
- Outputs either plain text or JSON with tracing data

## Design Patterns and Conventions

### Rule-Based Architecture
Rules are modular and composable. To add functionality:
1. Create a new rule class inheriting from `ImportRule`, `SkipRule`, or `SubstitutionRule`
2. Add it to the appropriate rule list in `Preprocessor`
3. Ensure rules don't create overlapping matches (causes conflicts)

### TraceableString Operations
When manipulating `TraceableString`:
- Use string concatenation: `new_str = ts1 + ts2` (preserves tracing)
- Use slicing: `substring = ts[10:20]` (preserves origin info)
- Avoid converting to `str` unless necessary (loses tracing)

### Testing Approach
- Unit tests for individual components (rules, utilities)
- Integration tests marked with `@pytest.mark.integration`
- Tests use temporary files and fixture data
- Origin tracing is tested extensively (see `test_origin.py`)

## Important Files and Locations

- `src/flachtex/__main__.py`: CLI entry point (do NOT use the old `main.py`)
- `src/flachtex/preprocessor.py`: Core preprocessing logic
- `src/flachtex/traceable_string.py`: Traceability implementation
- `src/flachtex/formatter/`: Diff-friendly formatting implementation
- `src/flachtex/rules/`: All preprocessing rules
- `docs/formatter.md`: Complete formatter documentation
- `docs/PROTECTION_MARKERS_STRATEGY.md`: Design decisions for protection markers
- `pyproject.toml`: Project configuration, dependencies, tool settings

## Recent Development Focus

Recent commits focus on protection markers and formatter control:
- Added RAW markers (`%%FLACHTEX-RAW-START/STOP`) to bypass all preprocessing
- Implemented FORMAT-SKIP markers for formatter-only exclusion
- Enhanced formatter with `--no-expand` mode (format without flattening)
- Documented marker interactions and use cases
