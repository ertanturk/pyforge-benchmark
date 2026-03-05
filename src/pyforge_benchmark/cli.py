"""Command-line interface for PyForge Benchmark."""

from __future__ import annotations

import argparse
import platform
import sys

from . import __version__
from .main import inject_sys_path, load_benchmark_files, main
from .registry import Registry


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="pyforge-benchmark",
        description="PyForge Benchmark - Automated performance testing framework",
        epilog="For more info: https://github.com/ertanturk/pyforge-benchmark",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Main command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run benchmarks and complexity analysis",
    )
    run_parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=None,
        help="Path to benchmarks directory (default: ./benchmarks)",
    )
    run_parser.add_argument(
        "-b",
        "--benchmarks-only",
        action="store_true",
        help="Run only benchmark tests",
    )
    run_parser.add_argument(
        "-c",
        "--complexity-only",
        action="store_true",
        help="Run only complexity analysis",
    )
    run_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output during execution",
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all registered benchmarks",
    )
    list_parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=None,
        help="Path to benchmarks directory (default: ./benchmarks)",
    )
    list_parser.add_argument(
        "-t",
        "--type",
        choices=["benchmark", "complexity"],
        default=None,
        help="Filter by test type",
    )
    list_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed information",
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show PyForge Benchmark information",
    )
    info_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed system information",
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        benchmarks_dir = args.dir if args.dir else None

        # Determine which tests to run:
        # If both or neither flag is specified, run both
        # If only one flag is specified, run only that type
        run_benchmarks = not args.complexity_only or args.benchmarks_only
        run_complexity = not args.benchmarks_only or args.complexity_only

        main(
            benchmarks_dir=benchmarks_dir,
            verbose=args.verbose,
            show_results=True,
            run_benchmarks=run_benchmarks,
            run_complexity=run_complexity,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _filter_benchmarks_by_type(all_keys: list[str], test_type: str | None) -> list[str]:
    """Filter benchmarks by type.

    Args:
        all_keys: All benchmark keys.
        test_type: Type to filter by, or None for all.

    Returns:
        Filtered list of keys.
    """
    if test_type is None:
        return all_keys

    filtered_keys: list[str] = []
    for key in all_keys:
        metadata = Registry().get(key)
        if metadata and metadata.get("type") == test_type:
            filtered_keys.append(key)
    return filtered_keys


def _print_benchmark_entry(key: str, verbose: bool) -> None:
    """Print a single benchmark entry.

    Args:
        key: Benchmark key.
        verbose: Whether to print verbose details.
    """
    metadata = Registry().get(key)
    if metadata is None:
        return

    test_type = metadata.get("type", "unknown")
    has_generator = "generator" in metadata

    if verbose:
        args_str = metadata.get("args", ())
        kwargs_str = metadata.get("kwargs", {})
        print(f"  [{test_type}] {key}")
        if args_str:
            print(f"    args: {args_str}")
        if kwargs_str:
            print(f"    kwargs: {kwargs_str}")
        if has_generator:
            print("    generator: provided")
    else:
        gen_marker = " [generator]" if has_generator else ""
        print(f"  [{test_type}] {key}{gen_marker}")


def cmd_list(args: argparse.Namespace) -> int:
    """Execute the list command.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        benchmarks_dir = args.dir if args.dir else None
        path = inject_sys_path(benchmarks_dir)

        if args.verbose:
            print(f"Loading benchmarks from: {path}\n")

        load_benchmark_files(path)

        registry = Registry()
        all_keys = registry.list_registered()

        if not all_keys:
            print("No benchmarks registered.")
            return 0

        # Filter by type if specified
        filtered_keys = _filter_benchmarks_by_type(all_keys, args.type)

        if not filtered_keys:
            print(f"No {args.type} registered.")
            return 0

        print(f"Registered {len(filtered_keys)} benchmark(s):\n")

        for key in sorted(filtered_keys):
            _print_benchmark_entry(key, args.verbose)

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Execute the info command.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print(f"PyForge Benchmark v{__version__}")
    print("=" * 60)

    if args.detailed:
        print("\nSystem Information:")
        print(f"  Python: {platform.python_version()}")
        print(f"  Platform: {platform.platform()}")
        print(f"  Processor: {platform.processor()}")

        registry = Registry()
        print("\nRegistry State:")
        print(f"  Registered benchmarks: {len(registry.list_registered())}")
    else:
        print("\nPyForge Benchmark automates performance testing and")
        print("complexity analysis for Python functions.")
        print("\nUsage:")
        print("  pyforge-benchmark run     Run all benchmarks")
        print("  pyforge-benchmark list    List registered benchmarks")
        print("  pyforge-benchmark info    Show information")
        print("\nFor help:")
        print("  pyforge-benchmark --help")

    return 0


def main_cli() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle no command provided
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "info":
        return cmd_info(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main_cli())
