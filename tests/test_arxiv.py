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

import tarfile
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from flachtex import Preprocessor
from flachtex.rules import SubimportChangesRule


def find_main_tex_file(directory: Path) -> str:
    """
    Attempt to find the main .tex file in a directory.

    Looks for common names like main.tex, paper.tex, or the first .tex file found.

    Args:
        directory: Directory to search for .tex files

    Returns:
        Name of the likely main .tex file

    Raises:
        FileNotFoundError: If no .tex files are found
    """
    # Common main file names in order of preference
    common_names = ["main.tex", "paper.tex", "manuscript.tex", "article.tex"]

    for name in common_names:
        if (directory / name).exists():
            return name

    # If no common name found, look for any .tex file
    tex_files = list(directory.glob("*.tex"))
    if tex_files:
        # If there's only one .tex file, that's probably it
        if len(tex_files) == 1:
            return tex_files[0].name
        # Otherwise, prefer files that don't look like includes
        # (avoid files starting with numbers or containing "section", "chapter", etc.)
        for tex_file in tex_files:
            name_lower = tex_file.name.lower()
            if not any(
                skip in name_lower
                for skip in ["section", "chapter", "appendix", "abstract", "intro"]
            ):
                return tex_file.name

        # If all else fails, return the first one
        return tex_files[0].name

    msg = f"No .tex files found in {directory}"
    raise FileNotFoundError(msg)


def download_arxiv_paper(
    url: str, extract_to: Path, main_file: str | None = None
) -> tuple[Path, str]:
    """
    Download and extract an arxiv paper.

    Args:
        url: The arxiv e-print URL (e.g., "https://arxiv.org/e-print/1505.03116")
        extract_to: Directory to extract the paper to
        main_file: Name of the main tex file. If None, will attempt to auto-detect.

    Returns:
        Tuple of (extraction directory Path, main file name)
    """

    def tex_file_filter(tarinfo, _path):
        """Filter to only extract .tex files."""
        if tarinfo.name.endswith(".tex"):
            return tarinfo
        return None

    extract_path = Path(extract_to)

    # Check if already downloaded (cached)
    if not extract_path.exists() or not any(extract_path.glob("*.tex")):
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
        response = None
        try:
            response = urllib.request.urlopen(req)
            with Path(path_tar).open("wb") as out_file:
                out_file.write(response.read())
        finally:
            if response is not None:
                response.close()

        # Verify it's a valid tarfile
        if not tarfile.is_tarfile(path_tar):
            msg = f"Downloaded file from {url} is not a valid tar file"
            raise ValueError(msg)

        # Extract only .tex files
        with tarfile.open(path_tar) as tar:
            tar.extractall(extract_path, filter=tex_file_filter)

        # Clean up the tarball
        Path(path_tar).unlink()

    # Auto-detect main file if not provided
    if main_file is None:
        main_file = find_main_tex_file(extract_path)

    return extract_path, main_file


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
# Use None for expected_main_file to auto-detect
ARXIV_PAPERS = [
    # Classic deep learning paper
    ("1505.03116", "https://arxiv.org/e-print/1505.03116", "main.tex"),
    # Another paper with different structure (if network allows)
    ("2203.07444", "https://arxiv.org/e-print/2203.07444", "survey.tex"),
    ("2103.14599", "https://arxiv.org/e-print/2103.14599", "main.tex"),
    ("2204.10836", "https://arxiv.org/e-print/2204.10836", "main.tex"),
    # Add more papers here as needed
]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("arxiv_id", "url", "main_file"),
    ARXIV_PAPERS,
    ids=[paper[0] for paper in ARXIV_PAPERS],
)
def test_arxiv_paper_flattening(arxiv_id: str, url: str, main_file: str):
    """
    Test that flachtex can successfully flatten real arxiv papers.

    This is an integration test that requires network access to download papers
    from arxiv. It will skip if the download fails (e.g., due to network issues
    or arxiv rate limiting).

    Args:
        arxiv_id: The arxiv paper ID
        url: The arxiv e-print URL
        main_file: Name of the main tex file
    """
    # Use a cache directory in the tests folder to persist downloads
    cache_dir = Path(__file__).parent / ".arxiv_cache"
    extract_to = cache_dir / f"paper_{arxiv_id}"

    try:
        # Download and extract the paper (or use cached version)
        paper_dir, detected_main_file = download_arxiv_paper(url, extract_to, main_file)
    except urllib.error.HTTPError as e:
        # Skip if we can't download (network issues, rate limiting, etc.)
        pytest.skip(f"Could not download paper {arxiv_id}: {e}")
    except Exception as e:
        pytest.fail(f"Failed to download arxiv paper {arxiv_id}: {e!s}")

    try:
        # Attempt to flatten the paper
        flattened = flatten_paper(paper_dir, detected_main_file)

        # Basic sanity checks
        assert flattened is not None, "Flattened content should not be None"
        assert len(flattened) > 0, "Flattened content should not be empty"
        assert isinstance(flattened, str), "Flattened content should be a string"

        # Check that we have some LaTeX content
        # Most papers should have at least a documentclass or begin{document}
        assert "\\documentclass" in flattened or "\\begin{document}" in flattened, (
            "Flattened content should contain LaTeX document structure"
        )

    except Exception as e:
        pytest.fail(f"Failed to flatten arxiv paper {arxiv_id}: {e!s}")


def test_arxiv_custom_urls():
    """
    Example test that can be customized with additional arxiv URLs.

    This test is meant to be easily extended by adding more URLs to the list.
    """
    # Add your custom arxiv URLs here
    custom_urls = [
        # ("paper_id", "https://arxiv.org/e-print/XXXX.XXXXX", "main.tex"),
        # ("paper_id2", "https://arxiv.org/e-print/YYYY.YYYYY", None),  # None = auto-detect
    ]

    if not custom_urls:
        pytest.skip("No custom URLs configured")

    cache_dir = Path(__file__).parent / ".arxiv_cache"

    for arxiv_id, url, main_file in custom_urls:
        extract_to = cache_dir / f"custom_paper_{arxiv_id}"

        try:
            # Download and extract the paper
            paper_dir, detected_main_file = download_arxiv_paper(
                url, extract_to, main_file
            )
        except urllib.error.HTTPError as e:
            pytest.skip(f"Could not download custom paper {arxiv_id}: {e}")

        # Flatten the paper
        flattened = flatten_paper(paper_dir, detected_main_file)

        # Verify the flattening succeeded
        assert flattened is not None
        assert len(flattened) > 0
        assert isinstance(flattened, str)
