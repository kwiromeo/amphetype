import time

import lesson_builder
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from amphetype.Config import Settings, SettingsCombo, SettingsEdit
from amphetype.Data import DB
from amphetype.QtUtil import AmphBoxLayout, AmphButton, AmphModel, AmphTree

# from amphetype.Text import LessonGeneratorPlain


class WordModel(AmphModel):
  def signature(self):
    self.words = []
    return (
      ["Item", "Speed", "Accuracy", "Viscosity", "Count", "Mistakes", "Impact"],
      [None, "%.1f wpm", "%.1f%%", "%.1f", None, None, "%.1f"],
    )

  def populateData(self, idx):
    if len(idx) != 0:
      return []

    return self.words

  def setData(self, words):
    self.words = list(map(list, words))
    self.reset()


class StringStats(QWidget):
  lessonStrings = pyqtSignal("PyQt_PyObject")

  def __init__(self, *args):
    super(StringStats, self).__init__(*args)

    self.model = WordModel()
    tw = AmphTree(self.model)
    tw.setIndentation(0)
    tw.setUniformRowHeights(True)
    tw.setRootIsDecorated(False)
    tw.setAlternatingRowColors(True)
    self.stats = tw

    self._item_kind_options = ["keys", "trigrams", "words"]
    self._statistic_options = [
      ("wpm asc", "slowest"),
      ("wpm desc", "fastest"),
      ("viscosity desc", "least fluid"),
      ("viscosity asc", "most fluid"),
      ("accuracy asc", "least accurate"),
      ("misses desc", "most mistyped"),
      ("total desc", "most common"),
      ("damage desc", "most damaging"),
    ]

    ob = SettingsCombo("ana_which", self._statistic_options)

    wc = SettingsCombo("ana_what", self._item_kind_options)
    lim = SettingsEdit("ana_many")
    self.w_count = SettingsEdit("ana_count")

    Settings.signal_for("ana_which").connect(self.update)
    Settings.signal_for("ana_what").connect(self.update)
    Settings.signal_for("ana_many").connect(self.update)
    Settings.signal_for("ana_count").connect(self.update)
    Settings.signal_for("history").connect(self.update)

    # extract statistics selections from global settings object
    selected_statistic = Settings.get("ana_which")
    selected_item_kind = self._item_kind_options[Settings.get("ana_what")]

    self.setLayout(
      AmphBoxLayout(
        [
          ["Display statistics about the", ob, wc, None, AmphButton("Update List", self.update)],
          [
            "Limit list to",
            lim,
            "items and don't show items with a count less than",
            self.w_count,
            None,
            AmphButton(
              "Send List to Lesson Generator", lambda: self.lessonStrings.emit([x[0] for x in self.model.words])
            ),
            AmphButton(
              "Smart Lesson From List Items",
              lambda: self.lessonStrings.emit(
                lesson_builder.create_lesson(
                  issues_list=self.model.words, item_kind=selected_item_kind, statistic_type=selected_statistic
                )
              ),
            ),
          ],
          (self.stats, 1),
        ]
      )
    )

  def update(self, *arg):
    ord = Settings.get("ana_which")
    cat = Settings.get("ana_what")
    limit = Settings.get("ana_many")
    count = Settings.get("ana_count")
    hist = time.time() - Settings.get("history") * 86400.0

    sql = """select data,12.0/time as wpm,
      100.0-100.0*misses/cast(total as real) as accuracy,
      viscosity,total,misses,
      total*time*time*(1.0+misses/total) as damage
        from
          (select data,agg_median(time) as time,agg_median(viscosity) as viscosity,
          sum(count) as total,sum(mistakes) as misses
          from statistic where w >= ? and type = ? group by data)
        where total >= ?
        order by %s limit %d""" % (ord, limit)

    self.model.setData(DB.fetchall(sql, (hist, cat, count)))
