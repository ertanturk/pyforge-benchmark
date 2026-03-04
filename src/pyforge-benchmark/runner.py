from __future__ import annotations

import gc
import multiprocessing
import time
from collections.abc import Callable
from typing import Any

from .registry import Registry

PROCESS_TIMEOUT = 10


def run_benchmark() -> list[dict[str, Any]]:
    """Run all registered benchmark functions in isolated subprocesses.

    Returns:
        A list of result dictionaries for each registered benchmark.
    """
    registry = Registry()
    results: list[dict[str, Any]] = []

    for key in registry.list_registered():
        metadata = registry.get(key)
        if metadata is None:
            continue

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
                    "status": "error",
                    "error": f"Benchmark timed out after {PROCESS_TIMEOUT}s for {key}",
                }
            )
        elif not result_queue.empty():
            result = result_queue.get_nowait()
            result["key"] = key
            results.append(result)
        else:
            results.append(
                {
                    "key": key,
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
    try:
        # Disable garbage collection to prevent it from affecting benchmark results
        gc.disable()

        # Get warmup and benchmark iterations
        warmup_iterations, benchmark_iterations = benchmark_iteration_decision(func, args, kwargs)

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


def benchmark_iteration_decision(
    func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[int, int]:
    try:
        start_time = time.perf_counter()
        func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        if elapsed_time < 1.0:
            return 5, 100  # More iterations for faster functions
        elif elapsed_time < 10.0:
            return 2, 20  # Moderate iterations for medium functions
        else:
            return 1, 5  # Fewer iterations for slower functions
    except Exception as err:
        raise RuntimeError(f"Error during benchmark iteration decision for {func}") from err
