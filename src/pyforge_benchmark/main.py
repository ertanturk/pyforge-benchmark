"""Main orchestration module for PyForge Benchmark complete cycle automation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .benchmark_runner import run_benchmark
from .complexity_runner import run_complexity_analysis
from .reporter import print_report


def inject_sys_path(benchmarks_dir: str | Path | None = None) -> Path:
    """Inject benchmarks directory into sys.path for module imports.

    Args:
        benchmarks_dir: Path to benchmarks directory. If None, uses default.

    Returns:
        The benchmarks directory path.

    Raises:
        ValueError: If benchmarks directory does not exist.
    """
    if benchmarks_dir is None:
        benchmarks_dir = Path.cwd() / "benchmarks"
    else:
        is_path = isinstance(benchmarks_dir, Path)
        benchmarks_dir = benchmarks_dir if is_path else Path(benchmarks_dir)

    if not benchmarks_dir.exists():
        raise ValueError(f"Benchmarks directory not found: {benchmarks_dir}")

    if not benchmarks_dir.is_dir():
        raise ValueError(f"Path is not a directory: {benchmarks_dir}")

    # Add to sys.path if not already there
    benchmarks_str = str(benchmarks_dir.resolve())
    if benchmarks_str not in sys.path:
        sys.path.insert(0, benchmarks_str)

    return benchmarks_dir


def discover_benchmark_modules(benchmarks_dir: Path) -> list[Path]:
    """Discover all Python files in benchmarks directory.

    Args:
        benchmarks_dir: Path to benchmarks directory.

    Returns:
        List of Python file paths (non-recursive, only top-level).

    Raises:
        ValueError: If no benchmark files found.
    """
    files = list(benchmarks_dir.glob("*.py"))

    # Filter out __pycache__ and hidden files
    files = [f for f in files if not f.name.startswith("_") and f.is_file()]

    if not files:
        raise ValueError(f"No benchmark files found in {benchmarks_dir}")

    return sorted(files)


def import_benchmark_module(file_path: Path) -> None:
    """Dynamically import a Python module to trigger decorators.

    Args:
        file_path: Path to the .py file.

    Raises:
        ImportError: If module import fails.
    """
    try:
        module_name = file_path.stem

        # Since we already injected benchmarks_dir to sys.path,
        # we can use __import__ which properly handles sys.modules
        if module_name not in sys.modules:
            __import__(module_name)
    except Exception as e:
        raise ImportError(f"Failed to import {file_path.name}: {e}") from e


def load_benchmark_files(benchmarks_dir: Path) -> None:
    """Load all benchmark files from the directory.

    Args:
        benchmarks_dir: Path to benchmarks directory.

    Raises:
        ImportError: If any file fails to import.
    """
    files = discover_benchmark_modules(benchmarks_dir)

    for file_path in files:
        try:
            import_benchmark_module(file_path)
        except ImportError as e:
            raise ImportError(f"Error loading {file_path.name}: {e}") from e


def run_all_benchmarks(
    run_benchmarks: bool = True,
    run_complexity: bool = True,
) -> dict[str, Any]:
    """Run benchmarks and/or complexity analyses based on parameters.

    Args:
        run_benchmarks: Whether to run benchmark tests.
        run_complexity: Whether to run complexity analysis.

    Returns:
        Dictionary with 'benchmarks' and 'complexity' keys (may be None if not run).

    Raises:
        RuntimeError: If benchmark or complexity execution fails.
    """
    results: dict[str, Any] = {}

    if run_benchmarks:
        try:
            results["benchmarks"] = run_benchmark()
        except Exception as e:
            raise RuntimeError(f"Benchmark execution failed: {e}") from e
    else:
        results["benchmarks"] = None

    if run_complexity:
        try:
            results["complexity"] = run_complexity_analysis()
        except Exception as e:
            raise RuntimeError(f"Complexity analysis execution failed: {e}") from e
    else:
        results["complexity"] = None

    return results


def run_cycle(
    benchmarks_dir: str | Path | None = None,
    verbose: bool = False,
    run_benchmarks: bool = True,
    run_complexity: bool = True,
) -> dict[str, Any]:
    """Execute the PyForge Benchmark cycle.

    Args:
        benchmarks_dir: Path to benchmarks directory. Uses default if None.
        verbose: Print verbose output during execution.
        run_benchmarks: Whether to run benchmark tests.
        run_complexity: Whether to run complexity analysis.

    Returns:
        Dictionary with benchmark and complexity results.

    Raises:
        ValueError: If benchmarks directory not found.
        ImportError: If module loading fails.
        RuntimeError: If benchmark execution fails.
    """
    if verbose:
        print("Injecting sys.path...")

    benchmarks_path = inject_sys_path(benchmarks_dir)

    if verbose:
        print(f"Loading benchmark files from: {benchmarks_path}")

    load_benchmark_files(benchmarks_path)

    if verbose:
        msg = []
        if run_benchmarks:
            msg.append("benchmarks")
        if run_complexity:
            msg.append("complexity analyses")
        print(f"Running {' and '.join(msg)}...")

    results = run_all_benchmarks(run_benchmarks=run_benchmarks, run_complexity=run_complexity)

    return results


def main(
    benchmarks_dir: str | Path | None = None,
    verbose: bool = False,
    show_results: bool = True,
    run_benchmarks: bool = True,
    run_complexity: bool = True,
) -> dict[str, Any]:
    """Main entry point for PyForge Benchmark automation.

    Args:
        benchmarks_dir: Path to benchmarks directory. Uses default if None.
        verbose: Print verbose output.
        show_results: Print results to stdout.
        run_benchmarks: Whether to run benchmark tests.
        run_complexity: Whether to run complexity analysis.

    Returns:
        Dictionary with benchmark and complexity results.
    """
    try:
        results = run_cycle(
            benchmarks_dir=benchmarks_dir,
            verbose=verbose,
            run_benchmarks=run_benchmarks,
            run_complexity=run_complexity,
        )

        if show_results:
            print_report(
                benchmark_results=results.get("benchmarks"),
                complexity_results=results.get("complexity"),
            )

        return results
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise
