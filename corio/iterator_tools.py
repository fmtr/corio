from itertools import chain, batched
from typing import List, Dict, Any, TypeVar, Generic, Iterable

from corio.datatype_tools import is_none


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


IterDifferT = TypeVar("IterDifferT")


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
