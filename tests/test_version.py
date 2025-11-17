"""
Tests for version consistency across the project.

This ensures that version numbers don't diverge between different locations.
"""

import re
import sys
from pathlib import Path

# Use tomllib (Python 3.11+) or tomli (Python 3.10) for TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def test_version_consistency():
    """Verify that __version__ in __init__.py matches version in pyproject.toml."""
    # Read version from pyproject.toml
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"

    # Parse TOML file
    if tomllib is not None:
        # Use tomllib/tomli for proper parsing
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        pyproject_version = pyproject_data["project"]["version"]
    else:
        # Fallback: simple regex parsing (for Python 3.10 without tomli installed)
        pyproject_content = pyproject_path.read_text()
        version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject_content, re.MULTILINE)
        assert version_match is not None, "version not found in pyproject.toml"
        pyproject_version = version_match.group(1)

    # Read version from __init__.py
    init_path = project_root / "src" / "flachtex" / "__init__.py"
    init_content = init_path.read_text()

    # Extract __version__ using regex
    version_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_content, re.MULTILINE)

    assert version_match is not None, (
        "__version__ not found in __init__.py. "
        "Please add: __version__ = \"x.y.z\""
    )

    init_version = version_match.group(1)

    # Compare versions
    assert init_version == pyproject_version, (
        f"Version mismatch!\n"
        f"  __init__.py: {init_version}\n"
        f"  pyproject.toml: {pyproject_version}\n"
        f"Please update both files to have the same version."
    )


def test_version_format():
    """Verify that version follows semantic versioning format."""
    from flachtex import __version__

    # Check semantic versioning format (X.Y.Z or X.Y.Z-suffix)
    semver_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$'

    assert re.match(semver_pattern, __version__), (
        f"Version '{__version__}' does not follow semantic versioning format (X.Y.Z)\n"
        f"Examples: 1.0.0, 1.2.3, 2.0.0-beta.1"
    )
