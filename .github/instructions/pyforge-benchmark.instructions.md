---
description: "Use when writing or modifying Python code in the pyforge-benchmark project. Covers type hints, docstrings, error handling, naming, and project conventions."
applyTo: "src/**/*.py"
---

# pyforge-benchmark Coding Conventions

## Type Hints

- Use modern union syntax: `dict[str, Any] | None`, not `Optional[dict[str, Any]]`
- Import from `collections.abc` for `Callable`, `Iterator`, etc.
- Annotate all function parameters and return types
- Use `ClassVar` for class-level variables

```python
from collections.abc import Callable
from typing import Any, ClassVar

def register(self, func: Callable[..., Any], test_type: str) -> str:
```

## Docstrings

- Google-style with `Args:` and `Returns:` sections
- Required on all public methods and classes

```python
def register(self, func: Callable[..., Any], test_type: str) -> str:
    """Register a callable function in the benchmark registry.

    Args:
        func: The callable function to register.
        test_type: Category label for the benchmark.

    Returns:
        The generated unique key for the registered function.
    """
```

## Error Handling

- Wrap operations in try-except; raise `RuntimeError` for failures, `ValueError` for invalid input
- Always chain exceptions with `from e`

```python
try:
    key = self.__generate_key(func)
except Exception as e:
    raise RuntimeError(f"Failed to register function: {func}") from e
```

## Naming & Visibility

- Private internals use double underscore: `__store`, `__generate_key()`
- Public API methods use plain snake_case: `register()`, `list_registered()`

## Style

- Line length: 100 characters
- Double quotes for strings
- 4-space indentation
- Target: Python 3.12+
- Linting: Ruff (rules: E, W, F, I, UP, B, C4, SIM, RUF, PL, ARG)

## Project Architecture

- Zero external runtime dependencies
- Singleton pattern for shared state (Registry)
- Module key format: `module.qualname` for unique function identification

## Benchmark Cycle

```
Benchmark: File Scanner -> Module Importer -> Decorator Trigger -> Registry Storage
  -> Main Engine Loop -> Data Serialization -> Subprocess Spawner -> Warmup Phase
  -> Measurement Phase -> Result Aggregation

Complexity Analyzer: Input Size Definition -> Data Generation -> Subprocess Execution
  -> Time Mapping -> Mathematical Regression -> Big-O Result
```

## Runner Cycle (runner.py)

The runner uses Python's built-in `multiprocessing` module as the execution engine. It is better
suited than `subprocess` because it natively handles passing Python objects (like functions) between
processes using `pickle`.

### 1. The Data Pipeline (`multiprocessing.Queue`)

Isolated processes do not share memory, so they communicate via a `Queue`. The main process creates
it, the worker subprocess writes the final timing results to it, and the main process reads it.

### 2. The Worker (runs inside the isolated process)

A standard wrapper function executed by the spawned process.

- **Input**: The target function, any required arguments, and the `Queue`.
- **Warmup Phase**: Runs the target function once without recording the time to prime the CPU cache.
- **Measurement Phase**: Runs the target function for a set number of iterations (e.g., 5). Uses
  `time.perf_counter()` to measure each run.
- **Output**: Calculates the average time and puts a result dictionary
  (e.g., `{"status": "success", "avg_time": 0.005}`) into the `Queue`.

### 3. The Manager (runs in the main process)

The core loop that manages the queue and the worker processes.

- **Setup**: Retrieves a function from the registry and creates a new `Queue`.
- **Spawn**: Creates a `multiprocessing.Process` pointing to the Worker function, passes the target
  user function as an argument, and starts the process.
- **Monitor**: Calls `process.join(timeout=10)` — forces the main engine to wait up to 10 seconds
  for the subprocess to finish.
- **Cleanup & Retrieval**:
  - If the process finishes in time, the manager reads the result from the `Queue`.
  - If the timeout hits, the manager terminates the stuck process (`process.terminate()`) and logs
    a timeout error for that function.

## CLI Commands

| Command                                | Purpose                                                 |
| -------------------------------------- | ------------------------------------------------------- |
| `pyforge-benchmark run`                | Run all registered benchmarks                           |
| `pyforge-benchmark run --type <type>`  | Run benchmarks filtered by type (complexity, benchmark) |
| `pyforge-benchmark run <path>`         | Run benchmarks from a specific file or directory        |
| `pyforge-benchmark -c <func1> <func2>` | Compare two functions head-to-head                      |
| `pyforge-benchmark list`               | List all registered benchmark functions                 |

## Edge Cases & Considerations

### Subprocess and Execution Risks

- **Serialization failures**: Subprocess isolation requires pickling. Unpicklable objects (open files, sockets, lambdas) must be detected early and reported with a clear error before spawning
- **Infinite loops**: Enforce a strict timeout on subprocesses; terminate stuck processes and log the failure without blocking the suite
- **Process crashes (OOM)**: Detect abrupt subprocess exits (e.g., OS killing for excessive RAM) and log as failure without crashing the main engine

### Collection and Import Risks

- **Registry key collisions**: Never use raw function names as keys; always use `module.qualname` to avoid overwrites from identically named functions in different files
- **Import side effects**: Importing user files to collect decorators may trigger top-level code outside `if __name__ == "__main__":` blocks; guard against this slowing or breaking the collection phase

### Measurement Accuracy

- **Garbage collection interference**: Temporarily disable GC (`gc.disable()`) during the measurement phase to avoid artificial delays; re-enable immediately after
- **Clock resolution**: For sub-microsecond functions, batch multiple invocations and measure total time rather than individual runs that may read as 0.0s
- **Setup isolation**: Data generation and setup time must be completely excluded from function measurement; run setup before the timed window
