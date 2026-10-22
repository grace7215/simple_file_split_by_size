# simple_file_split_by_size

Splits a binary file into chunks no larger than a given byte size, writing part files with zero-padded index suffixes.

```python
from simple_file_split_by_size import split_file_by_size

# Writes 8 bytes to input.bin for this example.
with open("input.bin", "wb") as f:
    f.write(b"abcdefgh")

result = split_file_by_size("input.bin", 4, "input.part")
# Creates input.part.000, input.part.001, ...
for part in result.parts:
    print(part.path, part.index, part.size)
```

## Why this exists

When you need to move a large file across size-limited channels — email
attachments, FAT32 volumes, simple HTTP uploads — you need to break the file
into bounded pieces and reassemble them later. There are general-purpose
archivers for that, but they encode metadata and directory structures you may
not want. This library does one thing: raw byte splits with a predictable
naming scheme (``{prefix}.{000, 001, ...}``) so reassembly is a plain
concatenation.

The trade-off is that parts carry no checksums or manifest — verifying
integrity and discovering the correct reassembly order is the caller's job.
That keeps the implementation tiny and dependency-free.

## Edge cases

An empty input file produces a single empty (zero-byte) output part rather than
zero parts. This keeps the operation total: every input maps to at least one
output file, and reassembly by concatenating all parts in index order always
reproduces the original, including the empty case.

`chunk_bytes` must be a positive `int`; `bool` is rejected even though it is a
subclass of `int` in Python, because it is not a meaningful size. Passing a
string like `"4"` or a float like `4.0` raises `TypeError`.

If you pass a file object (anything with a `.read` method) rather than a path,
the library reads from it but does not close it — the stream's lifetime stays
yours to manage.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
