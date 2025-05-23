import locale
import time

from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QWidget

from amphetype.Config import Settings, SettingsEdit
from amphetype.Data import DB
from amphetype.QtUtil import AmphBoxLayout, AmphButton

locale.setlocale(locale.LC_ALL, "")


class IncrementalProgress(QProgressBar):
  def __init__(self, maxi, *args):
    QProgressBar.__init__(self, *args)

    self.setRange(0, maxi)
    self.setValue(0)
    self.hide()

  def show(self):
    self.setValue(0)
    QProgressBar.show(self)

  def inc(self, val=1):
    self.setValue(self.value() + val)


class DatabaseWidget(QWidget):
  def __init__(self, *args):
    super(DatabaseWidget, self).__init__(*args)

    Settings.signal_for("db_name").connect(self.dbchange)

    self.stats_ = QLabel("\nPress Update to fetch database statistics\n")
    self.progress_ = IncrementalProgress(6 + 2)

    self.setLayout(
      AmphBoxLayout(
        [
          [
            "The database is essentially your 'profile'. It stores all your statistics, the texts you've imported, the lessons you've generated and so forth.",
            None,
          ],
          [
            AmphButton("Update", self.update),
            150,
            (
              [
                ["Current database:", SettingsEdit("db_name")],
                [
                  "For the database change to take effect you need to restart Amphetype. You can also specify a database name at the command line with the '--database=&lt;file&gt;' switch.\n"
                ],
              ],
              1,
            ),
          ],  # AmphButton("Import", self.importdb), "external DB file"]]],
          self.stats_,
          None,
          [
            "DELETE all statistics and results from:",
            AmphButton("Last Minute", lambda: self.delete_last(60.0)),
            AmphButton("Last Hour", lambda: self.delete_last(60.0 * 60.0)),
            AmphButton("Last 24 Hours", lambda: self.delete_last(60.0 * 60.0 * 24.0)),
            None,
          ],
          None,
          "After heavy use for several months the database can grow quite large since "
          + "lots of data are generated after every result and it's all stored indefinitely. "
          + "Here you can group old statistics into larger batches. This will speed up "
          + "data retrieval for statistics. It is recommended you do it once a month or so if you use the program regularly.\n",
          [
            "Group data older than",
            SettingsEdit("group_month"),
            "days into months, data older than",
            SettingsEdit("group_week"),
            "days into weeks, and data older than",
            SettingsEdit("group_day"),
            "days into days.",
            None,
          ],
          [AmphButton("Go!", self.cleanup), None],
          [self.progress_],
          None,
        ]
      )
    )

  def importdb(self):
    pass

  def delete_last(self, delta):
    threshold = time.time() - delta

    ds = DB.execute("""delete from statistic where w > ?""", (threshold,)).rowcount
    dm = DB.execute("""delete from mistake where w > ?""", (threshold,)).rowcount
    dr = DB.execute("""delete from result where w > ?""", (threshold,)).rowcount

    self.stats_.setText(f"Deleted {ds} statistic entries, {dm} mistake entries, {dr} results")

  def update(self):
    self.progress_.show()
    n_text = DB.fetchone("""select count(*) from text""", (0,))[0]
    self.progress_.inc(2)
    n_res = DB.fetchone("""select count(*) from result""", (0,))[0]
    self.progress_.inc(2)
    n_words = DB.fetchall("""select count(*),sum(count) from statistic
      group by type order by type""")
    self.progress_.inc(2)
    if len(n_words) != 3:
      n_words = [(0, 0), (0, 0), (0, 0)]
    n_first = DB.fetchone("""select w from result order by w asc limit 1""", (time.time(),))[0]
    self.progress_.hide()

    self.stats_.setText(
      locale.format_string(
        """Texts: %d
Results: %d
Analysis data: %d (%d keys, %d trigrams, %d words)
  %d characters and %d words typed total\n"""
        + ("First result was %.2f days ago.\n" % ((time.time() - n_first) / 86400.0)),
        tuple([n_text, n_res, sum([x[0] for x in n_words])] + [x[0] for x in n_words] + [n_words[0][1], n_words[2][1]]),
        True,
      )
    )

  def dbchange(self, nn):
    # DB.switchdb(nn)
    pass

  def cleanup(self):
    day = 24 * 60 * 60
    now = time.time()
    q = []

    self.progress_.show()
    for grp, lim in [
      (30.0, Settings.get("group_month")),
      (7.0, Settings.get("group_week")),
      (1.0, Settings.get("group_day")),
    ]:
      w = now - day * lim
      g = grp * day
      q.extend(
        DB.fetchall(
          """
        select avg(w),data,type,agg_mean(time,count),sum(count),sum(mistakes),agg_median(viscosity)
        from statistic where w <= %f
        group by data,type,cast(w/%f as int)"""
          % (w, g)
        )
      )
      self.progress_.inc()

      DB.execute("""delete from statistic where w <= ?""", (w,))
      self.progress_.inc()

    DB.executemany(
      """insert into statistic (w,data,type,time,count,mistakes,viscosity)
      VALUES (?,?,?,?,?,?,?)""",
      q,
    )
    self.progress_.inc()
    DB.commit()
    DB.execute("vacuum")
    self.progress_.inc()
    self.progress_.hide()


if __name__ == "__main__":
  app = QApplication([])
  dw = DatabaseWidget()
  dw.show()
  app.exec_()
