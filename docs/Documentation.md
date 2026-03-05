# PyForge Benchmark Documentation

## Overview

PyForge Benchmark is a lightweight, zero-dependency Python benchmarking framework designed for
personal projects and learning. It provides decorator-based performance measurement and automatic
Big-O complexity analysis through a simple CLI.

> **Note:** This is a personal/educational project and is not intended to compete with established
> benchmarking tools like `pytest-benchmark`, `asv`, or `pyperf`. It was built as a learning
> exercise in Python packaging, subprocess isolation, and algorithmic analysis.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Decorators](#decorators)
- [CLI Reference](#cli-reference)
- [Architecture](#architecture)
- [API Reference](#api-reference)

---

## Installation

```bash
pip install pyforge-benchmark
```

Or install from source:

```bash
git clone https://github.com/ertanturk/pyforge-benchmark.git
cd pyforge-benchmark
pip install -e .
```

**Requirements:** Python 3.12 or higher. No external runtime dependencies.

---

## Quick Start

### 1. Create a benchmarks directory

```bash
mkdir benchmarks
```

### 2. Write a benchmark file

Create `benchmarks/my_benchmarks.py`:

```python
from pyforge_benchmark import benchmark, complexity_analysis


@benchmark
def my_fast_function():
    """Measure how long this takes."""
    return sum(range(1000))


@benchmark(args=(50,))
def fibonacci(n: int) -> int:
    """Benchmark with arguments."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b


def generate_data(n: int) -> list[int]:
    """Data generator for complexity analysis."""
    return list(range(n))


@complexity_analysis(generator=generate_data)
def linear_search(data: list[int]) -> None:
    """Should be detected as O(n)."""
    for item in data:
        _ = item
```

### 3. Run

```bash
pyforge-benchmark run
```

Output:

```
════════════════════════════════════════════════════════════════════════
  BENCHMARK RESULTS
════════════════════════════════════════════════════════════════════════

  ● my_benchmarks.py
  ──────────────────────────────────────────────────────────────────────
    12.34 μs           my_fast_function (Line 4)
                       iterations: 100
    1.56 μs            fibonacci (Line 10)
                       iterations: 100

════════════════════════════════════════════════════════════════════════
  COMPLEXITY ANALYSIS
════════════════════════════════════════════════════════════════════════

  ● my_benchmarks.py
  ──────────────────────────────────────────────────────────────────────
    O(n)               linear_search (Line 23)
                       R² = 0.984
```

---

## Decorators

### `@benchmark`

Registers a function for execution-time measurement.

**Bare decorator:**

```python
@benchmark
def my_func():
    return 1 + 2
```

**With arguments:**

```python
@benchmark(args=(100,), kwargs={"key": "value"})
def my_func(n: int, key: str = "") -> int:
    return n
```

**Parameters:**

| Parameter | Type                    | Default | Description                          |
|-----------|-------------------------|---------|--------------------------------------|
| `args`    | `tuple[Any, ...]`       | `()`    | Positional arguments for the target  |
| `kwargs`  | `dict[str, Any] | None` | `None`  | Keyword arguments for the target     |

**Constraints:**

- Function must be picklable (no lambdas, closures, or inner functions)
- Arguments must also be picklable

---

### `@complexity_analysis`

Registers a function for Big-O complexity analysis.

**With generator:**

```python
def make_data(n: int) -> list[int]:
    return list(range(n))

@complexity_analysis(generator=make_data)
def sort_data(data: list[int]) -> list[int]:
    return sorted(data)
```

**Parameters:**

| Parameter   | Type                    | Default | Description                                    |
|-------------|-------------------------|---------|------------------------------------------------|
| `args`      | `tuple[Any, ...]`       | `()`    | Additional positional arguments                |
| `kwargs`    | `dict[str, Any] | None` | `None`  | Additional keyword arguments                   |
| `generator` | `Callable[[int], Any]`  | `None`  | Data generator accepting size N (required)     |

**Generator requirements:**

- Must accept exactly one positional argument (the input size N)
- Must be a named function (not a lambda) for pickling
- Must be defined at module level

**Supported complexity classes:**

| Complexity   | Description        |
|--------------|--------------------|
| `O(1)`       | Constant time      |
| `O(log n)`   | Logarithmic        |
| `O(√n)`      | Square root        |
| `O(n)`       | Linear             |
| `O(n log n)` | Linearithmic       |
| `O(n²)`      | Quadratic          |
| `O(n³)`      | Cubic              |
| `O(2ⁿ)`      | Exponential        |

---

## CLI Reference

### `pyforge-benchmark run`

Run all benchmarks and/or complexity analyses.

```bash
pyforge-benchmark run [OPTIONS]
```

| Flag                      | Description                         |
|---------------------------|-------------------------------------|
| `-d, --dir <path>`        | Benchmarks directory (default: `./benchmarks`) |
| `-b, --benchmarks-only`   | Run only benchmark tests            |
| `-c, --complexity-only`   | Run only complexity analysis        |
| `-v, --verbose`           | Print verbose output                |

**Examples:**

```bash
# Run everything
pyforge-benchmark run

# Only benchmarks
pyforge-benchmark run -b

# Only complexity, from a custom directory
pyforge-benchmark run -c -d ./perf_tests

# Verbose mode
pyforge-benchmark run -v
```

### `pyforge-benchmark list`

List all registered benchmark and complexity functions.

```bash
pyforge-benchmark list [OPTIONS]
```

| Flag                 | Description                      |
|----------------------|----------------------------------|
| `-d, --dir <path>`   | Benchmarks directory            |
| `-t, --type <type>`  | Filter: `benchmark` or `complexity` |
| `-v, --verbose`      | Show detailed information       |

### `pyforge-benchmark info`

Display framework version and system information.

```bash
pyforge-benchmark info [--detailed]
```

---

## Architecture

### Execution Flow

```
1. File Discovery     benchmarks/*.py files are found
2. Module Import      Files are imported, triggering decorators
3. Registry Storage   Decorated functions are registered with metadata
4. Subprocess Run     Each function runs in an isolated subprocess
5. Result Collection  Results are gathered via multiprocessing.Queue
6. Report Output      Formatted, colored terminal output
```

### Subprocess Isolation

Every benchmark and complexity measurement runs in a separate `multiprocessing.Process`. This
ensures:

- **No interference** between measurements
- **Timeout protection** for runaway functions
- **GC control** (garbage collection is disabled during measurement)
- **Memory isolation** (each function gets a clean memory state)

### Complexity Analysis Algorithm

The complexity analyzer uses **log-log regression** to determine Big-O:

1. Run the function at multiple input sizes N = (500, 1000, 2500, 5000, 10000, 25000)
2. Measure average execution time for each N
3. Compute `log(t) = k × log(n) + c` via linear regression
4. The exponent `k` directly indicates the polynomial degree
5. Special checks for O(1) and O(log n) which do not follow power-law scaling

The R² value indicates how well the data fits the predicted model (1.0 = perfect fit).

### Benchmark Runner

The benchmark runner automatically adapts iteration count based on function speed:

| Function Speed  | Warmup Iterations | Benchmark Iterations |
|-----------------|-------------------|----------------------|
| Fast (<1s)      | 5                 | 100                  |
| Medium (<10s)   | 2                 | 20                   |
| Slow (>10s)     | 1                 | 5                    |

---

## API Reference

### Programmatic Usage

```python
from pyforge_benchmark import main, run_cycle, print_report

# Run everything and get results
results = main(show_results=False)

# Access raw data
for entry in results["benchmarks"]:
    print(entry["key"], entry["avg_time"])

for entry in results["complexity"]:
    print(entry["key"], entry["big_o"]["complexity"])
```

### Module Exports

```python
from pyforge_benchmark import (
    benchmark,              # Benchmark decorator
    complexity_analysis,    # Complexity analysis decorator
    main,                   # Main entry point
    run_cycle,              # Run cycle without printing
    print_report,           # Print formatted report
)
```

---

## Limitations

- **Python 3.12+ only** — uses modern type syntax
- **No async support** — async functions are not currently supported
- **Pickling required** — all benchmark targets and generators must be picklable
- **Single-machine** — no distributed or multi-machine benchmarking
- **No statistical analysis** — does not compute confidence intervals or p-values
- **Personal use** — not designed for production CI/CD benchmarking pipelines

---

## License

MIT License. See [LICENSE](../LICENSE) for details.
