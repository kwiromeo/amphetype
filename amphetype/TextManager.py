import hashlib
import logging as log
import os.path as path
import time
import typing

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
  QLabel,
  QLayout,
  QBoxLayout,
  QHBoxLayout,
  QVBoxLayout,
  QFileDialog,
  QMessageBox,
  QProgressBar,
  QWidget,
  QFrame,
)

from amphetype.Config import Settings, SettingsCombo, SettingsEdit
from amphetype.Data import DB
from amphetype.QtUtil import (
  AmphBoxLayout,
  AmphButton,
  AmphGridLayout,
  AmphModel,
  AmphTree,
  WordWrapLabel,
)
from amphetype.Text import LessonMiner


class SourceModel(AmphModel):
  def signature(self):
    self.hidden = 1
    return (
      ["Source", "Length", "Results", "WPM", "Disabled"],
      [None, None, None, "%.1f", None],
    )

  def populateData(self, idxs):
    if len(idxs) == 0:
      return list(
        map(
          list,
          DB.fetchall("""
      select s.rowid,s.name,t.count,r.count,r.wpm,ifelse(nullif(t.dis,t.count),'No','Yes')
          from source as s
          left join (select source,count(*) as count,count(disabled) as dis from text group by source) as t
            on (s.rowid = t.source)
          left join (select source,count(*) as count,avg(wpm) as wpm from result group by source) as r
            on (t.source = r.source)
          where s.disabled is null
          order by s.name"""),
        )
      )

    if len(idxs) > 1:
      return []

    r = self.rows[idxs[0]]

    return list(
      map(
        list,
        DB.fetchall(
          """select t.rowid,substr(t.text,0,40)||"...",length(t.text),r.count,r.m,ifelse(t.disabled,'Yes','No')
        from (select rowid,* from text where source = ?) as t
        left join (select text_id,count(*) as count,agg_median(wpm) as m from result group by text_id) as r
          on (t.id = r.text_id)
        order by t.rowid""",
          (r[0],),
        ),
      )
    )


