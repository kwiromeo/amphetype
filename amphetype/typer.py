
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from amphetype.settings import *
from amphetype.layout import FStackedLayout, FBoxLayout
from amphetype.timingtuple import RunStats

from time import perf_counter as timer


RETURN_CHAR = '⏎' # '↵'
PARA_SEP = '\u2029'
LINE_SEP = '\u2028'
# DIAMOND = '◈'
# VIS_SPACE = '␣'



### TEXTDOCUMENT

text_props = dict(
  underline=QTextCharFormat.FontUnderline,
  color=QTextCharFormat.ForegroundBrush,
  background=QTextCharFormat.BackgroundBrush,
  kerning=QTextCharFormat.FontKerning,
  overline=QTextCharFormat.FontOverline,
  italic=QTextCharFormat.FontItalic)

def text_style(*args, **kwargs):
  res = QTextCharFormat()
  for a in args:
    res.setProperty(text_props[a], True)
  for k,v in kwargs.items():
    res.setProperty(text_props[k], v)
  return res



class Cursor(QTextCursor):
  def __init__(self, doc_or_cursor, position=None, select=None, fixed=False, **kwargs):
    super().__init__(doc_or_cursor, **kwargs)
    self.setKeepPositionOnInsert(fixed)
    if position is not None:
      if isinstance(position, tuple):
        self.setPosition(position[0])
        self.setPosition(position[1], self.KeepAnchor)
      else:
        self.setPosition(position)
    if select is not None:
      self.movePosition(select, self.KeepAnchor)

  def nextChar(self):
    return self.document().characterAt(self.position())

  def __repr__(self):
    if self.hasSelection():
      return f'({self.position()}/a={self.anchor()}/t="{self.selectedText()}")'
    return f'({self.position()})'



class LessonDocument(QTextDocument):
  style_untyped = text_style(kerning=False,
                             background=QBrush(QColor('antiquewhite')))
  style_error = text_style(kerning=False,
                           background=QBrush(QColor('firebrick')),
                           color=QBrush(QColor('white')))
  style_anyerror = text_style(kerning=False,
                              background=QBrush(QColor('darksalmon')))
  style_correct = text_style(kerning=False,
                             color=QBrush(QColor('dimgrey')),
                             background=QBrush(QColor('antiquewhite')))
  style_inactive = text_style(color=QBrush(QColor('grey')))


  # Cursor position changed.
  sig_position = pyqtSignal(QTextCursor)

  started = pyqtSignal()
  ready = pyqtSignal(str)
  completed = pyqtSignal('PyQt_PyObject')
  error = pyqtSignal(str)
  progress = pyqtSignal(int)

  def __init__(self, *args, **kwargs):
    super().__init__(*args, undoRedoEnabled=False, **kwargs)
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSize(16)
    self.setDefaultFont(f)

    self.set_text('default text')

  def block_format(self):
    b = QTextBlockFormat()
    b.setTopMargin(6.0)
    b.setBottomMargin(6.0)
    return b

  def set_text(self, text, prologue='', epilogue=''):
    text = text or 'default text'

    self.clear()
    
    c = Cursor(self)
    c.setBlockFormat(self.block_format())
    
    c.insertText(prologue, self.style_inactive)
    pos = c.position()
    c.insertText(epilogue, self.style_inactive)

    self._original_text = text
    self._match_text = self.sanitize(text)
    self._display_text = self._match_text.replace(RETURN_CHAR, RETURN_CHAR + '\n')
    
    self._start = Cursor(self, position=pos, fixed=True)
    self._end = Cursor(self, position=pos)
    self.cursor = Cursor(self, position=pos)
    
    self.reset()

  def reset(self):
    assert self._match_text and self._display_text

    self.active_region().insertText(self._display_text, self.style_untyped)

    if self.cursor != self._start:
      self.cursor.setPosition(self._start.position())
      self.sig_position.emit(self.cursor)

    self._run = None
    self._first_error = None
    self.ready.emit(self._match_text)

  def active_region(self):
    c = Cursor(self, position=self._start.position())
    c.setPosition(self._end.position(), c.KeepAnchor)
    return c

  def sanitize(self, text):
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    text = text.replace('\n', RETURN_CHAR)
    return text


  def is_running(self):
    """True if a lesson has started but not yet completed."""
    return self._run is not None and not self._run.is_complete()

  def is_finished(self):
    """True if a lesson has started and then completed."""
    return self._run is not None and self._run.is_complete()

  def is_ready(self):
    """True if a lesson has not yet started."""
    return self._run is None

  def start(self):
    """Switches to running state (warm start)."""
    assert self.is_ready()      
    self._run = RunStats.make(self._match_text, timer())
    self.started.emit()

  def insert(self, char, overwrite=True, lenient=False):
    if self._run is None:
      # Cold start.
      self._run = RunStats.make(self._match_text)
      self.started.emit()

    correct = char == self._run.current.char
    should_advance = correct or overwrite

    if self._first_error is not None:
      # Previous error blocking us.
      self._run.advance(should_advance)
      style = self.style_anyerror if correct else self.style_error
      self.actual_insert(char, style, overwrite=should_advance)
      return

    # Update timing data.
    self._run.visit(correct)
    
    if correct:
      self.progress.emit(self._run.index)
    else:
      if not lenient:
        self._first_error = Cursor(self.cursor, fixed=True)

    # If not really advancing `_run` will track inserts we're doing.
    self._run.advance(should_advance)

    style = self.style_correct if correct else self.style_error
    self.actual_insert(char, style, overwrite=should_advance)

    if self.is_finished():
      self.completed.emit(self._run)
    else:
      self.sig_position.emit(self.cursor)

  def actual_insert(self, char, style, overwrite=True):
    self.cursor.insertText(char, style)
    if overwrite:
      self.cursor.deleteChar()
    if self.cursor.atBlockEnd():
      self.cursor.movePosition(QTextCursor.NextCharacter)

  def backspace(self, by_word=False, protected=False):
    if not self.is_running():
      return

    mark = Cursor(self.cursor)
    if mark.atBlockStart():
      mark.movePosition(mark.PreviousCharacter)
    if by_word:
      mark.movePosition(mark.PreviousWord)
    else:
      mark.movePosition(mark.PreviousCharacter)
    if mark < self._start:
      mark.setPosition(self._start.position())

    if mark == self.cursor:
      return

    while self.cursor > mark:
      if protected and not self._run.last_was_error():
        break
      c = self._run.pop_char()
      if c is not None:
        self.cursor.insertText(c, self.style_untyped)
        self.cursor.movePosition(QTextCursor.PreviousCharacter)
      self.cursor.deletePreviousChar()
    
    if self._first_error and self.cursor <= self._first_error:
      self._first_error = None

    self.sig_position.emit(self.cursor)
    
    


