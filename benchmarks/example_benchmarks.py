"""Example benchmark file demonstrating PyForge Benchmark capabilities."""

from pyforge_benchmark import benchmark, complexity_analysis


# Generator functions for complexity analysis
def generate_list(n: int) -> list[int]:
    """Generate a list of integers from 0 to n-1."""
    return list(range(n))


# Simple function for benchmarking
@benchmark
def simple_addition():
    """A simple benchmark test."""
    return 1 + 2


# Benchmark with arguments
@benchmark(args=(10000,))
def fibonacci(n: int) -> int:
    """Calculate fibonacci number - iterative version.

    Uses iteration to avoid recursion depth issues and demonstrate
    argument passing in benchmarks.
    """
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# Complexity analysis with data generator
@complexity_analysis(generator=generate_list)
def linear_search(data: list[int]) -> None:
    """Linear search through data - O(n) complexity."""
    for item in data:
        _ = item


@complexity_analysis(generator=generate_list)
def bubble_sort(data: list[int]) -> list[int]:
    """Bubble sort - O(n²) complexity."""
    arr = data.copy()
    for i in range(len(arr)):
        for j in range(len(arr) - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
