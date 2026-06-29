import datetime
from datetime import timedelta
from itertools import chain, batched
from time import monotonic
from typing import List, Dict, Any, TypeVar, Generic, Iterable, Mapping, Sequence, Iterator as TypingIterator

from corio import dt, Constants
from corio.datatype import is_none
from corio.inherit import Inherit
from corio.logs import logger
from corio.strings import join, suffix_plural


def enlist(value) -> List[Any]:
    """

    Make a non-list into a singleton list

    """
    enlisted = value if isinstance(value, list) else [value]
    return enlisted


def dict_records_to_lists(data: List[Dict[Any, Any]], missing: Any = None) -> Dict[Any, List[Any]]:
    """

    Convert a list of dictionaries to lists format

    """
    keys = set(chain.from_iterable([datum.keys() for datum in data]))
    as_lists = {key: [] for key in keys}
    for datum in data:
        for key in keys:
            as_lists[key].append(datum.get(key, missing))
    return as_lists


def get_batch_sizes(total, num_batches):
    """

    Calculate the sizes of batches for a given total number of items and number of batches.

    """
    return [total // num_batches + (1 if x < total % num_batches else 0) for x in range(num_batches)]


def chunk_data(data, size: int):
    """

    Chunk data into batches of a given size, plus any remainder

    """
    chunked = [data[offset:offset + size] for offset in range(0, len(data), size)]
    return chunked


def rebatch(batches, size: int):
    """

    Rebatch arbitrary-sized input batches into fixed-size output batches.

    """
    return batched(chain.from_iterable(batches), size)


def strip_none(*items):
    """

    Remove nones from a list of arguments

    """
    return [item for item in items if not is_none(item)]


def dedupe(items):
    """

    Deduplicate a list of items, retaining order

    """
    return list(dict.fromkeys(items))


def get_class_lookup(*classes, name_function=lambda cls: cls.__name__):
    """

    Dictionary of class names to classes

    """
    return {name_function(cls): cls for cls in classes}


def flatten_tree(data, node=None, flat=None, sep=None):
    """

    Flatten a nested dictionary or list into a single level dictionary, with Paths as keys

    """

    if sep is not None:
        data = flatten_tree(data)
        data = {
            sep.join(path.parts): value
            for path, value in data.items()
        }
        return data

    from corio import Path

    node = node or Path()
    if flat is None:
        flat = {}

    if isinstance(data, Mapping):
        for k, v in data.items():
            flatten_tree(v, node=node / str(k), flat=flat)
        return flat

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        for i, v in enumerate(data):
            flatten_tree(v, node=node / f'[{i}]', flat=flat)
        return flat

    flat[node] = data
    return flat


IndexListT = TypeVar('IndexListT')  # Generic type for list items


class IndexList(list[IndexListT], Generic[IndexListT]):
    """

    List of objects selectable via attribute lookup, plus currently-selected item.

    """

    def __init__(self, iterable: Iterable[IndexListT] = ()):
        """

        Initialize with iterable

        """
        super().__init__(iterable)
        self.current: IndexListT | None = self[0] if self else None

    def __getattr__(self, name):
        """

        Return a lookup dict keyed on the specified field of each item in the self/list.

        """

        try:
            return self.__dict__[name]
        except KeyError:
            pass

        if hasattr(list, name):
            return getattr(self, name)

        result = {}
        for obj in self:
            try:
                value = getattr(obj, name)
            except AttributeError:
                value = obj[name]  # assume dict-like
            result[value] = obj
        return result

    @property
    def cls(self) -> dict[type, IndexListT]:
        return {obj.__class__: obj for obj in self}


IterDifferT = TypeVar("IterDifferT")
IteratorT = TypeVar("IteratorT")


class IterDiffer(Generic[IterDifferT]):
    """

    Compute added/removed differences between two iterables.

    """

    def __init__(self, before: Iterable[IterDifferT], after: Iterable[IterDifferT]):
        """

        Initialize with two iterables.

        """
        self.before: set[IterDifferT] = set(before)
        self.after: set[IterDifferT] = set(after)

    @property
    def added(self) -> set[IterDifferT]:
        """

        Items in `after` not in `before`.

        """
        return self.after - self.before

    @property
    def removed(self) -> set[IterDifferT]:
        """

        Items in `before` not in `after`.

        """
        return self.before - self.after

    @property
    def is_changed(self) -> bool:
        """

        True if any items added or removed.

        """
        return bool(self.added or self.removed)


class Iterator(Generic[IteratorT]):
    """

    Integrate an iterable with observability and progress/throughput stats.

    """

    def __init__(self, iterable: Iterable[IteratorT], *, total: int | None = None):
        """

        Initialize with iterable and optional explicit total.

        """
        self.iterable = iterable
        self.total = total if total is not None else self._get_total(iterable)
        self.count = 0
        self.started_at = None
        self.item: IteratorT | None = None
        self._span_context = None

    @classmethod
    def span(cls):
        """

        Return an iterator usable as a lightweight timing/logging context manager.

        """
        return cls([None], total=1)

    @staticmethod
    def _get_total(iterable: Iterable[IteratorT]) -> int | None:
        """

        Return len(iterable) when available, else None.

        """
        try:
            return len(iterable)
        except TypeError:
            return None

    @property
    def elapsed(self) -> timedelta:
        """

        Time elapsed since iteration started.

        """
        elapsed = dt.now() - self.started_at
        return elapsed

    @property
    def rate(self) -> float | None:
        """

        Current processed items per second.

        """
        elapsed = self.elapsed
        if elapsed.seconds <= 0:
            return None
        return self.count / elapsed.seconds

    @property
    def percentage(self) -> float | None:
        """

        Completion percentage when total is known.

        """
        if not self.total:
            return None
        return (self.count / self.total) * 100.0

    @property
    def eta(self) -> timedelta | None:
        """

        Estimated remaining time when total and rate are known.

        """
        if not self.total:
            return None
        if not self.rate:
            return None
        seconds = max((self.total - self.count) / self.rate, 0.0)
        delta = timedelta(seconds=round(seconds))
        return delta

    @property
    def item_desc(self) -> str:
        """

        Current item class name for logging text.

        """
        if self.item is None:
            return "item"
        return self.item.__class__.__name__

    @property
    def span_iteration(self):
        """

        Span context for overall iteration lifecycle.

        """
        return logger.span(f"Iterating count={self.total or 'unknown'} items...")

    @property
    def span_item(self):
        """

        Span context for per-item processing with stats.

        """
        texts = [self.percentage_text, self.rate_text, self.elapsed_text, self.eta_text, ]
        stats = join(texts, sep=" | ", )
        return logger.span(f"Processing {self.item_desc} {self.count}/{self.total or '?'}: {stats}")

    @property
    def is_over_count(self)-> bool:
        """

        True if count exceeds configured total.

        """
        if self.total is None:
            return False
        return self.count > self.total

    def log_completion(self) -> None:
        """

        Log successful completion summary for iteration.

        """
        logger.info(f"Completed {self.count} {self.item_desc}(s) in {self.elapsed} {self.avg_rate_text}")

    def log_over_total_warning(self) -> None:
        """

        Log a warning when processed count exceeds configured total.

        """
        logger.warning(f"Count exceeded total: {self.count}/{self.total}")

    def __iter__(self) -> TypingIterator[IteratorT]:
        """

        Yield items while updating stats and ensuring iterator cleanup.

        """
        self.count = 0
        self.started_at = dt.now()
        self.item = None
        iterator = iter(self.iterable)

        with self.span_iteration:
            try:
                for item in iterator:
                    self.count += 1
                    self.item = item
                    if self.is_over_count:
                        self.log_over_total_warning()
                    with self.span_item:
                        yield item
                self.log_completion()
            finally:
                close = getattr(iterator, "close", lambda: None)
                close()

    def __enter__(self):
        """

        Enter timing/logging context without consuming the wrapped iterable.

        """
        self.count = 1
        self.started_at = dt.now()
        self.item = None
        self._span_context = self.span_iteration
        self._span_context.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        """

        Exit timing/logging context and emit completion on success.

        """
        try:
            if exc_type is None:
                self.log_completion()
        finally:
            if self._span_context is not None:
                self._span_context.__exit__(exc_type, exc, traceback)
                self._span_context = None

    @property
    def count_text(self) -> str:
        """

        Formatted count text for span stats.

        """
        return f"count={self.count}"

    @property
    def percentage_text(self) -> str | None:
        """

        Formatted percentage text for span stats.

        """
        if self.percentage is None:
            return None
        return f"{self.percentage:.1f}%"

    @property
    def rate_text(self) -> str | None:
        """

        Formatted rate text for span stats.

        """
        rate=self.rate
        if rate is None:
            return None

        return f"{rate:.2f} {suffix_plural(count=rate,name=self.item_desc)}/s"

    @property
    def eta_text(self) -> str | None:
        """

        Formatted ETA text for span stats.

        """
        if self.eta is None:
            return None
        eta_dt = dt.now() + self.eta
        return f"eta={self.eta} wall={eta_dt.strftime(Constants.DATETIME_FILENAME_FORMAT)}"

    @property
    def elapsed_text(self) -> str | None:
        """

        Formatted elapsed-time text for span stats.

        """
        return f"elapsed={self.elapsed}"

    @property
    def avg_rate_text(self) -> str | None:
        """

        Formatted average rate text for completion logs.

        """
        if self.rate is None:
            return None
        return f"avg={self.rate:.2f} {self.item_desc}(s)/s"
