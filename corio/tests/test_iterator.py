from dataclasses import dataclass
from contextlib import nullcontext

from corio import iterator


class _NoopLogger:
    @staticmethod
    def span(_message):
        return nullcontext()

    @staticmethod
    def info(_message):
        return None


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
    assert objects.cls[_Obj].value == 2

    dicts = iterator.IndexList([{"id": "x", "value": 1}, {"id": "y", "value": 2}])
    assert dicts.id["y"]["value"] == 2


def test_iterator_yields_datum_with_stats(monkeypatch):
    monkeypatch.setattr(iterator, "logger", _NoopLogger())
    wrapped = iterator.Iterator([10, 20])
    values = list(wrapped)

    assert values == [10, 20]
    assert wrapped.count == 2
    assert wrapped.total == 2
    assert wrapped.percentage == 100.0


def test_iterator_logs_spans_and_completion():
    events = []

    class DummyLogger:
        @staticmethod
        def span(message):
            events.append(("span", message))
            return nullcontext()

        @staticmethod
        def info(message):
            events.append(("info", message))

    class Doc:
        pass

    docs = [Doc(), Doc()]
    original_logger = iterator.logger
    iterator.logger = DummyLogger()
    try:
        wrapped = iterator.Iterator(docs)
        list(wrapped)
    finally:
        iterator.logger = original_logger

    span_events = [message for kind, message in events if kind == "span"]
    info_events = [message for kind, message in events if kind == "info"]

    assert span_events[0].startswith("Iterating")
    assert span_events[1].startswith("Processing Doc 1/2: count=1")
    assert span_events[2].startswith("Processing Doc 2/2: count=2")
    assert any(message.startswith("Completed 2 Doc(s)") for message in info_events)


def test_iterator_warns_when_count_exceeds_total():
    events = []

    class DummyLogger:
        @staticmethod
        def span(message):
            events.append(("span", message))
            return nullcontext()

        @staticmethod
        def info(message):
            events.append(("info", message))

        @staticmethod
        def warning(message):
            events.append(("warning", message))

    original_logger = iterator.logger
    iterator.logger = DummyLogger()
    try:
        wrapped = iterator.Iterator([1, 2, 3], total=2)
        values = list(wrapped)
    finally:
        iterator.logger = original_logger

    warning_events = [message for kind, message in events if kind == "warning"]

    assert values == [1, 2, 3]
    assert wrapped.count == 3
    assert warning_events == ["Count exceeded total: 3/2"]


def test_iterator_calls_close_on_underlying_iterator_on_completion(monkeypatch):
    monkeypatch.setattr(iterator, "logger", _NoopLogger())

    class ClosableIterator:
        def __init__(self):
            self.closed = False
            self.values = iter([1, 2, 3])

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.values)

        def close(self):
            self.closed = True

    closable = ClosableIterator()
    wrapped = iterator.Iterator(closable)

    assert list(wrapped) == [1, 2, 3]
    assert closable.closed is True


def test_iterator_calls_close_on_underlying_iterator_on_early_stop(monkeypatch):
    monkeypatch.setattr(iterator, "logger", _NoopLogger())

    class ClosableIterator:
        def __init__(self):
            self.closed = False
            self.values = iter([1, 2, 3])

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.values)

        def close(self):
            self.closed = True

    closable = ClosableIterator()
    wrapped = iterator.Iterator(closable)

    for value in wrapped:
        assert value == 1
        break

    assert wrapped.count == 1
    assert closable.closed is True


def test_iterator_uses_custom_total_when_len_unavailable(monkeypatch):
    monkeypatch.setattr(iterator, "logger", _NoopLogger())

    def gen():
        yield "a"
        yield "b"

    wrapped = iterator.Iterator(gen(), total=5)
    values = list(wrapped)

    assert values == ["a", "b"]
    assert wrapped.total == 5
    assert wrapped.count == 2


def test_iterator_unknown_total_when_len_unavailable_and_no_total(monkeypatch):
    monkeypatch.setattr(iterator, "logger", _NoopLogger())

    def gen():
        yield "a"
        yield "b"

    wrapped = iterator.Iterator(gen())
    values = list(wrapped)

    assert values == ["a", "b"]
    assert wrapped.total is None
    assert wrapped.count == 2
    assert wrapped.percentage is None
    assert wrapped.eta is None


def test_iterator_supports_context_manager():
    events = []

    class DummyLogger:
        @staticmethod
        def span(message):
            events.append(("span", message))
            return nullcontext()

        @staticmethod
        def info(message):
            events.append(("info", message))

    original_logger = iterator.logger
    iterator.logger = DummyLogger()
    try:
        with iterator.Iterator([1, 2, 3]):
            pass
    finally:
        iterator.logger = original_logger

    span_events = [message for kind, message in events if kind == "span"]
    info_events = [message for kind, message in events if kind == "info"]

    assert len(span_events) == 1
    assert span_events[0].startswith("Iterating")
    assert any(message.startswith("Completed 1 item(s)") for message in info_events)


def test_iterator_span_context_manager():
    events = []

    class DummyLogger:
        @staticmethod
        def span(message):
            events.append(("span", message))
            return nullcontext()

        @staticmethod
        def info(message):
            events.append(("info", message))

    original_logger = iterator.logger
    iterator.logger = DummyLogger()
    try:
        with iterator.Iterator.span():
            pass
    finally:
        iterator.logger = original_logger

    span_events = [message for kind, message in events if kind == "span"]
    info_events = [message for kind, message in events if kind == "info"]

    assert len(span_events) == 1
    assert span_events[0].startswith("Iterating")
    assert any(message.startswith("Completed 1 item(s)") for message in info_events)
