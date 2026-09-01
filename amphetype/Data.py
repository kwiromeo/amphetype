"""SQLite layer: `Statistic` accumulator, custom SQL aggregates
(`agg_median`, `agg_mean`, `agg_first`), and helper functions
(`counter`, `regex_match`, `abbreviate`, `time_group`, `ifelse`).

The connection holds mutable state on `self` (`_count`, `lasttime_`,
`time_count_`, `regex_`) for the `counter`/`time_group`/`regex_match`
SQL functions. It is single-threaded (Qt main loop) and process-global
(imported as `DB`).

Invariant: `DB` is `None` until `init_db()` runs; the app flow
guarantees this via `bootstrap()`.
"""
import bisect
import sqlite3
import re

def trimmed_average(total, series):
  s = 0.0
  n = 0

  start = 0
  cutoff = total // 3
  while cutoff > 0:
    cutoff -= series[start][1]
    start += 1
  if cutoff < 0:
    s += -cutoff * series[start - 1][0]
    n += -cutoff

  end = len(series) - 1
  cutoff = total // 3
  while cutoff > 0:
    cutoff -= series[end][1]
    end -= 1
  if cutoff < 0:
    s += -cutoff * series[end + 1][0]
    n += -cutoff

  while start <= end:
    s += series[start][1] * series[start][0]
    n += series[start][1]
    start += 1

  return s / n


class Statistic(list):
  def __init__(self):
    super(Statistic, self).__init__()
    self.flawed_ = 0

  def append(self, x, flawed=False):
    bisect.insort(self, x)
    if flawed:
      self.flawed_ += 1


  def measurement(self):
    return trimmed_average(len(self), [(x, 1) for x in self])

  def median(self):
    input_length = len(self)
    if input_length == 0:
      return None
    if input_length & 1:
      return self[input_length // 2]
    return (self[input_length // 2] + self[input_length // 2 - 1]) / 2.0

  def flawed(self):
    return self.flawed_


class MedianAggregate(Statistic):
  def step(self, value: float | None) -> None:
    if value is not None:
      self.append(value)

  def finalize(self) -> float | None:
    return self.median()


class MeanAggregate(object):
  def __init__(self) -> None:
    self.sum_ = 0.0
    self.count_ = 0

  def step(self, value: float | None, count: int | None) -> None:
    if value is not None and count is not None:
      self.sum_ += value * count
      self.count_ += count

  def finalize(self) -> float | None:
    return self.sum_ / self.count_ if self.count_ > 0 else None

class FirstAggregate(object):
  def __init__(self) -> None:
    self.val = None

  def step(self, val: object) -> None:
    if self.val is None:
      self.val = val

  def finalize(self) -> object:
    return self.val


class AmphDatabase(sqlite3.Connection):
  def __init__(self, *args, **kwargs):
    super(AmphDatabase, self).__init__(*args, **kwargs)

    self.setRegex("")
    self.resetCounter()
    self.resetTimeGroup()
    self.create_function("counter", 0, self.counter)
    self.create_function("regex_match", 1, self.match)
    self.create_function("abbreviate", 2, self.abbreviate)
    self.create_function("time_group", 2, self.time_group)
    self.create_aggregate("agg_median", 1, MedianAggregate)
    self.create_aggregate("agg_mean", 2, MeanAggregate)
    self.create_aggregate("agg_first", 1, FirstAggregate)
    self.create_function("ifelse", 3, lambda x, y, z: y if x is not None else z)

    try:
      self.fetchall("select * from result,source,statistic,text,mistake limit 1")
    except Exception:
      self.newDB()

  def executemany_(self, sql, seq):
    return self.executemany(sql, seq)


  def resetTimeGroup(self):
    self.lasttime_ = 0.0
    self.time_count_ = 0

  def time_group(self, d, x):
    if abs(x - self.lasttime_) >= d:
      self.time_count_ += 1
    self.lasttime_ = x
    return self.time_count_

  def setRegex(self, x):
    self.regex_ = re.compile(x)

  def abbreviate(self, x, n):
    return x if len(x) <= n else x[: n - 3] + "..."

  def match(self, x):
    if self.regex_.search(x):
      return 1
    return 0

  def counter(self):
    self._count += 1
    return self._count

  def resetCounter(self):
    self._count = -1

  def newDB(self):
    self.executescript("""
create table source (name text, disabled integer, discount integer);
create table text (id text primary key, source integer, text text, disabled integer);
create table result (w real, text_id text, source integer, wpm real, accuracy real, viscosity real);
create table statistic (w real, data text, type integer, time real, count integer, mistakes integer, viscosity real);
create table mistake (w real, target text, mistake text, count integer);
create view text_source as
  select id,s.name,text,coalesce(t.disabled,s.disabled)
    from text as t left join source as s on (t.source = s.rowid);
    """)
    self.commit()


  def fetchall(self, *args):
    return self.execute(*args).fetchall()

  def fetchone(self, sql, default, *args):
    x = self.execute(sql, *args)
    g = x.fetchone()
    if g is None:
      return default
    return g

  def getSource(self, source, lesson=None):
    v = self.fetchall("select rowid from source where name = ? limit 1", (source,))
    if len(v) > 0:
      self.execute("update source set disabled = NULL where rowid = ?", v[0])
      self.commit()
      return v[0][0]
    self.execute("insert into source (name,discount) values (?,?)", (source, lesson))
    return self.getSource(source)

  def getTextContext(self, text_id):
    texts = sorted(
      DB.fetchall(
        """
select T.rowid,T.id,T.source,T.text
  from text as T, (select rowid,source from text where id=?) as T2
  where T.disabled is null and
    T.source = T2.source
  order by abs(T.rowid - T2.rowid) asc
  limit 3""",
        (text_id,),
      )
    )
    if text_id not in [t[1] for t in texts]:
      return (None, None, None)
    if len(texts) == 1:
      return (None, texts[0][1:], None)

    if texts[0][1] == text_id:
      return (None, texts[0][1:], texts[1][1:])
    if texts[-1][1] == text_id:
      return (texts[-2][1:], texts[-1][1:], None)

    assert len(texts) == 3 and texts[1][1] == text_id
    return (texts[0][1:], texts[1][1:], texts[2][1:])


# GLOBAL — None until init_db() is called. bootstrap() calls init_db()
# before any widget module is imported, so `from amphetype.Data import DB`
# in widget modules binds the live connection.
DB = None


def init_db(dbname):
  global DB
  DB = sqlite3.connect(dbname, 5, 0, "DEFERRED", False, AmphDatabase)
  return DB
