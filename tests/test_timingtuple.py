"""Regression tests for amphetype.timingtuple.

Covers the median bug fix (n=2 even case), pop_char guard, and core
RunStats/CharEntry contracts.
"""

from amphetype.timingtuple import CharEntry, RunStats, median


def test_median_empty():
    assert median([]) is None


def test_median_single():
    assert median([42.0]) == 42.0


def test_median_odd():
    assert median([1.0, 3.0, 2.0]) == 2.0


def test_median_even():
    assert median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_even_count_size_two():
    """Regression: n=2 would raise IndexError with the old code."""
    assert median([1.0, 2.0]) == 1.5


def test_make_and_attributes():
    r = RunStats.make("abc")
    assert len(r) == 3
    assert r.text == "abc"
    assert r.started is None
    assert r.index == 0
    for c in r:
        assert isinstance(c, CharEntry)
        assert c.char in "abc"


def test_char_entry_defaults():
    c = CharEntry("x")
    assert c.char == "x"
    assert c.inserts == 0
    assert c.timing is None
    assert c.mistakes == 0
    assert c.first is None
    assert c.first_any is None
    assert c.last is None
    assert c.errors == ""


def test_median_timing_none():
    r = RunStats.make("ab")
    assert r.median_timing is None


def test_median_timing_even():
    r = RunStats.make("ab")
    r[0].timing = 0.5
    r[1].timing = 1.5
    assert r.median_timing == 1.0


def test_median_timing_odd():
    r = RunStats.make("abc")
    r[0].timing = 0.5
    r[1].timing = 1.5
    r[2].timing = 2.5
    assert r.median_timing == 1.5


def test_none_timings_are_filtered():
    r = RunStats.make("abc")
    r[0].timing = 0.5
    r[1].timing = None
    r[2].timing = 2.5
    assert r.median_timing == 1.5


def test_faults():
    r = RunStats.make("abc")
    r[0].mistakes = 1
    assert r.faults == 1


def test_text():
    r = RunStats.make("hello")
    assert r.text == "hello"


def test_current():
    r = RunStats.make("abc")
    assert r.current is r[0]
    r.index = 1
    assert r.current is r[1]


def test_previous():
    r = RunStats.make("abc")
    assert r.previous is None
    r.index = 1
    assert r.previous is r[0]


def test_pop_char_past_end():
    """Regression: pop_char past end must not raise AttributeError."""
    r = RunStats.make("ab")
    r.index = 5
    assert r.pop_char() is None


def test_is_complete_fresh():
    r = RunStats.make("ab")
    assert not r.is_complete()
    r.index = 2
    assert not r.is_complete()


def test_result_returns_float_acc():
    r = RunStats.make("ab")
    wpm, vc, acc = r.result(accuracy=True)
    assert isinstance(acc, float)
    assert acc in (0.0, 1.0)
