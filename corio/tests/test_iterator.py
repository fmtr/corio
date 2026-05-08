from dataclasses import dataclass

from corio import iterator


def test_enlist_and_dedupe():
    assert iterator.enlist("x") == ["x"]
    assert iterator.enlist(["x"]) == ["x"]
    assert iterator.dedupe(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_dict_records_to_lists_and_chunking():
    data = [{"a": 1}, {"b": 2}]
    as_lists = iterator.dict_records_to_lists(data, missing=None)
    assert as_lists == {"a": [1, None], "b": [None, 2]}

    assert iterator.chunk_data([1, 2, 3, 4, 5], size=2) == [[1, 2], [3, 4], [5]]
    assert iterator.get_batch_sizes(total=10, num_batches=3) == [4, 3, 3]
    assert list(iterator.rebatch([[1, 2], [3], [4, 5]], size=2)) == [(1, 2), (3, 4), (5,)]


def test_strip_none_flatten_tree_and_iterdiffer():
    assert iterator.strip_none(1, None, 2) == [1, 2]

    tree = {"a": {"b": 1}, "list": [2, 3]}
    flat = iterator.flatten_tree(tree, sep=".")
    assert flat["a.b"] == 1
    assert flat["list.[0]"] == 2
    assert flat["list.[1]"] == 3

    diff = iterator.IterDiffer(before=[1, 2], after=[2, 3])
    assert diff.added == {3}
    assert diff.removed == {1}
    assert diff.is_changed is True


@dataclass
class _Obj:
    key: str
    value: int


def test_index_list_lookup_by_attr_and_key():
    objects = iterator.IndexList([_Obj(key="a", value=1), _Obj(key="b", value=2)])
    assert objects.key["a"].value == 1

    dicts = iterator.IndexList([{"id": "x", "value": 1}, {"id": "y", "value": 2}])
    assert dicts.id["y"]["value"] == 2
