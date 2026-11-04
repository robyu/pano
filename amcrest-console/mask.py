#!/usr/bin/env python3
"""Legacy Amcrest/Dahua motion-mask codec.

The camera stores the legacy mask as 18 integers, one per row. Each integer is
a 22-bit bitmap; bit 0 is the leftmost cell and a set bit means "monitored".
The newer ``MotionDetectWindow`` model is read-only for pano and is not encoded
here.

This module is stdlib only and has no camera/network side effects.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, List, Sequence

from camera import COLS, ROWS

FULL_ROW = (1 << COLS) - 1
FULL_MASK = [FULL_ROW] * ROWS
EMPTY_MASK = [0] * ROWS


class MaskError(ValueError):
    """Raised when a mask cannot be decoded or encoded safely."""


def decode(region_values: Iterable[int]) -> List[List[int]]:
    """Decode 18 row integers into an 18x22 grid of 0/1 cells."""
    values = list(region_values)
    if len(values) != ROWS:
        raise MaskError("expected {} region rows, got {}".format(ROWS, len(values)))
    grid: List[List[int]] = []
    for row, value in enumerate(values):
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, int):
            raise MaskError("region row {} is not an integer".format(row))
        if value < 0 or value > FULL_ROW:
            raise MaskError(
                "region row {} out of range: {}".format(row, value)
            )
        grid.append([(value >> col) & 1 for col in range(COLS)])
    return grid


def validate(rows: Sequence[Sequence[Any]]) -> List[List[int]]:
    """Validate and normalize a grid; raise MaskError on anything unusual."""
    if not isinstance(rows, (list, tuple)):
        raise MaskError("rows must be an 18x22 array")
    if len(rows) != ROWS:
        raise MaskError("expected {} rows, got {}".format(ROWS, len(rows)))
    grid: List[List[int]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            raise MaskError("row {} is not an array".format(row_index))
        if len(row) != COLS:
            raise MaskError(
                "row {} has {} cells, expected {}".format(
                    row_index, len(row), COLS
                )
            )
        normalized: List[int] = []
        for col_index, cell in enumerate(row):
            if cell is True or cell == 1:
                normalized.append(1)
            elif cell is False or cell == 0:
                normalized.append(0)
            else:
                raise MaskError(
                    "cell [{}, {}] must be 0 or 1".format(row_index, col_index)
                )
        grid.append(normalized)
    return grid


def encode(rows: Sequence[Sequence[Any]]) -> List[int]:
    """Encode an 18x22 grid into 18 row integers (LSB = leftmost)."""
    grid = validate(rows)
    values: List[int] = []
    for row in grid:
        value = 0
        for col, cell in enumerate(row):
            if cell:
                value |= 1 << col
        values.append(value)
    return values


def revision_from_regions(region_values: Iterable[int]) -> str:
    """Stable hash of the encoded mask, used to detect stale edits."""
    values = encode(decode(region_values))
    canonical = ",".join(str(value) for value in values)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def revision(rows: Sequence[Sequence[Any]]) -> str:
    return revision_from_regions(encode(rows))


def ascii(rows: Sequence[Sequence[Any]]) -> str:
    grid = validate(rows)
    return "\n".join(
        "".join("#" if cell else "." for cell in row) for row in grid
    )


def invert(rows: Sequence[Sequence[Any]]) -> List[List[int]]:
    grid = validate(rows)
    return [[0 if cell else 1 for cell in row] for row in grid]


def clear() -> List[List[int]]:
    return [[0] * COLS for _ in range(ROWS)]


def full() -> List[List[int]]:
    return [[1] * COLS for _ in range(ROWS)]


def count(rows: Sequence[Sequence[Any]]) -> int:
    grid = validate(rows)
    return sum(sum(row) for row in grid)
