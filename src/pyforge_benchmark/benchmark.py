"""Decorator for registering functions as benchmarks."""

import pickle
from collections.abc import Callable
from functools import wraps
from typing import Any, overload

from .registry import Registry


@overload
def benchmark(func: Callable[..., Any]) -> Callable[..., Any]: ...


@overload
def benchmark(
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


def benchmark(
    func: Callable[..., Any] | None = None,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a callable function as a benchmark.

    Can be used as a bare decorator or with parameters:
        @benchmark
        def my_func(): ...

        @benchmark(args=(42,), kwargs={"key": "value"})
        def my_func(n, key=""): ...

    Args:
        func: The callable when used as a bare decorator.
        args: Positional arguments to pass when benchmarking.
        kwargs: Keyword arguments to pass when benchmarking.

    Returns:
        The decorated function, or a decorator if called with parameters.

    Raises:
        ValueError: If func is not callable or if the function is not picklable.
        RuntimeError: If registration fails.
    """

    def _register(fn: Callable[..., Any]) -> Callable[..., Any]:
        # Check if fn is callable
        if not callable(fn):
            raise ValueError(f"Decorated target must be callable, got {type(fn).__name__}")

        # Check if function is a lambda (not directly picklable)
        if fn.__name__ == "<lambda>":
            raise ValueError("Lambda functions cannot be benchmarked (not picklable)")

        try:
            pickle.dumps(fn)
            pickle.dumps(args)
            pickle.dumps(kwargs or {})
        except (pickle.PicklingError, TypeError) as e:
            # If the error is about attribute lookup on the function's module,
            # it's likely because the module is still being imported.
            # The function will be available in sys.modules when benchmarks run.
            if not ("attribute lookup" in str(e) and fn.__module__ in str(e)):
                raise ValueError(f"Function, args, or kwargs are not picklable: {e}") from e

        try:
            registry = Registry()
            registry.register(fn, test_type="benchmark", args=args, kwargs=kwargs or {})
        except Exception as e:
            raise RuntimeError(f"Error registering benchmark for {fn}: {e}") from e

        @wraps(fn)
        def wrapper(*call_args: Any, **call_kwargs: Any) -> Any:
            return fn(*call_args, **call_kwargs)

        return wrapper

    if func is not None:
        # When used as @benchmark (bare decorator), validate func is callable
        if not callable(func):
            raise ValueError(f"Decorated target must be callable, got {type(func).__name__}")
        return _register(func)
    return _register
