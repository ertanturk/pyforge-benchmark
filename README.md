# PyForge Benchmark

A lightweight, zero-dependency Python benchmarking framework for personal projects and learning.

> **Note:** This is a personal/educational project. It is not intended to compete with established
> benchmarking tools like `pytest-benchmark`, `asv`, or `pyperf`.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Typing: Typed](https://img.shields.io/badge/typing-typed-blue.svg)](https://peps.python.org/pep-0561/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)

---

## Features

- **Decorator-based** — add `@benchmark` or `@complexity_analysis` and you're done
- **Subprocess isolation** — each measurement runs in a clean, isolated process
- **Automatic Big-O detection** — determines complexity class via log-log regression
- **Zero dependencies** — uses only the Python standard library
- **Colored terminal output** — aligned, grouped results with Unicode formatting
- **Fully typed** — PEP 561 compliant with `py.typed` marker

## Installation

```bash
pip install pyforge-benchmark
```

Or from source:

```bash
git clone https://github.com/ertanturk/pyforge-benchmark.git
cd pyforge-benchmark
pip install -e .
```

**Requires Python 3.12+**

## Quick Start

### 1. Create a benchmark file

```bash
mkdir benchmarks
```

Create `benchmarks/my_benchmarks.py`:

```python
from pyforge_benchmark import benchmark, complexity_analysis


@benchmark
def my_function():
    return sum(range(1000))


def generate_data(n: int) -> list[int]:
    return list(range(n))


@complexity_analysis(generator=generate_data)
def linear_search(data: list[int]) -> None:
    for item in data:
        _ = item
```

### 2. Run

```bash
pyforge-benchmark run
```

### 3. See results

```
════════════════════════════════════════════════════════════════════════
  BENCHMARK RESULTS
════════════════════════════════════════════════════════════════════════

  ● my_benchmarks.py
  ──────────────────────────────────────────────────────────────────────
    12.34 μs           my_function (Line 4)
                       iterations: 100

════════════════════════════════════════════════════════════════════════
  COMPLEXITY ANALYSIS
════════════════════════════════════════════════════════════════════════

  ● my_benchmarks.py
  ──────────────────────────────────────────────────────────────────────
    O(n)               linear_search (Line 13)
                       R² = 0.984
```

## Usage

### Benchmark Decorator

```python
# Bare decorator
@benchmark
def fast_function():
    return 1 + 2

# With arguments
@benchmark(args=(10000,))
def fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b
```

### Complexity Analysis Decorator

```python
def make_data(n: int) -> list[int]:
    return list(range(n))

@complexity_analysis(generator=make_data)
def bubble_sort(data: list[int]) -> list[int]:
    arr = data.copy()
    for i in range(len(arr)):
        for j in range(len(arr) - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
```

**Generator requirements:**

- Must accept exactly one argument (input size N)
- Must be a named function (not a lambda)
- Must be defined at module level

### Detected Complexity Classes

| Class        | Example               |
| ------------ | --------------------- |
| `O(1)`       | Hash table lookup     |
| `O(log n)`   | Binary search         |
| `O(√n)`      | Trial division        |
| `O(n)`       | Linear scan           |
| `O(n log n)` | Merge sort            |
| `O(n²)`      | Bubble sort           |
| `O(n³)`      | Matrix multiplication |
| `O(2ⁿ)`      | Subset enumeration    |

## CLI

```bash
# Run all benchmarks and complexity analysis
pyforge-benchmark run

# Run only benchmarks
pyforge-benchmark run -b

# Run only complexity analysis
pyforge-benchmark run -c

# Custom benchmarks directory
pyforge-benchmark run -d ./perf_tests

# Verbose output
pyforge-benchmark run -v

# List registered functions
pyforge-benchmark list
pyforge-benchmark list -t complexity

# Show version and system info
pyforge-benchmark info --detailed
```

## Programmatic API

```python
from pyforge_benchmark import main, run_cycle, print_report

# Run and get raw results
results = main(show_results=False)

# Access data
for entry in results["benchmarks"]:
    print(f"{entry['key']}: {entry['avg_time']:.6f}s")

for entry in results["complexity"]:
    print(f"{entry['key']}: {entry['big_o']['complexity']}")
```

## How It Works

### Benchmarking

1. Functions decorated with `@benchmark` are registered in a singleton registry
2. Each function runs in an isolated `multiprocessing.Process`
3. Iteration count adapts automatically (100 for fast, 5 for slow functions)
4. GC is disabled during measurement for accuracy
5. Results are communicated back via `multiprocessing.Queue`

### Complexity Analysis

1. Functions decorated with `@complexity_analysis` are tested at multiple input sizes
2. The generator creates test data for each N value
3. Execution time is measured at N = 500, 1000, 2500, 5000, 10000, 25000
4. Log-log regression (`log(t) = k × log(n) + c`) determines the growth exponent
5. The exponent maps directly to a Big-O complexity class
6. R² indicates model fit quality (1.0 = perfect)

## Project Structure

```
src/pyforge_benchmark/
├── __init__.py             # Public API exports
├── __main__.py             # python -m support
├── benchmark.py            # @benchmark decorator
├── benchmark_runner.py     # Subprocess benchmark execution
├── cli.py                  # Command-line interface
├── complexity.py           # @complexity_analysis decorator
├── complexity_runner.py    # Subprocess complexity measurement
├── main.py                 # Orchestration
├── py.typed                # PEP 561 type stub marker
├── registry.py             # Singleton function registry
└── reporter.py             # Colored terminal output
```

## Development

```bash
# Install in editable mode
pip install -e .

# Lint
ruff check src/
pylint src/pyforge_benchmark/

# Format
ruff format src/
```

## Limitations

- Python 3.12+ only
- No async function support
- All targets and generators must be picklable
- Single-machine only (no distributed benchmarking)
- No statistical confidence intervals
- Designed for personal use, not production CI/CD

## License

[MIT](LICENSE)

## Author

**Ertan Tunç Türk** — [ertantuncturk61@gmail.com](mailto:ertantuncturk61@gmail.com)
