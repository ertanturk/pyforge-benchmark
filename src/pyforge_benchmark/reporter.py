"""Report and display benchmark and complexity analysis results with colorful output."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

# Time conversion thresholds
NANO_SECOND_THRESHOLD: float = 1e-6
MICRO_SECOND_THRESHOLD: float = 1e-3

# Layout constants
REPORT_WIDTH: int = 72
RESULT_COL_WIDTH: int = 18
SEPARATOR_CHAR: str = "─"
HEADER_CHAR: str = "═"
INDENT: str = "  "
DETAIL_INDENT: str = "    "


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def _colorize(text: str, *codes: str) -> str:
    """Wrap text with ANSI color codes.

    Args:
        text: The text to colorize.
        *codes: One or more ANSI codes.

    Returns:
        Colorized string.
    """
    prefix = "".join(codes)
    return f"{prefix}{text}{Colors.RESET}"


def _pad_visible(text: str, width: int) -> str:
    """Pad a string containing ANSI codes to a visible width.

    Standard str formatting counts escape codes in the width,
    breaking alignment. This calculates visible length and pads
    with real spaces.

    Args:
        text: String potentially containing ANSI escape codes.
        width: Desired visible width.

    Returns:
        Left-aligned string padded to visible width.
    """
    # Strip ANSI codes for visible length calculation
    visible = re.sub(r"\033\[[0-9;]*m", "", text)
    padding = max(0, width - len(visible))
    return text + " " * padding


def format_time(seconds: float) -> str:
    """Format time duration in appropriate units.

    Args:
        seconds: Time duration in seconds.

    Returns:
        Formatted time string with appropriate unit.
    """
    if seconds < NANO_SECOND_THRESHOLD:
        return f"{seconds * 1e9:.2f} ns"
    elif seconds < MICRO_SECOND_THRESHOLD:
        return f"{seconds * 1e6:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1e3:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def _get_file_and_line(key: str, func: Any) -> tuple[str, int]:
    """Extract file name and line number from function.

    Args:
        key: Registry key in format 'module.qualname'.
        func: The function object.

    Returns:
        Tuple of (file_path, line_number).
    """
    try:
        source_file = inspect.getsourcefile(func)
        file_path = Path(source_file).name if source_file else key.split(".", maxsplit=1)[0] + ".py"

        try:
            line_number = inspect.getsourcelines(func)[1]
        except (OSError, TypeError):
            line_number = 0
    except Exception:
        file_path = key.split(".", maxsplit=1)[0] + ".py"
        line_number = 0

    return file_path, line_number


def _extract_function_name(key: str) -> str:
    """Extract function name from registry key.

    Args:
        key: Registry key in format 'module.qualname'.

    Returns:
        Just the function name part.
    """
    return key.rsplit(".", 1)[-1]


def _format_line_ref(line_number: int) -> str:
    """Format a line number reference.

    Args:
        line_number: Source line number (0 if unknown).

    Returns:
        Formatted string like '(Line 13)' or empty if unknown.
    """
    if line_number > 0:
        return f"(Line {line_number})"
    return ""


def _build_header(title: str) -> list[str]:
    """Build a section header block.

    Args:
        title: Section title text.

    Returns:
        List of formatted header lines.
    """
    lines: list[str] = []
    lines.append("")
    lines.append(_colorize(HEADER_CHAR * REPORT_WIDTH, Colors.DIM))
    lines.append(f"  {_colorize(title, Colors.BOLD, Colors.BRIGHT_WHITE)}")
    lines.append(_colorize(HEADER_CHAR * REPORT_WIDTH, Colors.DIM))
    return lines


def _build_file_header(file_path: str, color: str) -> list[str]:
    """Build a file group header.

    Args:
        file_path: Name of the source file.
        color: ANSI color for the file header.

    Returns:
        List of formatted file header lines.
    """
    lines: list[str] = []
    lines.append("")
    icon = _colorize("●", color, Colors.BOLD)
    name = _colorize(file_path, color, Colors.BOLD)
    lines.append(f"  {icon} {name}")
    lines.append(f"  {_colorize(SEPARATOR_CHAR * (REPORT_WIDTH - 2), Colors.DIM)}")
    return lines


def _group_results_by_file(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group result entries by their source file.

    Args:
        results: List of result dictionaries.

    Returns:
        Dictionary mapping file names to result lists.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        key = result.get("key", "unknown")
        func = result.get("func_ref")
        if func:
            file_path, _ = _get_file_and_line(key, func)
        else:
            file_path = key.split(".")[0] + ".py"

        if file_path not in grouped:
            grouped[file_path] = []
        grouped[file_path].append(result)
    return grouped


def _get_complexity_color(complexity: str) -> str:
    """Get color for complexity class.

    Args:
        complexity: Complexity class string (e.g., 'O(1)', 'O(n)').

    Returns:
        Color code for the complexity.
    """
    if complexity in ("O(1)", "O(log n)"):
        return Colors.BRIGHT_GREEN
    elif complexity in ("O(√n)",):
        return Colors.BRIGHT_BLUE
    elif complexity in ("O(n)", "O(n log n)"):
        return Colors.BRIGHT_CYAN
    elif complexity in ("O(n²)", "O(n^2)"):
        return Colors.BRIGHT_YELLOW
    elif complexity in ("O(n³)", "O(n^3)", "O(2ⁿ)", "O(2^n)"):
        return Colors.BRIGHT_RED
    else:
        return Colors.WHITE


def _format_benchmark_entry(result: dict[str, Any]) -> list[str]:
    """Format a single benchmark result entry.

    Args:
        result: A benchmark result dictionary.

    Returns:
        List of formatted lines for this entry.
    """
    lines: list[str] = []
    key = result.get("key", "unknown")
    func = result.get("func_ref")
    func_name = _extract_function_name(key)
    status = result.get("status", "unknown")

    if func:
        _, line_number = _get_file_and_line(key, func)
    else:
        line_number = 0

    line_ref = _format_line_ref(line_number)

    if status == "success":
        avg_time = result.get("avg_time", 0)
        iterations = result.get("iterations", 0)

        time_str = _colorize(format_time(avg_time), Colors.BOLD, Colors.GREEN)
        padded_time = _pad_visible(time_str, RESULT_COL_WIDTH)

        name_part = _colorize(func_name, Colors.BOLD, Colors.WHITE)
        line_part = _colorize(f" {line_ref}", Colors.DIM) if line_ref else ""

        lines.append(f"{DETAIL_INDENT}{padded_time} {name_part}{line_part}")
        lines.append(
            f"{DETAIL_INDENT}{' ' * RESULT_COL_WIDTH} "
            f"{_colorize(f'iterations: {iterations}', Colors.DIM)}"
        )
    else:
        error = result.get("error", "Unknown error")

        tag = _colorize(" ERROR ", Colors.BOLD, Colors.WHITE, Colors.BG_RED)
        padded_tag = _pad_visible(tag, RESULT_COL_WIDTH)

        name_part = _colorize(func_name, Colors.BOLD, Colors.WHITE)
        line_part = _colorize(f" {line_ref}", Colors.DIM) if line_ref else ""

        lines.append(f"{DETAIL_INDENT}{padded_tag} {name_part}{line_part}")
        lines.append(f"{DETAIL_INDENT}{' ' * RESULT_COL_WIDTH} {_colorize(error, Colors.RED)}")

    return lines


def _format_complexity_entry(result: dict[str, Any]) -> list[str]:
    """Format a single complexity analysis result entry.

    Args:
        result: A complexity result dictionary.

    Returns:
        List of formatted lines for this entry.
    """
    lines: list[str] = []
    key = result.get("key", "unknown")
    func = result.get("func_ref")
    func_name = _extract_function_name(key)
    status = result.get("status", "unknown")

    if func:
        _, line_number = _get_file_and_line(key, func)
    else:
        line_number = 0

    line_ref = _format_line_ref(line_number)

    if status == "success":
        big_o = result.get("big_o", {})
        complexity = big_o.get("complexity", "Unknown")
        r_squared = big_o.get("r_squared", 0)

        color = _get_complexity_color(complexity)
        complexity_str = _colorize(complexity, Colors.BOLD, color)
        padded_complexity = _pad_visible(complexity_str, RESULT_COL_WIDTH)

        name_part = _colorize(func_name, Colors.BOLD, Colors.WHITE)
        line_part = _colorize(f" {line_ref}", Colors.DIM) if line_ref else ""

        lines.append(f"{DETAIL_INDENT}{padded_complexity} {name_part}{line_part}")
        lines.append(
            f"{DETAIL_INDENT}{' ' * RESULT_COL_WIDTH} "
            f"{_colorize(f'R² = {r_squared:.3f}', Colors.DIM)}"
        )
    else:
        error = result.get("error", "Unknown error")

        tag = _colorize(" ERROR ", Colors.BOLD, Colors.WHITE, Colors.BG_RED)
        padded_tag = _pad_visible(tag, RESULT_COL_WIDTH)

        name_part = _colorize(func_name, Colors.BOLD, Colors.WHITE)
        line_part = _colorize(f" {line_ref}", Colors.DIM) if line_ref else ""

        lines.append(f"{DETAIL_INDENT}{padded_tag} {name_part}{line_part}")
        lines.append(f"{DETAIL_INDENT}{' ' * RESULT_COL_WIDTH} {_colorize(error, Colors.RED)}")

    return lines


def report_benchmarks(results: list[dict[str, Any]]) -> str:
    """Report benchmark results grouped by file with color.

    Args:
        results: List of benchmark result dictionaries.

    Returns:
        Formatted report string.
    """
    if not results:
        return _colorize("  No benchmark results to report.", Colors.BOLD, Colors.YELLOW)

    lines: list[str] = _build_header("BENCHMARK RESULTS")
    grouped = _group_results_by_file(results)

    for file_path in sorted(grouped.keys()):
        lines.extend(_build_file_header(file_path, Colors.CYAN))

        for result in grouped[file_path]:
            lines.extend(_format_benchmark_entry(result))

    lines.append("")
    return "\n".join(lines)


def report_complexity(results: list[dict[str, Any]]) -> str:
    """Report complexity analysis results grouped by file with color.

    Args:
        results: List of complexity analysis result dictionaries.

    Returns:
        Formatted report string.
    """
    if not results:
        return _colorize("  No complexity analysis results to report.", Colors.BOLD, Colors.YELLOW)

    lines: list[str] = _build_header("COMPLEXITY ANALYSIS")
    grouped = _group_results_by_file(results)

    for file_path in sorted(grouped.keys()):
        lines.extend(_build_file_header(file_path, Colors.MAGENTA))

        for result in grouped[file_path]:
            lines.extend(_format_complexity_entry(result))

    lines.append("")
    return "\n".join(lines)


def report_combined(
    benchmark_results: list[dict[str, Any]] | None = None,
    complexity_results: list[dict[str, Any]] | None = None,
) -> str:
    """Report both benchmark and complexity analysis results.

    Args:
        benchmark_results: List of benchmark result dictionaries.
        complexity_results: List of complexity analysis result dictionaries.

    Returns:
        Combined formatted report string.
    """
    sections: list[str] = []

    if benchmark_results:
        sections.append(report_benchmarks(benchmark_results))

    if complexity_results:
        sections.append(report_complexity(complexity_results))

    if not sections:
        return _colorize("  No results to report.", Colors.BOLD, Colors.YELLOW)

    return "\n".join(sections)


def print_benchmarks(results: list[dict[str, Any]]) -> None:
    """Print benchmark results to stdout.

    Args:
        results: List of benchmark result dictionaries.
    """
    print(report_benchmarks(results))


def print_complexity(results: list[dict[str, Any]]) -> None:
    """Print complexity analysis results to stdout.

    Args:
        results: List of complexity analysis result dictionaries.
    """
    print(report_complexity(results))


def print_report(
    benchmark_results: list[dict[str, Any]] | None = None,
    complexity_results: list[dict[str, Any]] | None = None,
) -> None:
    """Print combined benchmark and complexity analysis report to stdout.

    Args:
        benchmark_results: List of benchmark result dictionaries.
        complexity_results: List of complexity analysis result dictionaries.
    """
    print(report_combined(benchmark_results, complexity_results))