### WIDGET


class TyperOptions(QGroupBox):
  defaults = {
    'lenient_mode': False,
    'require_space': True,
    'overwrite_mode': True,
    'limit_backspace': False,
  }

  def __init__(self, S, *args, **kwargs):
    super().__init__(*args, title='Input Mode', **kwargs)

    self.setLayout(FBoxLayout([
      QCheckBox('Overwrite mode',
                checked=S['overwrite_mode'],
                toggled=S('overwrite_mode').set,
                toolTip="""In overwrite mode input will overwrite text in the buffer, no matter if correct or not. If turned off (insert mode) input will work more like real-world typing, but might be more distracting."""),
      QCheckBox("Lenient mode (NB! Read tooltip!)",
                checked=S['lenient_mode'], toggled=S('lenient_mode').set,
                toolTip="""In lenient mode past errors will not block further progress and you can complete a text without fully matching it. This might skew statistics slightly, because errors normally have the biggest impact on typing speed. Note also that combining this with overwrite mode means it's possible to complete a text without having typed every letter which means less statistical data can be collected (last letter <i>must</i> be typed correctly). It's recommended to leave it off unless you have a strong preference."""),
      QCheckBox('Wait for <SPACE> before start',
                checked=S['require_space'], toggled=S('require_space').set,
                toolTip="""Require user to press spacebar before accepting input. Note that turning this off means that the first letter, word, and trigraph of every lesson cannot be timed correctly, so they will be discarded."""),
      QCheckBox('Prevent backspacing over correct input',
                checked=S['limit_backspace'], toggled=S('limit_backspace').set,
                toolTip="""Turning this on will prevent backspace from going back over any correct input. Works best for overwrite mode."""),
      ]))



