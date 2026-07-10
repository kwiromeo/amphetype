"""Unit tests for amphetype/Data.py SQL aggregates.

Run via `pytest tests/test_data_aggregates.py` or
`python -m unittest tests.test_data_aggregates`.
"""
import sqlite3
import unittest

from amphetype.Data import AmphDatabase


class TestMedianAggregate(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", factory=AmphDatabase)

    def tearDown(self):
        self.db.close()

    def test_empty_returns_none(self):
        got = self.db.execute(
            "select agg_median(viscosity) from statistic"
        ).fetchone()[0]
        self.assertIsNone(got)

    def test_single_row_returns_value(self):
        self.db.execute("insert into statistic (viscosity) values (1.5)")
        got = self.db.execute(
            "select agg_median(viscosity) from statistic"
        ).fetchone()[0]
        self.assertEqual(got, 1.5)

    def test_odd_count_picks_middle(self):
        for v in (1.0, 2.0, 3.0, 4.0, 5.0):
            self.db.execute("insert into statistic (viscosity) values (?)", (v,))
        got = self.db.execute(
            "select agg_median(viscosity) from statistic"
        ).fetchone()[0]
        self.assertEqual(got, 3.0)

    def test_even_count_averages_middle_pair(self):
        for v in (1.0, 2.0, 3.0, 4.0):
            self.db.execute("insert into statistic (viscosity) values (?)", (v,))
        got = self.db.execute(
            "select agg_median(viscosity) from statistic"
        ).fetchone()[0]
        self.assertEqual(got, 2.5)

    def test_nulls_are_skipped(self):
        for v in (1.0, None, 3.0):
            self.db.execute("insert into statistic (viscosity) values (?)", (v,))
        got = self.db.execute(
            "select agg_median(viscosity) from statistic"
        ).fetchone()[0]
        self.assertEqual(got, 2.0)


class TestMeanAggregate(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", factory=AmphDatabase)

    def tearDown(self):
        self.db.close()

    def test_empty_returns_none(self):
        got = self.db.execute(
            "select agg_mean(time, count) from statistic"
        ).fetchone()[0]
        self.assertIsNone(got)

    def test_weighted_average(self):
        self.db.executemany(
            "insert into statistic (time, count) values (?, ?)",
            [(0.5, 2), (0.7, 4), (0.3, 4)],
        )
        got = self.db.execute(
            "select agg_mean(time, count) from statistic"
        ).fetchone()[0]
        # weighted mean = (0.5*2 + 0.7*4 + 0.3*4) / 10 = 0.50
        self.assertAlmostEqual(got, 0.50, places=4)


class TestFirstAggregate(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", factory=AmphDatabase)

    def tearDown(self):
        self.db.close()

    def test_empty_returns_none(self):
        got = self.db.execute(
            "select agg_first(text_id) from result"
        ).fetchone()[0]
        self.assertIsNone(got)

    def test_returns_first_non_null(self):
        self.db.executemany(
            "insert into result (w, text_id) values (?, ?)",
            [(1.0, "alpha"), (2.0, "beta")],
        )
        got = self.db.execute(
            "select agg_first(text_id) from result"
        ).fetchone()[0]
        self.assertEqual(got, "alpha")


class TestAbbreviate(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", factory=AmphDatabase)

    def tearDown(self):
        self.db.close()

    def test_short_string_unchanged(self):
        got = self.db.execute("select abbreviate('hello', 10)").fetchone()[0]
        self.assertEqual(got, "hello")

    def test_long_string_truncated_with_ellipsis(self):
        got = self.db.execute("select abbreviate('hello world', 8)").fetchone()[0]
        self.assertEqual(got, "hello...")

    def test_exact_length_unchanged(self):
        got = self.db.execute("select abbreviate('abcdefgh', 8)").fetchone()[0]
        self.assertEqual(got, "abcdefgh")


if __name__ == "__main__":
    unittest.main()