class TextManager(QWidget):
  setText = pyqtSignal("PyQt_PyObject")
  gotoText = pyqtSignal()
  refreshSources = pyqtSignal()

  split_text = [
    "Welcome to Amphetype!\n",
    "Amphetype is a layout-agnostic typing program that measures your speed and progress",
    "while identifying typing problems.\n",
    "This is just a default text since your database is empty.",
    'Go to the "Sources" tab and try importing a text.\n',
    "Several whole novels already come packaged with Amphetype!",
    "Later on you can generate highly customizable lessons directly from your statistics!\n",
    "Good luck!",
  ]
  welcome_text = " ".join(split_text)

  defaultText = (
    "",
    0,
    welcome_text,
  )

  def __init__(self, *args):
    super(TextManager, self).__init__(*args)

    self.diff_eval = lambda x: 1
    self.model = SourceModel()
    tv = AmphTree(self.model)
    tv.doubleClicked["QModelIndex"].connect(self.onDoubleClicked)
    tv.resizeColumnToContents(0)
    tv.setColumnWidth(0, max(340, tv.columnWidth(0) + 40))

    # Set column size of tree view columns in Text Manager
    # This prevents having a bottom scroll wheel to view all the fields in the
    # tree view
    tv.setColumnWidth(1, min(60, tv.columnWidth(1) + 10))
    tv.setColumnWidth(2, min(60, tv.columnWidth(2) + 10))
    tv.setColumnWidth(3, min(60, tv.columnWidth(3) + 10))
    tv.setColumnWidth(4, min(60, tv.columnWidth(4) + 10))
    self.tree = tv

    self.progress = QProgressBar()
    self.progress.setRange(0, 100)
    self.progress.hide()

    regex_usage_msg = str(
      "on all selected texts that match "
      '<a href="http://en.wikipedia.org/wiki/Regular_expression">regular expression</a>'
    )

    main_panel = self._create_layout()
    self.setLayout(main_panel)

    # self.setLayout(
    #   AmphBoxLayout(
    #     [
    #       (
    #         [
    #           source_list_msg,
    #           (self.tree, 1),
    #           self.progress,
    #           [
    #             AmphButton("Import Texts", self.addFiles),
    #             AmphButton("Import code file", self._select_code_files),
    #             None,
    #             AmphButton("Enable All", self.enableAll),
    #             AmphButton("Delete Disabled", self.removeDisabled),
    #             None,
    #             AmphButton("Update List", self.update_text_list),
    #           ],
    #           [
    #             AmphButton("Toggle disabled", self.disableSelected),
    #             regex_usage_msg,
    #             SettingsEdit("text_regex"),
    #           ],
    #         ],
    #         1,
    #       ),
    #       [
    #         [
    #           "Selection method for new lessons:",
    #           SettingsCombo(
    #             "select_method",
    #             ["Random", "In Order", "Difficult", "Easy"],
    #           ),
    #           None,
    #         ],
    #         lesson_order_msg,
    #         20,
    #         AmphGridLayout(
    #           [
    #             [
    #               (
    #                 "Repeat <i>texts</i> that don't meet the following requirements:\n",
    #                 (1, 3),
    #               )
    #             ],
    #             ["WPM:", SettingsEdit("min_wpm")],
    #             ["Accuracy:", SettingsEdit("min_acc"), (None, (0, 1))],
    #             [
    #               (
    #                 "Repeat <i>lessons</i> that don't meet the following requirements:\n",
    #                 (1, 3),
    #               )
    #             ],
    #             ["WPM:", SettingsEdit("min_lesson_wpm")],
    #             ["Accuracy:", SettingsEdit("min_lesson_acc")],
    #           ]
    #         ),
    #         None,
    #       ],
    #     ],
    #     QBoxLayout.Direction.LeftToRight,
    #   )
    # )

    # self._set_layout()
    Settings.signal_for("select_method").connect(self._set_select)
    Settings.signal_for("text_force_ascii").connect(self.nextText)
    self._set_select(Settings.get("select_method"))

  def _create_layout(self) -> QLayout:
    # Add Message at the top of the stack panel
    source_list_msg = str(
      "Below you will see the different text sources used. Disabling texts or sources deactivates "
      "them so they won't be selected for typing. You can double click a text to do that "
      "particular text.",
    )

    main_stack_panel = QVBoxLayout()
    main_stack_panel.addWidget(WordWrapLabel(source_list_msg))

    # Add a line before the side by side panel
    source_label_divider = QFrame()
    source_label_divider.setFrameShape(QFrame.HLine)
    source_label_divider.setFrameShadow(QFrame.Sunken)

    ## TODO: How does self.progress work? if it works, add it to the vertical stack layout

    main_stack_panel.addWidget(source_label_divider)

    # Add tree and other side by side
    side_by_side = QHBoxLayout()

    side_by_side.addWidget(self.tree, 5)

    # Settings Panel
    settings_panel = QVBoxLayout()

    # Lesson Order Selector
    settings_panel.addWidget(WordWrapLabel("<b>Set method for picking next lessons:</b>"))

    settings_panel.addWidget(
      SettingsCombo(
        "select_method",
        ["Random", "In Order", "Difficult", "Easy"],
      ),
    )
    lesson_order_msg = str(
      "<b>Random</b> selects a random text from the lesson listed in the sources."
      "<br />"
      "<b>In Order</b> works by selecting the next text after the one you completed last, in "
      "the order they were added to the database"
      "<br/>"
      "<b>Easy/Difficult</b> works by estimating your WPM for several random texts and choosing"
      " the fastest/slowest)"
    )
    settings_panel.addWidget(WordWrapLabel(lesson_order_msg))

    lesson_order_divider = QFrame()
    lesson_order_divider.setFrameShape(QFrame.HLine)
    lesson_order_divider.setFrameShadow(QFrame.Sunken)
    settings_panel.addWidget(lesson_order_divider)

    set_text_wpm_layout = QHBoxLayout()
    set_text_wpm_layout.addWidget(WordWrapLabel("WPM (text): "), 2)
    set_text_wpm_layout.addWidget(SettingsEdit("min_wpm"), 1)

    set_text_accuracy_layout = QHBoxLayout()
    set_text_accuracy_layout.addWidget(WordWrapLabel("Accuracy (text): "), 2)
    set_text_accuracy_layout.addWidget(SettingsEdit("min_acc"), 1)

    set_lesson_wpm_layout = QHBoxLayout()
    set_lesson_wpm_layout.addWidget(WordWrapLabel("WPM (lesson): "), 2)
    set_lesson_wpm_layout.addWidget(SettingsEdit("min_lesson_wpm"), 1)

    set_lesson_accuracy_layout = QHBoxLayout()
    set_lesson_accuracy_layout.addWidget(WordWrapLabel("Accuracy (lesson): "), 2)
    set_lesson_accuracy_layout.addWidget(SettingsEdit("min_lesson_acc"), 1)

    settings_panel.addWidget(
      WordWrapLabel("Repeat <i>texts</i> that don't meet the following requirements:\n")
    )
    settings_panel.addLayout(set_text_wpm_layout)
    settings_panel.addLayout(set_text_accuracy_layout)

    repeat_settings_divider = QFrame()
    repeat_settings_divider.setFrameShape(QFrame.HLine)
    repeat_settings_divider.setFrameShadow(QFrame.Sunken)
    settings_panel.addWidget(repeat_settings_divider)

    settings_panel.addWidget(
      WordWrapLabel("Repeat <i>lessons</i> that don't meet the following requirements:\n")
    )

    settings_panel.addLayout(set_lesson_wpm_layout)
    settings_panel.addLayout(set_lesson_accuracy_layout)

    settings_panel.addStretch()

    side_by_side.addLayout(settings_panel, 2)
    main_stack_panel.addLayout(side_by_side)

    split_panel_divider = QFrame()
    split_panel_divider.setFrameShape(QFrame.HLine)
    split_panel_divider.setFrameShadow(QFrame.Sunken)
    main_stack_panel.addWidget(split_panel_divider)

    manage_sources_row = QHBoxLayout()
    manage_sources_row.addWidget(QLabel("<b>Add Items to Sources: </b>"))
    manage_sources_row.addWidget(AmphButton("Import Texts", self.addFiles))
    manage_sources_row.addWidget(AmphButton("Import Code", self._select_code_files))

    manage_source_divider = QFrame()
    manage_source_divider.setFrameShape(QFrame.VLine)
    manage_source_divider.setFrameShadow(QFrame.Sunken)
    manage_sources_row.addWidget(manage_source_divider)

    manage_sources_row.addWidget(QLabel("<b>Manage Sources: </b>"))
    manage_sources_row.addWidget(AmphButton("Enable All Text", self.enableAll))
    manage_sources_row.addWidget(AmphButton("Remove Disabled", self.removeDisabled))

    additional_source_divider = QFrame()
    additional_source_divider.setFrameShape(QFrame.VLine)
    additional_source_divider.setFrameShadow(QFrame.Sunken)
    manage_sources_row.addWidget(additional_source_divider)

    manage_sources_row.addWidget(WordWrapLabel("<b>Update Sources: </b>"))
    manage_sources_row.addWidget(AmphButton("Update List", self.update_text_list))

    manage_sources_row.addStretch()

    main_stack_panel.addLayout(manage_sources_row)

    return main_stack_panel

  def _set_select(self, v):
    if v == 0 or v == 1:
      self.diff_eval = lambda x: 1
      self.nextText()
      return

    hist = time.time() - 86400.0 * Settings.get("history")
    tri = dict(
      DB.execute(
        """
          select data,agg_median(time) as wpm from statistic
          where w >= ? and type = 1
          group by data""",
        (hist,),
      ).fetchall()
    )  # [(t, (m, c)) for t, m, c in

    g = list(tri.values())
    if len(g) == 0:
      return lambda x: 1
    g.sort(reverse=True)
    expect = g[len(g) // 4]

    def _func(v):
      text = v[2]
      v = 0
      s = 0.0
      for i in range(0, len(text) - 2):
        t = text[i : i + 3]
        if t in tri:
          s += tri[t]
        else:
          s += expect
          v += 1
      avg = s / (len(text) - 2)

      divider = 1 if avg < 1 else avg

      return 12.0 / divider

    self.diff_eval = _func
    self.nextText()

  def _select_code_files(self) -> None:
    user_home_dir = path.expanduser("~")
    found_dir = user_home_dir if str(user_home_dir) else (Settings.DATA_DIR / "texts")

    file_dialog = QFileDialog(self, "Import Text From Source Code", directory=str(found_dir))
    file_dialog.setNameFilters(["UTF-8 source code (*.py)", "All files (*)"])
    file_dialog.setFileMode(QFileDialog.ExistingFiles)
    file_dialog.setAcceptMode(QFileDialog.AcceptOpen)

    file_dialog.filesSelected["QStringList"].connect(self._extract_lessons_from_code)

    file_dialog.show()

  def _extract_lessons_from_code(self, files):
    for file in files:
      print(file)

  def addFiles(self):
    qf = QFileDialog(self, "Import Text From File(s)", directory=str(Settings.DATA_DIR / "texts"))
    qf.setNameFilters(["UTF-8 text files (*.txt)", "All files (*)"])
    qf.setFileMode(QFileDialog.ExistingFiles)
    qf.setAcceptMode(QFileDialog.AcceptOpen)

    qf.filesSelected["QStringList"].connect(self.setImpList)

    qf.show()

  def setImpList(self, files):
    self.sender().hide()
    self.progress.show()
    for x in map(str, files):
      self.progress.setValue(0)
      fname = path.basename(x)
      try:
        lm = LessonMiner(x)
      except Exception:
        log.error(f"failed to process file {fname}!")
        continue
      lm.progress[int].emit(self.progress.setValue)
      self.addTexts(fname, lm, update=False)

    self.progress.hide()
    self.update()
    DB.commit()

  def addTexts(self, source, texts, lesson=None, update=True):
    id = DB.getSource(source, lesson)
    r: typing.List[str] = []
    for x in texts:
      h = hashlib.sha1()
      h.update(x.encode("utf-8"))
      txt_id = h.hexdigest()
      dis = 1 if lesson == 2 else None
      try:
        DB.execute(
          "insert into text (id,text,source,disabled) values (?,?,?,?)",
          (txt_id, x, id, dis),
        )
        r.append(txt_id)
      except Exception:
        pass  # silently skip ...
    if update:
      self.update_text_list()
    if lesson:
      DB.commit()
    return r

  def newReview(self, review):
    q = self.addTexts("<Reviews>", [review], lesson=2, update=False)
    if q:
      v = DB.fetchone("select id,source,text from text where id = ?", self.defaultText, q)
      self.emit_text(v)
    else:
      self.nextText()

  def update_text_list(self):
    self.refreshSources.emit()
    self.model.reset()

  def nextText(self):
    type = Settings.get("select_method")

    if type != 1:
      # Not in order
      v = DB.execute(
        "select id,source,text from text where disabled is null order by random() limit %d"
        % Settings.get("num_rand")
      ).fetchall()
      if len(v) == 0:
        v = None
      elif type == 2:
        v = min(v, key=self.diff_eval)
      elif type == 3:
        v = max(v, key=self.diff_eval)
      else:
        v = v[0]  # random, just pick the first
    else:
      # Fetch in order
      last_id = (0,)
      g = DB.fetchone(
        """select r.text_id
        from result as r left join source as s on (r.source = s.rowid)
        where (s.discount is null) or (s.discount = 1) order by r.w desc limit 1""",
        None,
      )
      if g is not None:
        last_id = DB.fetchone("select rowid from text where id = ?", last_id, g)
      v = DB.fetchone(
        "select id,source,text from text where rowid > ? and disabled is null order by rowid asc limit 1",
        None,
        last_id,
      )

    if v is None:
      v = self.defaultText

    self.emit_text(v)

  def removeUnused(self):
    DB.execute("""
      delete from source where rowid in (
        select s.rowid from source as s
          left join result as r on (s.rowid=r.source)
          left join text as t on (t.source=s.rowid)
        group by s.rowid
        having count(r.rowid) = 0 and count(t.rowid) = 0
      )""")
    DB.execute("""
      update source set disabled = 1 where rowid in (
        select s.rowid from source as s
          left join result as r on (s.rowid=r.source)
          left join text as t on (t.source=s.rowid)
        group by s.rowid
        having count(r.rowid) > 0 and count(t.rowid) = 0
      )""")
    self.refreshSources.emit()

  def removeDisabled(self):
    DB.execute("delete from text where disabled is not null")
    self.removeUnused()
    self.update_text_list()
    DB.commit()

  def enableAll(self):
    DB.execute("update text set disabled = null where disabled is not null")
    self.update_text_list()

  def disableSelected(self):
    cats, texts = self.getSelected()
    DB.setRegex(Settings.get("text_regex"))
    DB.executemany(
      """update text set disabled = ifelse(disabled,NULL,1)
        where rowid = ? and regex_match(text) = 1""",
      [(x,) for x in texts],
    )
    DB.executemany(
      """update text set disabled = ifelse(disabled,NULL,1)
        where source = ? and regex_match(text) = 1""",
      [(x,) for x in cats],
    )
    self.update_text_list()

  def getSelected(self):
    texts = []
    cats = []
    for idx in self.tree.selectedIndexes():
      if idx.column() != 0:
        continue
      if idx.parent().isValid():
        texts.append(self.model.data(idx, Qt.UserRole)[0])
      else:
        cats.append(self.model.data(idx, Qt.UserRole)[0])
    return (cats, texts)

  def onDoubleClicked(self, idx):
    p = idx.parent()
    if not p.isValid():
      return

    q = self.model.data(idx, Qt.UserRole)
    v = DB.fetchall("select id,source,text from text where rowid = ?", (q[0],))

    self.cur = v[0] if len(v) > 0 else self.defaultText
    self.emit_text(self.cur)
    self.gotoText.emit()

  def emit_text(self, v):
    log.info("setting new text id=%s length=%d source=%s", v[0], len(v[2]), v[1])
    if Settings.get("text_force_ascii"):
      text_id, text_src, found_txt = v
      v = (text_id, text_src, force_ascii(found_txt))
    self.setText.emit(v)


_bothered = False


def force_ascii(txt):
  try:
    import codecs

    import translitcodec  # noqa

    return codecs.encode(txt, "translit/long")
  except ImportError:
    # What do we do here?
    global _bothered
    if not _bothered:
      QMessageBox.information(
        None,
        "Missing Module",
        "Module <code>translitcodec</code> needed to translate unicode to ascii.\nTry running <code>pip install translitcodec</code>.",
      )
    _bothered = True
    return txt.encode("ascii", errors="replace").decode()
