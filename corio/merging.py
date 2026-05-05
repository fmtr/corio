from deepmerge import always_merger
from functools import reduce


def merge(*data):
    """

    Merges multiple data dictionaries/objects recursively.

    """
    merged = reduce(always_merger.merge, data)
    return merged
