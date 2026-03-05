"""Smoke test to verify the package imports and exposes its public API."""

from pyforge_benchmark import __version__, benchmark, complexity_analysis


def test_version_is_string() -> None:
    """Ensure __version__ is a non-empty string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_public_api_exists() -> None:
    """Verify core decorators are importable."""
    assert callable(benchmark)
    assert callable(complexity_analysis)
