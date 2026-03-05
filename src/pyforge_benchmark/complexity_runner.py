from __future__ import annotations

import gc
import inspect
import math
import multiprocessing
import time
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from .registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable

# Default range of N values to test — use wider spread with more points
# for better log-log regression fit. Larger minimum N reduces constant
# overhead impact on the slope estimate.
DEFAULT_N_RANGE = (1000, 2500, 5000, 10000, 25000, 50000)
PROCESS_TIMEOUT = 30
MIN_EXECUTION_TIME = 1e-6  # 1 microsecond
MAX_ITERATIONS = 100
MIN_MEASUREMENTS = 3
MIN_SAMPLES_PER_N = 5  # Minimum sample count per input size for noise reduction

# R² thresholds for complexity classification
R2_CONSTANT_THRESHOLD = 0.90
R2_LOGARITHMIC_THRESHOLD = 0.95
LOG_EXPONENT_THRESHOLD = 0.15

# Exponent boundaries for Big-O classification
_EXPONENT_BOUNDARIES: dict[float, str] = {
    0.3: "O(log n)",
    0.75: "O(√n)",
    1.25: "O(n)",
    1.75: "O(n log n)",
    2.5: "O(n²)",
    3.5: "O(n³)",
}


class _ComplexityParams(NamedTuple):
    """Parameters for complexity measurement worker."""

    func: Callable[..., Any]
    generator: Callable[..., Any]
    n: int
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


def run_complexity_analysis() -> list[dict[str, Any]]:
    """Run all registered complexity analysis functions in isolated subprocesses.

    Returns:
        A list of result dictionaries for each registered complexity function.
    """
    registry = Registry()
    results: list[dict[str, Any]] = []

    for key, metadata in registry.list_by_type("complexity"):
        func = metadata["func_ref"]
        generator = metadata.get("generator")
        args: tuple[Any, ...] = metadata.get("args", ())
        kwargs: dict[str, Any] = metadata.get("kwargs", {})

        result = _run_complexity_worker(func, generator, args, kwargs)
        result["key"] = key
        result["func_ref"] = func
        results.append(result)

    return results


