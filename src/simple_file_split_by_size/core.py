"""Core splitting logic.

The implementation uses a streaming reader so files much larger than
``chunk_bytes`` do not need to be held in memory. Output filenames are
``"{output_prefix}.{i:03d}"`` — three-digit zero-padded indices — which keeps
files sortable in a directory listing up to 999 parts. Callers needing more
parts should build their own naming on top of the returned list of ``Part``
records.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import BinaryIO, Iterator, Union


@dataclass(frozen=True)
class Part:
    """One output file produced by :func:`split_file_by_size`.

    The ``index`` field is zero-based and corresponds to the numeric suffix
    on the file's name. ``size`` is in bytes.
    """

    path: str
    index: int
    size: int


@dataclass(frozen=True)
class SplitResult:
    """Outcome of a split: the total number of parts and a list of them."""

    parts: list
    part_count: int


def _open_for_read(source: Union[str, os.PathLike, BinaryIO]) -> BinaryIO:
    """Return a binary file handle.

    If ``source`` is already a readable binary stream we pass it through
    unchanged so the caller can manage its lifetime (useful for pipes,
    in-memory objects, etc.). Otherwise we open the path in read-binary mode
    and mark the handle for closing when the split is done.
    """

    if hasattr(source, "read"):
        return source
    return open(source, "rb")


def _iter_chunks(handle: BinaryIO, chunk_bytes: int) -> Iterator[bytes]:
    """Yield successive ``chunk_bytes``-sized chunks from ``handle``.

    Reading in fixed slices (rather than ``read()`` with no argument) bounds
    peak memory to ``chunk_bytes`` even for multi-gigabyte inputs.
    """

    while True:
        block = handle.read(chunk_bytes)
        if not block:
            return
        yield block


def split_file_by_size(
    source,
    chunk_bytes,
    output_prefix,
):
    """Split ``source`` into part files each no larger than ``chunk_bytes``.

    Parameters
    ----------
    source
        Path to the input file, or an already-open readable binary stream.
        When a stream is passed the function does not close it — that remains
        the caller's responsibility.
    chunk_bytes
        Maximum size in bytes of each output part. Must be a positive integer.
    output_prefix
        Output path prefix; each part is written as ``"{output_prefix}.{i:03d}"``
        where ``i`` is the zero-based part index.

    Returns
    -------
    SplitResult
        ``parts`` is a list of :class:`Part` in index order;
        ``part_count`` is its length.

    Raises
    ------
    ValueError
        If ``chunk_bytes`` is not a positive integer.
    TypeError
        If ``chunk_bytes`` is not an ``int``.

    Notes
    -----
    An empty input file produces exactly one empty (zero-byte) output part.
    This makes the split operation total — every input maps to at least one
    output — and keeps reassembly straightforward: concatenate every part in
    index order, including the trailing empty file, and the result equals the
    input. Callers that prefer zero parts for an empty input should check the
    input file's size before calling.
    """

    if not isinstance(chunk_bytes, int) or isinstance(chunk_bytes, bool):
        raise TypeError("chunk_bytes must be an int")
    if chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be positive")

    own_handle = False
    try:
        handle = _open_for_read(source)
        own_handle = not hasattr(source, "read")

        parts = []
        index = 0
        for block in _iter_chunks(handle, chunk_bytes):
            path = "{}.{:03d}".format(output_prefix, index)
            with open(path, "wb") as out:
                out.write(block)
            parts.append(Part(path=path, index=index, size=len(block)))
            index += 1

        if not parts:
            path = "{}.000".format(output_prefix)
            with open(path, "wb"):
                pass
            parts.append(Part(path=path, index=0, size=0))

        return SplitResult(parts=parts, part_count=len(parts))
    finally:
        if own_handle:
            handle.close()
