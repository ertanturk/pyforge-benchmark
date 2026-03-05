import inspect
import pickle
import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any

from .registry import Registry


def _validate_function(fn: Callable[..., Any]) -> None:
    """Validate that the function is suitable for complexity analysis.

    Args:
        fn: The function to validate.

    Raises:
        ValueError: If the function is not callable, is a lambda, or is async.
    """
    if not callable(fn):
        raise ValueError(f"Decorated target must be callable, got {type(fn).__name__}")

    if fn.__name__ == "<lambda>":
        raise ValueError("Lambda functions cannot be analyzed (not picklable)")

    if inspect.iscoroutinefunction(fn):
        raise ValueError("Async functions are not supported for complexity analysis")


def _count_required_params(sig: inspect.Signature) -> list[str]:
    """Count required parameters excluding self/cls.

    Args:
        sig: The function signature.

    Returns:
        List of required parameter names.
    """
    required: list[str] = []
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    return required


def _check_var_params(sig: inspect.Signature) -> tuple[bool, bool]:
    """Check if signature has *args or **kwargs.

    Args:
        sig: The function signature.

    Returns:
        Tuple of (has_var_args, has_var_kwargs).
    """
    has_var_args = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    return has_var_args, has_var_kwargs


def _validate_generator(generator: Callable[..., Any]) -> None:
    """Validate that the generator is suitable for complexity analysis.

    Args:
        generator: The generator function to validate.

    Raises:
        ValueError: If the generator is invalid.
    """
    if not callable(generator):
        raise ValueError(f"Generator must be callable, got {type(generator).__name__}")

    if generator.__name__ == "<lambda>":
        raise ValueError("Lambda generators cannot be analyzed (not picklable)")

    try:
        gen_sig = inspect.signature(generator)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot inspect generator signature: {e}") from e

    gen_params = [
        p
        for p in gen_sig.parameters.values()
        if p.name not in ("self", "cls")
        and p.kind
        not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]
    if len(gen_params) != 1:
        raise ValueError(
            f"Generator must accept exactly one positional argument (N), got {len(gen_params)}"
        )

    try:
        pickle.dumps(generator)
    except (pickle.PicklingError, TypeError) as e:
        # If the error is about attribute lookup on the generator's module,
        # it's likely because the module is still being imported.
        if not ("attribute lookup" in str(e) and generator.__module__ in str(e)):
            raise ValueError(f"Generator is not picklable: {e}") from e


def _validate_picklable(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any] | None,
) -> None:
    """Validate that function and arguments are picklable.

    Args:
        fn: The function to check.
        args: Positional arguments.
        kwargs: Keyword arguments.

    Raises:
        ValueError: If any component is not picklable.
    """
    try:
        pickle.dumps(fn)
        pickle.dumps(args)
        pickle.dumps(kwargs or {})
    except (pickle.PicklingError, TypeError) as e:
        # If the error is about attribute lookup on the function's module,
        # it's likely because the module is still being imported.
        # The function will be available in sys.modules when complexity analysis runs.
        if not ("attribute lookup" in str(e) and fn.__module__ in str(e)):
            raise ValueError(f"Function, args, or kwargs are not picklable: {e}") from e


def complexity_analysis(
    func: Callable[..., Any] | None = None,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    generator: Callable[..., Any] | None = None,
) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a callable function for complexity analysis.

    Can be used as a bare decorator or with parameters:
        @complexity_analysis
        def my_func(n): ...

        @complexity_analysis(generator=lambda n: list(range(n)))
        def my_func(data): ...

    Args:
        func: The callable when used as a bare decorator.
        args: Positional arguments to pass during analysis.
        kwargs: Keyword arguments to pass during analysis.
        generator: A callable that accepts one positional argument (N) and
            generates test data. Required if func has required parameters.

    Returns:
        The decorated function, or a decorator if called with parameters.

    Raises:
        ValueError: If func is not callable, generator requirements not met,
            or inputs are not picklable.
        RuntimeError: If registration fails.
    """

    def _register(fn: Callable[..., Any]) -> Callable[..., Any]:
        _validate_function(fn)

        try:
            sig = inspect.signature(fn)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot inspect function signature: {e}") from e

        required_params = _count_required_params(sig)
        has_var_args, has_var_kwargs = _check_var_params(sig)

        # Validate generator requirements
        if required_params or has_var_args or has_var_kwargs:
            if generator is None:
                raise ValueError(
                    f"Function {fn.__name__} has required/variable parameters "
                    f"({', '.join(required_params)}) but no generator provided"
                )
        elif generator is not None:
            warnings.warn(
                f"Function {fn.__name__} takes no required parameters "
                f"but a generator was provided; it will be ignored",
                UserWarning,
                stacklevel=2,
            )

        if generator is not None:
            _validate_generator(generator)

        _validate_picklable(fn, args, kwargs)

        # Register in registry
        try:
            registry = Registry()
            registry.register(
                fn,
                test_type="complexity",
                args=args,
                kwargs=kwargs or {},
                generator=generator,
            )
        except Exception as e:
            raise RuntimeError(f"Error registering complexity analysis for {fn}: {e}") from e

        @wraps(fn)
        def wrapper(*call_args: Any, **call_kwargs: Any) -> Any:
            return fn(*call_args, **call_kwargs)

        return wrapper

    if func is not None:
        if not callable(func):
            raise ValueError(f"Decorated target must be callable, got {type(func).__name__}")
        return _register(func)
    return _register
