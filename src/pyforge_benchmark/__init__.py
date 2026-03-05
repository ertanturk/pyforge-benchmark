"""PyForge Benchmark - Automated performance testing framework.

A lightweight Python benchmarking framework for personal projects and learning.
Provides decorator-based benchmarks, automatic performance comparison, and
built-in complexity analysis.
"""

from __future__ import annotations

from .benchmark import benchmark
from .complexity import complexity_analysis
from .main import main, run_cycle
from .reporter import print_report

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0dev"
__author__ = "Ertan Tunç Türk"
__email__ = "ertantuncturk61@gmail.com"

__all__ = [
    "__version__",
    "benchmark",
    "complexity_analysis",
    "main",
    "print_report",
    "run_cycle",
]
