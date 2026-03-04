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
    """

    def _register(fn: Callable[..., Any]) -> Callable[..., Any]:
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
        return _register(func)
    return _register
