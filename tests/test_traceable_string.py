import pytest

from flachtex import TraceableString


def test_get_origin():
    ts = TraceableString("content", "origin", 0)
    assert ts.get_origin(2) == ("origin", 2)


def test_add():
    ts1 = TraceableString("left", "A", 0)
    ts2 = TraceableString("right", "B", 0)
    ts = ts1 + ts2
    assert str(ts) == "leftright"


def test_json():
    ts1 = TraceableString("left", "A", 0)
    ts2 = TraceableString("right", "B", 0)
    ts = ts1 + ts2
    ts_ = TraceableString.from_json(ts.to_json())
    assert ts == ts_


def test_invalid_json():
    ts1 = TraceableString("left", "A", 0)
    ts2 = TraceableString("right", "B", 0)
    ts = ts1 + ts2
    data = ts.to_json()
    data["origins"].append([])  # Introduce invalid data
    with pytest.raises(ValueError, match="Data not compatible: list indices must be integers or slices, not str"):
        TraceableString.from_json(data)
