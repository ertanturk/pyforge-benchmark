"""Singleton registry for storing benchmark and complexity analysis metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable


class Registry:
    """Singleton registry for benchmark and complexity function metadata.

    Uses a class-level store so all instances share the same registered
    functions. Access via ``Registry()`` from anywhere in the codebase.
    """

    instance: ClassVar[Registry | None] = None
    __store: ClassVar[dict[str, Any]] = {}

    def __new__(cls) -> Registry:
        """Create or return the singleton Registry instance.

        Returns:
            The single Registry instance.

        Raises:
            RuntimeError: If instance creation fails.
        """
        try:
            if cls.instance is None:
                cls.instance = super().__new__(cls)
            return cls.instance
        except Exception as e:
            raise RuntimeError(f"Error creating Registry instance: {e}") from e

    def __generate_key(self, func: Callable[..., Any]) -> str:
        """Generate a unique key for the given function.

        Args:
            func (Callable[..., Any]): The function for which to generate a key.

        Returns:
            str: A unique key in the format 'module.qualname' for the function.
        """
        try:
            return f"{func.__module__}.{func.__qualname__}"
        except Exception as e:
            raise ValueError(f"Error generating key for function {func}: {e}") from e

    def register(
        self,
        func: Callable[..., Any],
        test_type: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        **metadata_kwargs: Any,
    ) -> None:
        """Register a function with a unique key.

        Args:
            func: The function to register.
            test_type: The type of the test.
            args: Positional arguments to pass when benchmarking.
            kwargs: Keyword arguments to pass when benchmarking.
            **metadata_kwargs: Additional metadata to store (e.g., generator).
        """
        try:
            unique_key = self.__generate_key(func)
            metadata: dict[str, Any] = {
                "func_ref": func,
                "type": test_type,
                "args": args,
                "kwargs": kwargs or {},
                **metadata_kwargs,
            }
            self.__store[unique_key] = metadata
        except Exception as e:
            raise RuntimeError(f"Error registering function {func}: {e}") from e

    def remove(self, key: str) -> None:
        """Remove a function from the registry.

        Args:
            key (str): The unique key of the function to remove.
        """
        try:
            if key in self.__store:
                del self.__store[key]
            else:
                raise KeyError(f"Key '{key}' not found in registry.")
        except Exception as e:
            raise RuntimeError(f"Error removing key '{key}': {e}") from e

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve the metadata for a registered function.

        Args:
            key (str): The unique key of the function to retrieve.

        Returns:
            dict[str, Any] | None: The metadata for the function, or None if not found.
        """
        try:
            return self.__store.get(key)
        except Exception as e:
            raise RuntimeError(f"Error retrieving metadata for key '{key}': {e}") from e

    def list_registered(self) -> list[str]:
        """List all registered functions in the registry.

        Returns:
            list[str]: A list of unique keys for all registered functions.
        """
        try:
            return list(self.__store.keys())
        except Exception as e:
            raise RuntimeError(f"Error listing registered functions: {e}") from e

    def clear(self) -> None:
        """Clear all entries from the registry."""
        try:
            self.__store.clear()
        except Exception as e:
            raise RuntimeError(f"Error clearing registry: {e}") from e

    def filter_by_type(self, test_type: str) -> list[dict[str, Any]]:
        """Filter registered functions by their test type.

        Args:
            test_type (str): The type of the test to filter by.

        Returns:
            list[dict[str, Any]]: A list of metadata dictionaries
            for functions matching the specified test type.
        """
        try:
            return [metadata for metadata in self.__store.values() if metadata["type"] == test_type]
        except Exception as e:
            raise RuntimeError(f"Error filtering registry by type '{test_type}': {e}") from e

    def list_by_type(self, test_type: str) -> list[tuple[str, dict[str, Any]]]:
        """List all registered functions of a given type as (key, metadata) pairs.

        Args:
            test_type (str): The type of the test to filter by.

        Returns:
            list[tuple[str, dict[str, Any]]]: A list of (key, metadata) tuples.
        """
        try:
            return [
                (key, metadata)
                for key, metadata in self.__store.items()
                if metadata["type"] == test_type
            ]
        except Exception as e:
            raise RuntimeError(f"Error listing registry by type '{test_type}': {e}") from e
