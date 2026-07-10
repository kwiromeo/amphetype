import hashlib
import logging as log
import os.path as path
import time
import typing

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
  QFileDialog,
  QFrame,
  QHBoxLayout,
  QLabel,
  QLayout,
  QMenu,
  QMessageBox,
  QProgressBar,
  QVBoxLayout,
  QWidget,
)

from amphetype.Config import Settings, SettingsCombo, SettingsEdit
from amphetype.Data import DB
from amphetype.QtUtil import (
  AmphButton,
  AmphModel,
  AmphTree,
  WordWrapLabel,
)
from amphetype.Text import LessonMiner
from amphetype.lesson_builder import code_lessons


class SourceModel(AmphModel):
  # Skip the first column (rowid) when displaying data in the tree view.
  hidden = 1

  def signature(self):
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

    source_row = self.rows[idxs[0]]

    return list(
      map(
        list,
        DB.fetchall(
          """select t.rowid,substr(t.text,0,40)||"...",length(t.text),r.count,r.m,ifelse(t.disabled,'Yes','No')
        from (select rowid,* from text where source = ?) as t
        left join (select text_id,count(*) as count,agg_median(wpm) as m from result group by text_id) as r
          on (t.id = r.text_id)
        order by t.rowid""",
          (source_row[0],),
        ),
      )
    )


