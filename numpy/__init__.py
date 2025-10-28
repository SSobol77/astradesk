"""
Minimal stub implementation of a subset of the NumPy API needed for the tests.

The goal of this stub is not to be fast nor feature complete — it merely provides
enough functionality for small numerical routines built on top of simple Python
lists.  Only the symbols that are exercised by the test-suite are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
import random as _py_random
from typing import Iterable, List, Sequence, Tuple, Union

Number = Union[int, float]


def _as_float(value: Number) -> float:
    return float(value)


@dataclass
class _Array:
    """Lightweight array wrapper backed by nested Python lists."""

    _data: List[List[float]]
    _cols: int = 0

    def __post_init__(self) -> None:
        if any(not isinstance(row, list) for row in self._data):
            self._data = [list(row) for row in self._data]
        if self._data and self._cols == 0:
            self._cols = len(self._data[0])

    # -- Python protocol helpers -------------------------------------------------
    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, key, value) -> None:
        if isinstance(key, tuple):
            row, col = key
            self._data[row][col] = _as_float(value)
        elif isinstance(key, slice):
            self._data[key] = value
        else:
            if isinstance(value, list):
                self._data[key] = [_as_float(v) for v in value]
            else:
                self._data[key] = _as_float(value)

    def __repr__(self) -> str:
        return f"_Array({self._data!r})"

    # -- Convenience API ---------------------------------------------------------
    def copy(self) -> "_Array":
        return _Array([row[:] for row in self._data], self._cols)

    def tolist(self) -> List[List[float]]:
        return [row[:] for row in self._data]

    @property
    def shape(self) -> Tuple[int, int]:
        rows = len(self._data)
        return rows, self._cols

    def astype(self, dtype) -> "_Array":
        # We only support casting to float32/float (treated the same here).
        if dtype not in (float32, float):
            raise TypeError("Unsupported dtype for stub array.")
        return _Array([[dtype(x) for x in row] for row in self._data], self._cols)


def _ensure_array(values: Iterable[Iterable[Number]], cols: int | None = None) -> _Array:
    data = [[float(v) for v in row] for row in values]
    if cols is None and data:
        cols = len(data[0])
    return _Array(data, cols or 0)


def array(values: Sequence[Sequence[Number]], dtype=None) -> _Array:
    arr = _ensure_array(values)
    return arr.astype(dtype) if dtype else arr


def zeros(shape: Tuple[int, int], dtype=None) -> _Array:
    rows, cols = shape
    data = [[0.0 for _ in range(cols)] for _ in range(rows)]
    arr = _ensure_array(data, cols=cols)
    return arr.astype(dtype) if dtype else arr


float32 = float  # pragma: no mutate - treat float32 the same as float


class _RandomModule:
    @staticmethod
    def rand(*shape: int) -> _Array:
        if not shape:
            raise ValueError("shape is required")
        if len(shape) == 1:
            rows, cols = shape[0], 1
        else:
            rows, cols = shape
        data = [[_py_random.random() for _ in range(cols)] for _ in range(rows)]
        return _ensure_array(data, cols=cols)


random = _RandomModule()


def clip(values: Sequence[float], min_value: float, max_value: float) -> List[float]:
    return [max(min(v, max_value), min_value) for v in values]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def inner(a: Sequence[float], b: Sequence[float]) -> float:
    return dot(a, b)


def argsort(values: Sequence[float], reverse: bool = False) -> List[int]:
    return sorted(range(len(values)), key=values.__getitem__, reverse=reverse)


def linalg_norm(vector: Sequence[float]) -> float:
    return sum(x * x for x in vector) ** 0.5


class _LinalgModule:
    @staticmethod
    def norm(vector: Sequence[float]) -> float:
        return linalg_norm(vector)


linalg = _LinalgModule()


class _TestingModule:
    @staticmethod
    def assert_array_equal(left, right) -> None:
        def _convert(obj):
            if hasattr(obj, "tolist"):
                return obj.tolist()
            return obj

        if _convert(left) != _convert(right):
            raise AssertionError(f"Arrays are not equal: {left!r} != {right!r}")


testing = _TestingModule()


__all__ = [
    "_Array",
    "array",
    "zeros",
    "float32",
    "random",
    "clip",
    "dot",
    "inner",
    "argsort",
    "linalg",
    "testing",
]
