"""Benchmark runner with subprocess isolation and automatic iteration scaling."""

from __future__ import annotations

import gc
import multiprocessing
import time
from typing import TYPE_CHECKING, Any

from .registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable

PROCESS_TIMEOUT = 10
ITERATION_DECISION_TIMEOUT = 2  # Max 2 seconds for iteration decision
FAST_FUNCTION_THRESHOLD = 1.0
MEDIUM_FUNCTION_THRESHOLD = 10.0


def run_benchmark() -> list[dict[str, Any]]:
    """Run all registered benchmark functions in isolated subprocesses.

    Returns:
        A list of result dictionaries for each registered benchmark.
    """
    registry = Registry()
    results: list[dict[str, Any]] = []

    # Filter only benchmark type functions
    for key, metadata in registry.list_by_type("benchmark"):
        func = metadata["func_ref"]
        args: tuple[Any, ...] = metadata.get("args", ())
        kwargs: dict[str, Any] = metadata.get("kwargs", {})
        result_queue: multiprocessing.Queue[dict[str, Any]] = multiprocessing.Queue()

        process = multiprocessing.Process(
            target=benchmark_worker,
            args=(func, args, kwargs, result_queue),
        )
        process.start()
        process.join(timeout=PROCESS_TIMEOUT)

        if process.is_alive():
            process.terminate()
            process.join()
            results.append(
                {
                    "key": key,
                    "func_ref": func,
                    "status": "error",
                    "error": f"Benchmark timed out after {PROCESS_TIMEOUT}s for {key}",
                }
            )
        elif not result_queue.empty():
            result = result_queue.get_nowait()
            result["key"] = key
            result["func_ref"] = func
            results.append(result)
        else:
            results.append(
                {
                    "key": key,
                    "func_ref": func,
                    "status": "error",
                    "error": f"No result returned for {key}",
                }
            )

    return results


def benchmark_worker(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result_queue: multiprocessing.Queue[dict[str, Any]],
) -> None:
    """Execute benchmark measurements in an isolated subprocess.

    Determines optimal iteration count, runs warmup, then measures
    function execution time over multiple iterations.

    Args:
        func: The function to benchmark.
        args: Positional arguments for the function.
        kwargs: Keyword arguments for the function.
        result_queue: Queue to communicate results back to the main process.
    """
    try:
        # Disable garbage collection to prevent it from affecting benchmark results
        gc.disable()

        # Get warmup and benchmark iterations
        # Use a separate process to avoid long hangs
        decision_queue: multiprocessing.Queue[tuple[int, int]] = multiprocessing.Queue()
        decision_process = multiprocessing.Process(
            target=_iteration_decision_worker,
            args=(func, args, kwargs, decision_queue),
        )
        decision_process.start()
        decision_process.join(timeout=ITERATION_DECISION_TIMEOUT)

        if decision_process.is_alive():
            decision_process.terminate()
            decision_process.join()
            # Use conservative defaults if iteration decision times out
            warmup_iterations, benchmark_iterations = 1, 5
        elif not decision_queue.empty():
            warmup_iterations, benchmark_iterations = decision_queue.get_nowait()
        else:
            # Use conservative defaults if no decision returned
            warmup_iterations, benchmark_iterations = 1, 5

        # Warmup phase
        for _ in range(warmup_iterations):
            func(*args, **kwargs)

        # Benchmark phase
        durations: list[float] = []
        for _ in range(benchmark_iterations):
            start_time = time.perf_counter()
            func(*args, **kwargs)
            end_time = time.perf_counter()
            durations.append(end_time - start_time)

        # Calculate average duration
        avg_time = sum(durations) / len(durations)
        result_queue.put(
            {
                "status": "success",
                "avg_time": avg_time,
                "iterations": benchmark_iterations,
            }
        )
    except Exception as err:
        result_queue.put(
            {
                "status": "error",
                "error": f"Error during benchmark worker for {func}: {err}",
            }
        )
    finally:
        # Re-enable garbage collection after benchmarking
        gc.enable()


def _iteration_decision_worker(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    decision_queue: multiprocessing.Queue[tuple[int, int]],
) -> None:
    """Worker process to determine optimal iteration count."""
    try:
        start_time = time.perf_counter()
        func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if elapsed_time < FAST_FUNCTION_THRESHOLD:
            decision_queue.put((5, 100))  # More iterations for faster functions
        elif elapsed_time < MEDIUM_FUNCTION_THRESHOLD:
            decision_queue.put((2, 20))  # Moderate iterations for medium functions
        else:
            decision_queue.put((1, 5))  # Fewer iterations for slower functions
    except Exception:
        # On any error, use conservative defaults
        decision_queue.put((1, 5))