class TyperWidget(QTextEdit):
  def __init__(self, settings, *args, text=None, **kwargs):
    # Need to set TextEditable flag to make the cursor the normal
    # blinky kind. Not sure how to show it for read-only mode.
    super().__init__(*args,
                     contextMenuPolicy=Qt.NoContextMenu,
                     textInteractionFlags=Qt.TextEditable,
                     objectName='TyperWidget',
                     undoRedoEnabled=False,
                     cursorWidth=3,
                     **kwargs)

    self._settings = settings
    self._lesson = None
    # settings('lenient_mode').bind_value(self.setLenientMode)
    # settings('require_space').bind_value(self.setRequireSpace)
    settings('overwrite_mode').bind_value(self.setOverwriteMode)

  def setLesson(self, lesson):
    if lesson == self._lesson:
      self.setTextCursor(lesson.cursor)
      self.updateStatus()
      return
    
    if self._lesson is not None:
      self._lesson.sig_position.disconnect(self.setTextCursor)
      self._lesson.ready.disconnect(self.updateStatus)
      self._lesson.completed.disconnect(self.updateStatus)

    if self.document() != lesson:
      w = self.cursorWidth() # Layout thingamajig resets cursor width.
      self.setDocument(lesson)
      self.setCursorWidth(w)
    self.setTextCursor(lesson.cursor)
    self.updateStatus()

    lesson.sig_position.connect(self.setTextCursor)
    lesson.ready.connect(self.updateStatus)
    lesson.completed.connect(self.updateStatus)
    self._lesson = lesson

  def updateStatus(self):
    if self._lesson is None:
      return
    self.setReadOnly(self._lesson.is_finished())

  # Block mouse cursor movement. (Focus should still work.)
  def mousePressEvent(self, e):
    pass

  def mouseReleaseEvent(self, e):
    pass

  def keyPressEvent(self, evt):
    if not self._lesson:
      evt.ignore()
      return

    if evt.key() == Qt.Key_Backspace or evt.key() == Qt.Key_Back:
      by_word = bool(evt.modifiers() & (Qt.ControlModifier | Qt.MetaModifier | Qt.AltModifier))
      self.backspace(word=by_word)
    elif evt.key() == Qt.Key_Enter or evt.key() == Qt.Key_Return:
      self.insert(RETURN_CHAR)
    elif evt.key() == Qt.Key_Escape:
      self._lesson.reset()
    elif evt.text() and ord(evt.text()) >= 32:
      self.insert(evt.text())
    else:
      evt.ignore()
      return

    evt.accept()

  def insert(self, char):
    if self._lesson is None or self._lesson.is_finished():
      return
    
    if not self._lesson.is_running() and self._settings['require_space']:
      if char == ' ':
        self._lesson.start()
      return

    self._lesson.insert(char, overwrite=self.overwriteMode(), lenient=self._settings['lenient_mode'])

  def backspace(self, word=False):
    if self._lesson is None or not self._lesson.is_running():
      return
    self._lesson.backspace(by_word=word, protected=self._settings['limit_backspace'])




