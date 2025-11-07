"""
Tests for flattening real arxiv papers.

This test suite downloads arxiv papers and tests that flachtex can successfully
flatten them. Downloads are cached to avoid repeated network requests.

Usage:
------
1. Add arxiv papers to test by adding tuples to the ARXIV_PAPERS list:
   ARXIV_PAPERS = [
       ("paper_id", "https://arxiv.org/e-print/XXXX.XXXXX", "main.tex"),
       ...
   ]

2. Run the integration tests with:
   pytest tests/test_arxiv.py -v

3. Skip integration tests (e.g., in CI) with:
   pytest -m "not integration"

4. The papers are cached in tests/.arxiv_cache/ to avoid repeated downloads.

5. If download fails (network issues, rate limiting), tests will be skipped
   rather than failed.

Note:
-----
These are integration tests requiring network access. Some environments may block
arxiv downloads or apply rate limiting, in which case the tests will be skipped.
"""

import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from flachtex import Preprocessor
from flachtex.rules import SubimportChangesRule


def download_arxiv_paper(url: str, extract_to: Path, main_file: str = "main.tex") -> Path:
    """
    Download and extract an arxiv paper.

    Args:
        url: The arxiv e-print URL (e.g., "https://arxiv.org/e-print/1505.03116")
        extract_to: Directory to extract the paper to
        main_file: Name of the main tex file (used to check if already downloaded)

    Returns:
        Path to the extraction directory
    """

    def tex_file_filter(tarinfo, path):
        """Filter to only extract .tex files."""
        if tarinfo.name.endswith(".tex"):
            return tarinfo
        return None

    extract_path = Path(extract_to)
    main_path = extract_path / main_file

    # Check if already downloaded (cached)
    if not main_path.exists():
        # Create directory if it doesn't exist
        extract_path.mkdir(parents=True, exist_ok=True)

        # Download the tarball
        path_tar = str(extract_path) + ".tar.gz"

        # Add headers to avoid 403 errors from arxiv
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; flachtex-test/1.0; +https://github.com/d-krupke/flachtex)"
            },
        )
        with urllib.request.urlopen(req) as response:
            with open(path_tar, "wb") as out_file:
                out_file.write(response.read())

        # Verify it's a valid tarfile
        if not tarfile.is_tarfile(path_tar):
            msg = f"Downloaded file from {url} is not a valid tar file"
            raise ValueError(msg)

        # Extract only .tex files
        with tarfile.open(path_tar) as tar:
            tar.extractall(extract_path, filter=tex_file_filter)

        # Clean up the tarball
        Path(path_tar).unlink()

    return extract_path


def flatten_paper(base_dir: Path, main_file: str = "main.tex") -> str:
    """
    Flatten a LaTeX paper using flachtex.

    Args:
        base_dir: Directory containing the LaTeX files
        main_file: Name of the main tex file

    Returns:
        The flattened LaTeX content as a string
    """
    preprocessor = Preprocessor(str(base_dir))
    preprocessor.subimport_rules.append(SubimportChangesRule())

    main_path = base_dir / main_file
    doc = preprocessor.expand_file(str(main_path))

    return str(doc)


# List of arxiv papers to test
# Format: (arxiv_id, url, expected_main_file)
ARXIV_PAPERS = [
    ("1505.03116", "https://arxiv.org/e-print/1505.03116", "main.tex"),
    # Add more papers here as needed
]


@pytest.mark.integration
@pytest.mark.parametrize("arxiv_id,url,main_file", ARXIV_PAPERS)
def test_arxiv_paper_flattening(arxiv_id: str, url: str, main_file: str, tmp_path: Path):
    """
    Test that flachtex can successfully flatten real arxiv papers.

    This is an integration test that requires network access to download papers
    from arxiv. It will skip if the download fails (e.g., due to network issues
    or arxiv rate limiting).

    Args:
        arxiv_id: The arxiv paper ID
        url: The arxiv e-print URL
        main_file: Name of the main tex file
        tmp_path: Pytest fixture providing a temporary directory
    """
    # Use a cache directory in the tests folder to persist downloads
    cache_dir = Path(__file__).parent / ".arxiv_cache"
    extract_to = cache_dir / f"paper_{arxiv_id}"

    try:
        # Download and extract the paper (or use cached version)
        paper_dir = download_arxiv_paper(url, extract_to, main_file)
    except urllib.error.HTTPError as e:
        # Skip if we can't download (network issues, rate limiting, etc.)
        pytest.skip(f"Could not download paper {arxiv_id}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to download arxiv paper {arxiv_id}: {e!s}")

    try:
        # Attempt to flatten the paper
        flattened = flatten_paper(paper_dir, main_file)

        # Basic sanity checks
        assert flattened is not None, "Flattened content should not be None"
        assert len(flattened) > 0, "Flattened content should not be empty"
        assert isinstance(flattened, str), "Flattened content should be a string"

        # Check that we have some LaTeX content
        # Most papers should have at least a documentclass or begin{document}
        assert (
            "\\documentclass" in flattened or "\\begin{document}" in flattened
        ), "Flattened content should contain LaTeX document structure"

    except Exception as e:
        pytest.fail(f"Failed to flatten arxiv paper {arxiv_id}: {e!s}")


def test_arxiv_custom_urls(tmp_path: Path):
    """
    Example test that can be customized with additional arxiv URLs.

    This test is meant to be easily extended by adding more URLs to the list.
    """
    # Add your custom arxiv URLs here
    custom_urls = [
        # ("paper_id", "https://arxiv.org/e-print/XXXX.XXXXX", "main.tex"),
    ]

    if not custom_urls:
        pytest.skip("No custom URLs configured")

    cache_dir = Path(__file__).parent / ".arxiv_cache"

    for arxiv_id, url, main_file in custom_urls:
        extract_to = cache_dir / f"custom_paper_{arxiv_id}"

        # Download and extract the paper
        paper_dir = download_arxiv_paper(url, extract_to, main_file)

        # Flatten the paper
        flattened = flatten_paper(paper_dir, main_file)

        # Verify the flattening succeeded
        assert flattened is not None
        assert len(flattened) > 0
        assert isinstance(flattened, str)