class TextManager(QWidget):
  setText = pyqtSignal("PyQt_PyObject")
  gotoText = pyqtSignal()
  refreshSources = pyqtSignal()

  welcome_message_lines = [
    "Welcome to Amphetype!\n",
    "Amphetype is a layout-agnostic typing program that measures your speed and progress",
    "while identifying typing problems.\n",
    "This is just a default text since your database is empty.",
    'Go to the "Sources" tab and try importing a text.\n',
    "Several whole novels already come packaged with Amphetype!",
    "Later on you can generate highly customizable lessons directly from your statistics!\n",
    "Good luck!",
  ]
  welcome_text = " ".join(welcome_message_lines)

  empty_db_placeholder = (
    "",
    0,
    welcome_text,
  )

  def __init__(self, *args):
    super(TextManager, self).__init__(*args)

    self.difficulty_evaluator = lambda x: 1
    self._replay_pending = False
    self.model = SourceModel()
    sources_tree_view = AmphTree(self.model)
    sources_tree_view.doubleClicked["QModelIndex"].connect(self.onDoubleClicked)
    sources_tree_view.resizeColumnToContents(0)
    sources_tree_view.setColumnWidth(0, max(340, sources_tree_view.columnWidth(0) + 40))

    # Set column size of tree view columns in Text Manager
    # This prevents having a bottom scroll wheel to view all the fields in the
    # tree view
    sources_tree_view.setColumnWidth(1, min(60, sources_tree_view.columnWidth(1) + 10))
    sources_tree_view.setColumnWidth(2, min(60, sources_tree_view.columnWidth(2) + 10))
    sources_tree_view.setColumnWidth(3, min(60, sources_tree_view.columnWidth(3) + 10))
    sources_tree_view.setColumnWidth(4, min(60, sources_tree_view.columnWidth(4) + 10))
    self.tree = sources_tree_view
    self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.tree.customContextMenuRequested.connect(self.on_context_menu)

    self.progress = QProgressBar()
    self.progress.setRange(0, 100)
    self.progress.hide()

    ui_panel = self._create_layout()
    self.setLayout(ui_panel)

    # self._set_layout()
    Settings.signal_for("select_method").connect(self._set_select)
    Settings.signal_for("text_force_ascii").connect(self.nextText)
    self._set_select(Settings.get("select_method"))

    self._replay_pending = True

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
      "<b>Random</b> selects a random text from the lessons listed in the sources."
      "<br />"
      "<b>In Order</b> selects the next text after the one you completed last, in "
      "the order they were added to the database."
      "<br/>"
      "<b>Easy/Difficult</b> estimates your WPM for several random texts and choosing"
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

    settings_panel.addWidget(WordWrapLabel("<b>Set threshold for reapeating text:</b>"))
    settings_panel.addWidget(
      WordWrapLabel("Repeat <b><i>texts</i></b> that don't meet the following requirements:\n")
    )
    settings_panel.addLayout(set_text_wpm_layout)
    settings_panel.addLayout(set_text_accuracy_layout)

    repeat_settings_divider = QFrame()
    repeat_settings_divider.setFrameShape(QFrame.HLine)
    repeat_settings_divider.setFrameShadow(QFrame.Sunken)
    settings_panel.addWidget(repeat_settings_divider)

    settings_panel.addWidget(WordWrapLabel("<b>Set threshold for reapeating lessons:</b>"))
    settings_panel.addWidget(
      WordWrapLabel("Repeat <b><i>lessons</i></b> that don't meet the following requirements:\n")
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
    manage_sources_row.addWidget(AmphButton("Import Texts", self._select_text_files))
    manage_sources_row.addWidget(AmphButton("Import Code", self._select_code_files))

    manage_source_divider = QFrame()
    manage_source_divider.setFrameShape(QFrame.VLine)
    manage_source_divider.setFrameShadow(QFrame.Sunken)
    manage_sources_row.addWidget(manage_source_divider)

    manage_sources_row.addWidget(QLabel("<b>Manage Sources: </b>"))
    manage_sources_row.addWidget(AmphButton("Enable All Text", self.enableAll))
    manage_sources_row.addWidget(AmphButton("Toggle Selected", self.disableSelected))
    manage_sources_row.addWidget(AmphButton("Remove Disabled", self.removeDisabled))

    additional_source_divider = QFrame()
    additional_source_divider.setFrameShape(QFrame.VLine)
    additional_source_divider.setFrameShadow(QFrame.Sunken)
    manage_sources_row.addWidget(additional_source_divider)

    # Add update source list button
    manage_sources_row.addStretch()
    manage_sources_row.addWidget(AmphButton("Update Source List", self.update_sources_list))
    manage_sources_row.addStretch()

    main_stack_panel.addLayout(manage_sources_row)

    # TODO (Romeo K. 12/17/2025): add bulk regex enable/disable back into UI.
    # Previous implementation:
    # [
    #   AmphButton("Toggle disabled", self.disableSelected),
    #   regex_usage_msg,
    #   SettingsEdit("text_regex"),
    # ],
    #
    # UI help message
    # regex_usage_msg = str(
    #   "on all selected texts that match "
    #   '<a href="http://en.wikipedia.org/wiki/Regular_expression">regular expression</a>'
    # )

    return main_stack_panel

  def _set_select(self, method_index):
    if method_index == 0 or method_index == 1:
      self.difficulty_evaluator = lambda x: 1
      self.nextText()
      return

    history_threshold = time.time() - 86400.0 * Settings.get("history")
    trigram_wpm_map = dict(
      DB.execute(
        """
          select data,agg_median(time) as wpm from statistic
          where w >= ? and type = 1
          group by data""",
        (history_threshold,),
      ).fetchall()
    )

    wpm_values = list(trigram_wpm_map.values())
    if len(wpm_values) == 0:
      return lambda x: 1
    wpm_values.sort(reverse=True)
    fallback_wpm = wpm_values[len(wpm_values) // 4]

    def calc_text_difficulty(text_record):
      text_content = text_record[2]
      unknown_trigrams = 0
      total_wpm = 0.0
      for i in range(0, len(text_content) - 2):
        trigram = text_content[i : i + 3]
        if trigram in trigram_wpm_map:
          total_wpm += trigram_wpm_map[trigram]
        else:
          total_wpm += fallback_wpm
          unknown_trigrams += 1
      average_wpm = total_wpm / (len(text_content) - 2)

      divider = 1 if average_wpm < 1 else average_wpm

      return 12.0 / divider

    self.difficulty_evaluator = calc_text_difficulty
    self.nextText()

  def _select_code_files(self) -> None:
    user_home_dir = path.expanduser("~")
    found_dir = user_home_dir if str(user_home_dir) else (Settings.DATA_DIR / "texts")

    file_dialog = QFileDialog(self, "Import Text From Source Code", directory=str(found_dir))
    file_dialog.setNameFilters(["UTF-8 source code (*.py)", "All files (*)"])
    file_dialog.setFileMode(QFileDialog.ExistingFiles)
    file_dialog.setAcceptMode(QFileDialog.AcceptOpen)

    file_dialog.filesSelected["QStringList"].connect(self._get_lessons_from_code)

    file_dialog.show()

  def _get_lessons_from_code(self, files):
    for file in files:
      lesson_extractor = code_lessons.LessonExtractor(file)
      found_lessons = lesson_extractor.get_lessons()
      if not found_lessons:
        continue

      # Add found lesson to database
      pseudo_filename = code_lessons.create_id_from_path(file)
      self.addTexts(pseudo_filename, found_lessons, update=False)

    self.progress.hide()
    self.update_sources_list()
    DB.commit()

  def _select_text_files(self):
    qf = QFileDialog(self, "Import Text From File(s)", directory=str(Settings.DATA_DIR / "texts"))
    qf.setNameFilters(["UTF-8 text files (*.txt)", "All files (*)"])
    qf.setFileMode(QFileDialog.ExistingFiles)
    qf.setAcceptMode(QFileDialog.AcceptOpen)

    qf.filesSelected["QStringList"].connect(self._get_lessons_from_text)

    qf.show()

  def _get_lessons_from_text(self, files: typing.List[str]):
    assert self.sender() is not None
    self.sender().hide()
    self.progress.show()
    for x in files:
      self.progress.setValue(0)
      fname = path.basename(x)
      try:
        lesson_miner = LessonMiner(x)
      except Exception:
        log.error(f"failed to process file {fname}!")
        continue
      lesson_miner.progress[int].emit(self.progress.setValue)
      self.addTexts(fname, lesson_miner, update=False)

    self.progress.hide()
    self.update_sources_list()
    DB.commit()

  def addTexts(self, source: str, texts: typing.Iterable[str], lesson=None, update=True):
    source_id = DB.getSource(source, lesson)
    inserted_text_ids: typing.List[str] = []
    for x in texts:
      h = hashlib.sha1()
      h.update(x.encode("utf-8"))
      txt_id = h.hexdigest()
      dis = 1 if lesson == 2 else None
      try:
        DB.execute(
          "insert into text (id,text,source,disabled) values (?,?,?,?)",
          (txt_id, x, source_id, dis),
        )
        inserted_text_ids.append(txt_id)
      except Exception:
        pass  # silently skip ...
    if update:
      self.update_sources_list()
    if lesson:
      DB.commit()
    return inserted_text_ids

  def newReview(self, review):
    self._replay_pending = False
    inserted_ids = self.addTexts("<Reviews>", [review], lesson=2, update=False)
    if inserted_ids:
      text_record = DB.fetchone(
        "select id,source,text from text where id = ?",
        self.empty_db_placeholder,
        (inserted_ids[0],),
      )
      self.emit_text(text_record)
    else:
      self.nextText()

  def update_sources_list(self):
    self.refreshSources.emit()
    self.model.reset()

  def _last_incomplete_text(self):
    """Return (text_id, source, text) for the most recent result that missed
    its WPM/accuracy target, or None if the last result was good, the text
    or source has been disabled/deleted, or there are no results."""
    row = DB.fetchone(
      """select t.id, t.source, t.text, r.wpm, r.accuracy, s.discount
      from result r
      join text t on t.id = r.text_id
      join source s on s.rowid = r.source
      where t.disabled is null and s.disabled is null
      order by r.w desc limit 1""",
      None,
    )
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

  def nextText(self):
    if self._replay_pending:
      self._replay_pending = False
      record = self._last_incomplete_text()
      if record is not None:
        self.emit_text(record)
        return

    selection_mode = Settings.get("select_method")

    if selection_mode != 1:
      # Not in order
      text_records = DB.execute(
        "select id,source,text from text where disabled is null order by random() limit %d"
        % Settings.get("num_rand")
      ).fetchall()
      if len(text_records) == 0:
        text_record = None
      elif selection_mode == 2:
        text_record = min(text_records, key=self.diff_eval)
      elif selection_mode == 3:
        text_record = max(text_records, key=self.diff_eval)
      else:
        text_record = text_records[0]  # random, just pick the first
    else:
      # Fetch in order
      last_text_rowid = (0,)
      last_text_id = DB.fetchone(
        """select r.text_id
        from result as r left join source as s on (r.source = s.rowid)
        where (s.discount is null) or (s.discount = 1) order by r.w desc limit 1""",
        None,
      )
      if last_text_id is not None:
        last_text_rowid = DB.fetchone(
          "select rowid from text where id = ?", last_text_rowid, last_text_id
        )
      text_record = DB.fetchone(
        "select id,source,text from text where rowid > ? and disabled is null order by rowid asc limit 1",
        None,
        last_text_rowid,
      )

    if text_record is None:
      text_record = self.defaultText

    self.emit_text(text_record)

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
    self.update_sources_list()
    DB.commit()

  def enableAll(self):
    DB.execute("update text set disabled = null where disabled is not null")
    self.update_sources_list()

  def disableSelected(self):
    sources, texts = self.getSelected()
    DB.setRegex(Settings.get("text_regex"))
    DB.executemany(
      """update text set disabled = ifelse(disabled,NULL,1)
        where rowid = ? and regex_match(text) = 1""",
      [(x,) for x in texts],
    )
    DB.executemany(
      """update text set disabled = ifelse(disabled,NULL,1)
        where source = ? and regex_match(text) = 1""",
      [(x,) for x in sources],
    )
    self.update_sources_list()

  def on_context_menu(self, pos):
    menu = QMenu(self)
    delete_action = menu.addAction("Delete Selected")
    action = menu.exec_(self.tree.mapToGlobal(pos))
    if action == delete_action:
      self.deleteSelected()

  def deleteSelected(self):
    sources, texts = self.getSelected()
    if not sources and not texts:
      return

    msg = f"Are you sure you want to delete {len(sources)} sources and {len(texts)} texts?\n\nThis will also delete ALL associated results and statistics."
    if QMessageBox.question(self, "Confirm Deletion", msg) != QMessageBox.Yes:
      return

    # Delete Sources
    for rowid in sources:
      # Delete related stats/mistakes via results
      DB.execute("DELETE FROM mistake WHERE w IN (SELECT w FROM result WHERE source = ?)", (rowid,))
      DB.execute(
        "DELETE FROM statistic WHERE w IN (SELECT w FROM result WHERE source = ?)", (rowid,)
      )
      DB.execute("DELETE FROM result WHERE source = ?", (rowid,))
      DB.execute("DELETE FROM text WHERE source = ?", (rowid,))
      DB.execute("DELETE FROM source WHERE rowid = ?", (rowid,))

    # Delete Individual Texts
    for rowid in texts:
      # Get the unique text ID (hash) to clean up results
      text_id = DB.fetchone("SELECT id FROM text WHERE rowid = ?", (None,), (rowid,))[0]
      if text_id:
        DB.execute(
          "DELETE FROM mistake WHERE w IN (SELECT w FROM result WHERE text_id = ?)", (text_id,)
        )
        DB.execute(
          "DELETE FROM statistic WHERE w IN (SELECT w FROM result WHERE text_id = ?)", (text_id,)
        )
        DB.execute("DELETE FROM result WHERE text_id = ?", (text_id,))
      DB.execute("DELETE FROM text WHERE rowid = ?", (rowid,))

    DB.commit()
    self.update_sources_list()

    # Ensure we aren't pointing to a deleted text
    self.nextText()

  def getSelected(self):
    texts = []
    sources = []
    for idx in self.tree.selectedIndexes():
      if idx.column() != 0:
        continue
      if idx.parent().isValid():
        texts.append(self.model.data(idx, Qt.UserRole)[0])
      else:
        sources.append(self.model.data(idx, Qt.UserRole)[0])
    return (sources, texts)

  def onDoubleClicked(self, index):
    parent_index = index.parent()
    if not parent_index.isValid():
      return

    row_data = self.model.data(index, Qt.UserRole)
    text_record = DB.fetchone(
      "select id,source,text from text where rowid = ?", self.empty_db_placeholder, (row_data[0],)
    )

    self.current_text_record = text_record
    self.emit_text(self.current_text_record)
    self.gotoText.emit()

  def emit_text(self, text_record):
    log.info(
      "setting new text id=%s length=%d source=%s",
      text_record[0],
      len(text_record[2]),
      text_record[1],
    )
    if Settings.get("text_force_ascii"):
      text_id, text_src, found_txt = text_record
      text_record = (text_id, text_src, force_ascii(found_txt))
    self.setText.emit(text_record)


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
