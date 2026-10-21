"""simple_file_split_by_size — split a binary file into size-capped chunks."""

from .core import Part, SplitResult, split_file_by_size

__all__ = ["Part", "SplitResult", "split_file_by_size"]
__version__ = "1.0.0"
