"""
Smoke tests for the startup replay feature.

Tests the _last_incomplete_text query logic directly against a temporary
SQLite database with the same schema as the real DB.
"""
import sqlite3
import sys
import os
import unittest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# We need QApplication for Settings, but we can test the query logic
# by creating a temp DB with the same schema and running the query.
# For the Settings-dependent threshold comparison, we import Settings
# after QApplication is created.

from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)


from amphetype.Config import Settings

# Set known thresholds so tests are deterministic regardless of user settings
_saved_min_wpm = Settings.get("min_wpm")
_saved_min_acc = Settings.get("min_acc")
_saved_min_lesson_wpm = Settings.get("min_lesson_wpm")
_saved_min_lesson_acc = Settings.get("min_lesson_acc")
Settings.set("min_wpm", 50.0)
Settings.set("min_acc", 97.0)
Settings.set("min_lesson_wpm", 50.0)
Settings.set("min_lesson_acc", 97.0)


def make_db():
    """Create a temporary in-memory DB with the amphetype schema."""
    db = sqlite3.connect(":memory:")
    db.executescript("""
        create table source (name text, disabled integer, discount integer);
        create table text (id text primary key, source integer, text text, disabled integer);
        create table result (w real, text_id text, source integer, wpm real, accuracy real, viscosity real);
        create table statistic (w real, data text, type integer, time real, count integer, mistakes integer, viscosity real);
        create table mistake (w real, target text, mistake text, count integer);
    """)
    return db


def last_incomplete_text(db):
    """Replicate TextManager._last_incomplete_text query logic."""
    row = db.execute("""
        select t.id, t.source, t.text, r.wpm, r.accuracy, s.discount
        from result r
        join text t on t.id = r.text_id
        join source s on s.rowid = r.source
        where t.disabled is null and s.disabled is null
        order by r.w desc limit 1
    """).fetchone()
    if row is None:
        return None
    text_id, source, text, wpm, accuracy, discount = row
    if discount:
        min_wpm = Settings.get("min_lesson_wpm")
        min_acc = Settings.get("min_lesson_acc")
    else:
        min_wpm = Settings.get("min_wpm")
        min_acc = Settings.get("min_acc")
    if wpm < min_wpm or accuracy < min_acc / 100.0:
        return (text_id, source, text)
    return None


class TestLastIncompleteText(unittest.TestCase):
    """Regression tests for TextManager._last_incomplete_text."""

    def test_below_threshold_returns_text(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
        db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 50.0, 0.5)")
        result = last_incomplete_text(db)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 't1')

    def test_above_threshold_returns_none(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
        db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 50.0, 0.99)")
        result = last_incomplete_text(db)
        self.assertIsNone(result)

    def test_deleted_text_returns_none(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
        db.execute("insert into text (id, source, text, disabled) values ('t1', 1, 'hello world', 1)")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 10.0, 0.5)")
        result = last_incomplete_text(db)
        self.assertIsNone(result)

    def test_disabled_source_returns_none(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount, disabled) values (1, 'test_lesson', 1, 1)")
        db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 10.0, 0.5)")
        result = last_incomplete_text(db)
        self.assertIsNone(result)

    def test_no_results_returns_none(self):
        db = make_db()
        result = last_incomplete_text(db)
        self.assertIsNone(result)

    def test_non_lesson_above_threshold_returns_none(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount) values (1, 'test_plain', 0)")
        db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 60.0, 0.98)")
        result = last_incomplete_text(db)
        self.assertIsNone(result)

    def test_non_lesson_below_threshold_returns_text(self):
        db = make_db()
        db.execute("insert into source (rowid, name, discount) values (1, 'test_plain', 0)")
        db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
        db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 30.0, 0.5)")
        result = last_incomplete_text(db)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 't1')


if __name__ == "__main__":
    unittest.main()