def _run_complexity_worker(
    func: Callable[..., Any],
    generator: Callable[..., Any] | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Run complexity analysis on a function with subprocess isolation.

    Args:
        func: The function to analyze.
        generator: The data generator callable.
        args: Additional positional arguments.
        kwargs: Additional keyword arguments.

    Returns:
        A result dictionary with measurements and Big-O complexity.
    """
    if generator is None:
        return {
            "status": "error",
            "error": "No generator provided for complexity analysis",
        }

    # Perform pre-flight dry run
    try:
        _perform_dry_run(func, generator, args, kwargs)
    except Exception as e:
        return {"status": "error", "error": f"Dry run failed: {e}"}

    # Run scaling tests
    measurements: list[dict[str, float]] = []
    for n in DEFAULT_N_RANGE:
        params = _ComplexityParams(
            func=func,
            generator=generator,
            n=n,
            args=args,
            kwargs=kwargs,
        )
        result_queue: multiprocessing.Queue[dict[str, Any]] = multiprocessing.Queue()

        process = multiprocessing.Process(
            target=_complexity_measurement_worker,
            args=(params, result_queue),
        )
        process.start()
        process.join(timeout=PROCESS_TIMEOUT)

        if process.is_alive():
            process.terminate()
            process.join()
            # Don't fail entirely — use partial measurements if we have enough
            if len(measurements) >= MIN_MEASUREMENTS:
                break
            return {
                "status": "error",
                "error": f"Complexity measurement timed out for N={n}",
            }

        if not result_queue.empty():
            result = result_queue.get_nowait()
            if result["status"] == "success":
                measurements.append({"n": result["n"], "time": result["avg_time"]})
            else:
                return result

    # Calculate Big-O complexity
    try:
        big_o_result = _calculate_big_o(measurements)
    except Exception as e:
        return {"status": "error", "error": f"Big-O calculation failed: {e}"}

    return {
        "status": "success",
        "measurements": measurements,
        "big_o": big_o_result,
    }


def _perform_dry_run(
    func: Callable[..., Any],
    generator: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Perform a pre-flight check to validate generator and function compatibility.

    Args:
        func: The function to test.
        generator: The data generator.
        args: Additional arguments.
        kwargs: Additional keyword arguments.

    Raises:
        ValueError: If validation fails.
    """
    try:
        test_data = generator(1)
    except Exception as e:
        raise ValueError(f"Generator failed on N=1: {e}") from e

    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot inspect function signature: {e}") from e

    func_params = [
        p
        for p in sig.parameters.values()
        if p.name not in ("self", "cls")
        and p.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]

    param_count = len(func_params)
    if param_count == 1:
        _validate_single_param(test_data)
    elif param_count > 1:
        _validate_multi_param(test_data, func_params)

    _validate_binding(sig, test_data, args, kwargs)


def _validate_single_param(test_data: Any) -> None:
    """Validate test data for single-parameter functions.

    Args:
        test_data: The data to validate.

    Raises:
        ValueError: If validation fails.
    """
    if isinstance(test_data, (tuple, dict)):
        data = cast("tuple[Any, ...] | dict[str, Any]", test_data)
        raise ValueError(
            f"Function expects single object but generator returned {data.__class__.__name__}"
        )


def _validate_multi_param(test_data: Any, func_params: list[Any]) -> None:
    """Validate test data for multi-parameter functions.

    Args:
        test_data: The data to validate.
        func_params: List of function parameters.

    Raises:
        ValueError: If validation fails.
    """
    if isinstance(test_data, tuple):
        data = cast("tuple[Any, ...]", test_data)
        param_count = len(func_params)
        if len(data) != param_count:
            raise ValueError(
                f"Generator returned tuple with {len(data)} items "
                f"but function expects {param_count} parameters"
            )
    elif isinstance(test_data, dict):
        data = cast("dict[str, Any]", test_data)
        param_names = {p.name for p in func_params}
        missing_keys = param_names - data.keys()
        if missing_keys:
            raise ValueError(f"Generator returned dict missing keys: {missing_keys}")
    else:
        param_count = len(func_params)
        raise ValueError(
            f"Function expects {param_count} parameters but "
            f"generator returned {test_data.__class__.__name__}"
        )


def _validate_binding(
    sig: inspect.Signature,
    test_data: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Validate that test data can be bound to function signature.

    Args:
        sig: The function signature.
        test_data: The test data.
        args: Additional positional arguments.
        kwargs: Additional keyword arguments.

    Raises:
        ValueError: If binding fails.
    """
    try:
        if isinstance(test_data, dict):
            bound_args = sig.bind(test_data, *args, **kwargs)
        elif isinstance(test_data, tuple):
            bound_args = sig.bind(*test_data, *args, **kwargs)
        else:
            bound_args = sig.bind(test_data, *args, **kwargs)
        bound_args.apply_defaults()
    except TypeError as e:
        raise ValueError(f"Signature binding failed: {e}") from e


def _call_func_with_data(
    func: Callable[..., Any],
    test_data: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """Call function with test data using appropriate unpacking.

    Args:
        func: The function to call.
        test_data: The test data.
        args: Additional arguments.
        kwargs: Additional keyword arguments.
    """
    if isinstance(test_data, dict):
        func(test_data, *args, **kwargs)
    elif isinstance(test_data, tuple):
        func(*test_data, *args, **kwargs)
    else:
        func(test_data, *args, **kwargs)


def _generate_test_data(
    params: _ComplexityParams,
    result_queue: multiprocessing.Queue[dict[str, Any]],
) -> Any:
    """Generate test data, handling errors and returning None on failure.

    Args:
        params: Complexity measurement parameters.
        result_queue: Queue to communicate errors.

    Returns:
        Test data or None if generation failed.
    """
    try:
        return params.generator(params.n)
    except MemoryError as e:
        result_queue.put(
            {
                "status": "error",
                "error": f"Memory exhaustion at N={params.n}: {e}",
            }
        )
        return None
    except Exception as e:
        result_queue.put(
            {
                "status": "error",
                "error": f"Generator failed at N={params.n}: {e}",
            }
        )
        return None


def _measure_durations(
    params: _ComplexityParams,
    test_data: Any,
) -> list[float]:
    """Measure function durations with auto-scaling iterations.

    Runs the function at least ``MIN_SAMPLES_PER_N`` times to reduce
    measurement noise. For very fast functions the iteration count is
    scaled up further until the average duration exceeds the minimum
    execution-time threshold. Returns the median-filtered durations.

    Args:
        params: Complexity measurement parameters.
        test_data: The initial test data.

    Returns:
        List of duration measurements.
    """
    durations: list[float] = []
    iterations = max(MIN_SAMPLES_PER_N, 1)

    while True:
        iter_durations: list[float] = []

        for iteration in range(iterations):
            if iteration > 0:
                try:
                    test_data = params.generator(params.n)
                except (MemoryError, Exception):
                    break

            gc.disable()
            try:
                start_time = time.perf_counter()
                _call_func_with_data(params.func, test_data, params.args, params.kwargs)
                end_time = time.perf_counter()
                iter_durations.append(end_time - start_time)
            finally:
                gc.enable()

        if not iter_durations:
            break

        avg_duration = sum(iter_durations) / len(iter_durations)
        if avg_duration >= MIN_EXECUTION_TIME or iterations >= MAX_ITERATIONS:
            durations.extend(iter_durations)
            break

        iterations = min(iterations * 2, MAX_ITERATIONS)

    return durations


def _complexity_measurement_worker(
    params: _ComplexityParams,
    result_queue: multiprocessing.Queue[dict[str, Any]],
) -> None:
    """Measure function execution time for a given N value.

    Runs in an isolated subprocess with controlled environment.

    Args:
        params: Complexity measurement parameters.
        result_queue: Queue to communicate results.
    """
    try:
        gc.collect()
        test_data = _generate_test_data(params, result_queue)
        if test_data is None:
            return

        durations = _measure_durations(params, test_data)
        # Use median to reduce impact of outliers from GC pauses or scheduling
        sorted_durations = sorted(durations) if durations else []
        median_time = sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0.0

        result_queue.put(
            {
                "status": "success",
                "n": params.n,
                "avg_time": median_time,
                "iterations": len(durations),
                "samples": len(durations),
            }
        )
    except Exception as err:
        result_queue.put(
            {
                "status": "error",
                "error": f"Error during complexity measurement for N={params.n}: {err}",
            }
        )
    finally:
        gc.enable()


def _calculate_big_o(measurements: list[dict[str, float]]) -> dict[str, Any]:
    """Calculate Big-O complexity using log-log regression.

    Uses the relationship log(t) = k * log(n) + c to determine the
    polynomial degree k. Then matches k to the closest known complexity
    class. This is more robust than fitting each model independently
    because it directly measures the growth exponent.

    Also tests O(1) and O(log n) explicitly since they don't follow
    the power-law assumption.

    Args:
        measurements: List of {n, time} measurements.

    Returns:
        Dictionary with Big-O complexity classification and fit quality.

    Raises:
        ValueError: If calculation fails.
    """
    if len(measurements) < MIN_MEASUREMENTS:
        raise ValueError(f"At least {MIN_MEASUREMENTS} measurements required for Big-O calculation")

    n_values = [m["n"] for m in measurements]
    time_values = [m["time"] for m in measurements]

    if any(t <= 0 for t in time_values):
        raise ValueError("All time values must be positive for Big-O calculation")

    # 1. Fit the log-log model: log(t) = k * log(n) + c
    #    The exponent k tells us the polynomial degree directly.
    log_n = [math.log(x) for x in n_values]
    log_t = [math.log(x) for x in time_values]
    exponent, _intercept, power_r2 = _linear_regression(log_n, log_t)

    # 2. Also test special models that don't fit power-law
    r2_constant = _fit_r_squared_constant([float(x) for x in n_values], time_values)
    r2_logarithmic = _fit_r_squared_model([math.log(x) for x in n_values], time_values)

    # 3. Determine best complexity class
    #    Priority: check O(1) and O(log n) first (special cases),
    #    then use the exponent to classify polynomial growth.
    if r2_constant > R2_CONSTANT_THRESHOLD and r2_constant >= power_r2:
        return {
            "complexity": "O(1)",
            "r_squared": round(r2_constant, 3),
            "coefficient": None,
        }

    if r2_logarithmic > R2_LOGARITHMIC_THRESHOLD and exponent < LOG_EXPONENT_THRESHOLD:
        return {
            "complexity": "O(log n)",
            "r_squared": round(r2_logarithmic, 3),
            "coefficient": None,
        }

    # Use the exponent from log-log regression to classify
    complexity = _classify_exponent(exponent)

    return {
        "complexity": complexity,
        "r_squared": round(power_r2, 3),
        "coefficient": round(exponent, 3),
    }


def _fit_r_squared_constant(n_values: list[float], time_values: list[float]) -> float:
    """Calculate a goodness-of-fit score for O(1) constant time.

    Measures how little the time depends on n by computing
    1 - R²(t ~ n). A value close to 1.0 means time does NOT
    depend on n, indicating O(1) behaviour.

    Args:
        n_values: Input size values.
        time_values: Corresponding time measurements.

    Returns:
        Score between 0 and 1 (higher = more constant).
    """
    _, _, r2_linear = _linear_regression(n_values, time_values)
    return max(0.0, 1.0 - r2_linear)


def _fit_r_squared_model(x_values: list[float], y_values: list[float]) -> float:
    """Calculate R² for a linear model y = m*x + b.

    Args:
        x_values: Transformed independent variable.
        y_values: Time values.

    Returns:
        R² value for the fit.
    """
    _, _, r_squared = _linear_regression(x_values, y_values)
    return r_squared


def _classify_exponent(exponent: float) -> str:
    """Classify the growth exponent into a Big-O complexity class.

    The exponent k from log(t) = k * log(n) + c maps to:
        k ~ 0     -> O(1) or O(log n)
        k ~ 0.5   -> O(sqrt(n))
        k ~ 1     -> O(n)
        k ~ 1-1.5 -> O(n log n) (slightly super-linear)
        k ~ 2     -> O(n^2)
        k ~ 3     -> O(n^3)
        k > 4     -> O(2^n)  (exponential, but rare in log-log)

    Args:
        exponent: The growth exponent from log-log regression.

    Returns:
        Big-O complexity string.
    """
    for boundary, complexity in _EXPONENT_BOUNDARIES.items():
        if exponent < boundary:
            return complexity
    return "O(2ⁿ)"


def _linear_regression(x_values: list[float], y_values: list[float]) -> tuple[float, float, float]:
    """Perform linear regression and return slope, intercept, and R².

    Args:
        x_values: Independent variable values.
        y_values: Dependent variable values.

    Returns:
        Tuple of (slope, intercept, r_squared).
    """
    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values, strict=True))
    sum_x2 = sum(x**2 for x in x_values)

    denominator = n * sum_x2 - sum_x**2
    if denominator == 0:
        return 0.0, 0.0, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # Calculate R²
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in y_values)
    ss_res = sum(
        (y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values, strict=True)
    )

    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    return slope, intercept, r_squared
