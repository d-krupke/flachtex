import unittest

from flachtex import TraceableString


class TraceableStringTest(unittest.TestCase):
    def test_1(self):
        ts = TraceableString("content", "origin", 0)
        self.assertEqual(ts.get_origin(2), ("origin", 2))

    def test_add(self):
        ts1 = TraceableString("left", "A", 0)
        ts2 = TraceableString("right", "B", 0)
        ts = ts1 + ts2
        self.assertEqual(str(ts), "leftright")

    def test_json(self):
        ts1 = TraceableString("left", "A", 0)
        ts2 = TraceableString("right", "B", 0)
        ts = ts1 + ts2
        ts_ = TraceableString.from_json(ts.to_json())
        self.assertEqual(ts, ts_)

    def test_json2(self):
        ts1 = TraceableString("left", "A", 0)
        ts2 = TraceableString("right", "B", 0)
        ts = ts1 + ts2
        data = ts.to_json()
        data["origins"].append([])
        self.assertRaises(ValueError, lambda: TraceableString.from_json(data))
