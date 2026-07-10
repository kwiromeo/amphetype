"""
Smoke tests for the startup replay feature.

Tests the _last_incomplete_text query logic directly against a temporary
SQLite database with the same schema as the real DB.
"""
import sqlite3
import sys
import os

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


# --- Test 1: Below threshold returns the text ---
print("=== Test 1: Below threshold returns the text ===")
db = make_db()
db.execute("insert into source (rowid, name, discount) values (1, 'test_source', 0)")
db.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
# Insert a result with WPM=10, accuracy=0.5 (below default min_wpm=0? No, min_wpm=0.0 default)
# Default min_wpm is 0.0, so 10 WPM is NOT below 0.0. Let's use min_lesson thresholds.
# Actually, let's set discount=1 (lesson) so it uses min_lesson_wpm=0.0, min_lesson_acc=97.0
db.execute("delete from source")
db.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
db.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 50.0, 0.5)")
result = last_incomplete_text(db)
# min_lesson_wpm=0.0, so 50.0 >= 0.0 is fine. But accuracy=0.5 < 97.0/100 = 0.97, so it should return the text
assert result is not None, "Expected text tuple for below-accuracy result"
assert result[0] == 't1', f"Expected text_id 't1', got {result[0]}"
print(f"  PASS: got {result}")

# --- Test 2: Above threshold returns None ---
print("=== Test 2: Above threshold returns None ===")
db2 = make_db()
db2.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
db2.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
db2.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 50.0, 0.99)")
result = last_incomplete_text(db2)
# accuracy=0.99 >= 0.97, wpm=50.0 >= 0.0 → None
assert result is None, f"Expected None for above-threshold result, got {result}"
print("  PASS: got None")

# --- Test 3: Deleted text returns None ---
print("=== Test 3: Deleted text returns None ===")
db3 = make_db()
db3.execute("insert into source (rowid, name, discount) values (1, 'test_lesson', 1)")
db3.execute("insert into text (id, source, text, disabled) values ('t1', 1, 'hello world', 1)")
db3.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 10.0, 0.5)")
result = last_incomplete_text(db3)
# text is disabled → join with t.disabled is null excludes it → None
assert result is None, f"Expected None for disabled text, got {result}"
print("  PASS: got None")

# --- Test 4: Disabled source returns None ---
print("=== Test 4: Disabled source returns None ===")
db4 = make_db()
db4.execute("insert into source (rowid, name, discount, disabled) values (1, 'test_lesson', 1, 1)")
db4.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
db4.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 10.0, 0.5)")
result = last_incomplete_text(db4)
# source is disabled → join with s.disabled is null excludes it → None
assert result is None, f"Expected None for disabled source, got {result}"
print("  PASS: got None")

# --- Test 5: No results returns None ---
print("=== Test 5: No results returns None ===")
db5 = make_db()
result = last_incomplete_text(db5)
assert result is None, f"Expected None for empty DB, got {result}"
print("  PASS: got None")

# --- Test 6: Non-lesson (discount=0) uses min_wpm/min_acc ---
print("=== Test 6: Non-lesson uses min_wpm/min_acc ===")
db6 = make_db()
db6.execute("insert into source (rowid, name, discount) values (1, 'test_plain', 0)")
db6.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
db6.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 60.0, 0.98)")
result = last_incomplete_text(db6)
# wpm=60.0 >= 50.0, accuracy=0.98 >= 0.97 → None (above threshold)
assert result is None, f"Expected None for above-threshold plain text, got {result}"
print("  PASS: got None")

# --- Test 7: Below threshold for plain text returns text ---
print("=== Test 7: Below threshold for plain text returns text ===")
db7 = make_db()
db7.execute("insert into source (rowid, name, discount) values (1, 'test_plain', 0)")
db7.execute("insert into text (id, source, text) values ('t1', 1, 'hello world')")
db7.execute("insert into result (w, text_id, source, wpm, accuracy) values (1000, 't1', 1, 30.0, 0.5)")
result = last_incomplete_text(db7)
# wpm=30.0 < 50.0 → below threshold, returns text
assert result is not None, "Expected text tuple for below-threshold plain text"
assert result[0] == 't1', f"Expected text_id 't1', got {result[0]}"
print(f"  PASS: got {result}")
print("  PASS: got None")

print()
print("All smoke tests passed!")