class TyperWindow(QWidget):
  wantReview = pyqtSignal('PyQt_PyObject')
  wantText = pyqtSignal()
  statsChanged = pyqtSignal()
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    app = QApplication.instance()
    self.S = app.settings.makeSettings('typer', TyperOptions.defaults)
    self.DB = app.DB

    self._typer = TyperWidget(self.S)
    self._label = QLabel()
    self._prog = QProgressBar()
    self._prog_layout = FStackedLayout([self._label, self._prog])

    doc = LessonDocument()
    doc.started.connect(self._prog_layout.cycle)
    doc.progress.connect(self._prog.setValue)
    doc.ready.connect(self.typingReady)
    doc.completed.connect(self.typingDone)

    self._typer.setLesson(doc)
    
    self._doc = doc

    self.S('require_space').bind_change(self.updateLabel)

    self.setLayout(FBoxLayout([
      [self._prog_layout,
       # QPushButton("test", clicked=self.XXX),
       TyperOptions(self.S)],
      (self._typer, 1),
      ]))

  # def XXX(self):
  #   import random
  #   a = ' '.join([random.choice('prologue is here.'.split()) for _ in range(random.randint(0, 8))])
  #   b = ' '.join([random.choice('this is a test.'.split()) for _ in range(random.randint(1, 10))])
  #   c = ' '.join([random.choice("where's the epilogue?".split()) for _ in range(random.randint(0, 8))])
  #   self._doc.set_text(b, a, c)
  
  def showEvent(self, evt):
    super().showEvent(evt)
    self._typer.setFocus()

  def typingReady(self, text):
    self._prog_layout.setCurrentIndex(0)
    self._prog.setMaximum(len(text))

  def setDefaultText(self):
    pass

  def setText(self, txt):
    self._current_lesson = txt
    textid, _, _ = txt
    pre,text,post = self.DB.getTextContext(textid)
    if text is None:
      return self.setDefaultText()
    pre = '[BEGIN]' if pre is None else pre[2]
    post = '[END]' if post is None else post[2]

    self._doc.set_text(text[2], prologue=(pre + '\n'), epilogue=('\n' + post))

  def updateLabel(self):
    text = []
    text.append("[This beta typer will not collect statistics currently, don't use it!]")
    if self.S['require_space']:
      text.append("Press SPACE to start typing the text.")
    else:
      text.append("Text ready for typing!")
    text.append("Press ESCAPE to cancel at any time.")
    text.append("Check out the preferences tab for ways to customize input.")
    self._label.setText('\n'.join(text))

  def typingDone(self, run):
    self._prog_layout.cycle()

    for x in run.timed_words():
      # print(x.result())
      pass
    for x in run.timed_ngrams(3):
      # print(x.result())
      pass

    # viscosity = sum([((x-spc)/spc)**2 for x in times]) / chars

    # DB.execute('insert into result (w,text_id,source,wpm,accuracy,viscosity) values (?,?,?,?,?,?)',
    #        (now, self.text[0], self.text[1], 12.0/spc, accuracy, viscosity))

    # v2 = DB.fetchone("""select agg_median(wpm),agg_median(acc) from
    #   (select wpm,100.0*accuracy as acc from result order by w desc limit %d)""" % Settings.get('def_group_by'), (0.0, 100.0))
    # self.result.setText("Last: %.1fwpm (%.1f%%), last 10 average: %.1fwpm (%.1f%%)"
    #   % ((12.0/spc, 100.0*accuracy) + v2))

    # self.statsChanged.emit()

    # stats = collections.defaultdict(Statistic)
    # visc = collections.defaultdict(Statistic)
    # text = self.text[2]

    # for c, t, m in zip(text, times, mis):
    #   stats[c].append(t, m)
    #   visc[c].append(((t-spc)/spc)**2)

    # def gen_tup(s, e):
    #   perch = sum(times[s:e])/(e-s)
    #   visc = sum([((x-perch)/perch)**2 for x in times[s:e]])/(e-s)
    #   return (text[s:e], perch, len([_f for _f in mis[s:e] if _f]), visc)

    # for tri, t, m, v in [gen_tup(i, i+3) for i in range(0, chars-2)]:
    #   stats[tri].append(t, m > 0)
    #   visc[tri].append(v)

    # regex = re.compile(r"(\w|'(?![A-Z]))+(-\w(\w|')*)*")

    # for w, t, m, v in [gen_tup(*x.span()) for x in regex.finditer(text) if x.end()-x.start() > 3]:
    #   stats[w].append(t, m > 0)
    #   visc[w].append(v)

    # def type(k):
    #   if len(k) == 1:
    #     return 0
    #   elif len(k) == 3:
    #     return 1
    #   return 2

    # vals = []
    # for k, s in stats.items():
    #   v = visc[k].median()
    #   vals.append( (s.median(), v*100.0, now, len(s), s.flawed(), type(k), k) )

    # is_lesson = DB.fetchone("select discount from source where rowid=?", (None,), (self.text[1], ))[0]

    # if Settings.get('use_lesson_stats') or not is_lesson:
    #   DB.executemany_('''insert into statistic
    #     (time,viscosity,w,count,mistakes,type,data) values (?,?,?,?,?,?,?)''', vals)
    #   DB.executemany_('insert into mistake (w,target,mistake,count) values (?,?,?,?)',
    #       [(now, k[0], k[1], v) for k, v in mistakes.items()])

    # if is_lesson:
    #   mins = (Settings.get("min_lesson_wpm"), Settings.get("min_lesson_acc"))
    # else:
    #   mins = (Settings.get("min_wpm"), Settings.get("min_acc"))

    # if 12.0/spc < mins[0] or accuracy < mins[1]/100.0:
    #   self.setText(self.text)
    # elif not is_lesson and Settings.get('auto_review'):
    #   ws = [x for x in vals if x[5] == 2]
    #   if len(ws) == 0:
    #     self.wantText.emit()
    #     return
    #   ws.sort(key=lambda x: (x[4],x[0]), reverse=True)
    #   i = 0
    #   while ws[i][4] != 0:
    #     i += 1
    #   i += (len(ws) - i) // 4

    #   self.wantReview.emit([x[6] for x in ws[0:i]])
    # else:
    #   self.wantText.emit()


