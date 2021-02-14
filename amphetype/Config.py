

import pickle
from amphetype.QtUtil import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import getpass
import os
import re
from pathlib import Path
from amphetype.meta import *


# First of all parse argument for setting file location.
import argparse

parser = argparse.ArgumentParser(description="Advanced type training program.")
parser.add_argument('-l', '--local', action='store_true',
                    help=f"""uses the local data directory ({DATA_DIR}) for database and
                    settings. Useful for running a "portable" instance that stores all
                    files locally instead of in user home directory.""")
parser.add_argument('-d', '--database', metavar='DBFILE',
                    help='uses the database file %(metavar)s')
parser.add_argument('-s', '--settings', metavar='INIFILE',
                    help="uses settings file %(metavar)s")
parser.add_argument('-V', '--version', action='version', version=f'amphetype {__version__}')

# parse_known_args() because there might be QT arguments?
cliopts, _ = parser.parse_known_args()




def get_default_db_name():
  "Default database name is based on username."

  try:
    _user = getpass.getuser() or 'user'
  except: # Docs just say "otherwise, an exception is raised."
    _user = 'user'

  _user = re.sub('[^a-z0-9_-]', '', _user, flags=re.I) or 'user'
  return _user + '.db'


class SettingsMeta(type(QObject)):
  def __new__(cls, name, bases, ns):
    for k,v in ns['defaults'].items():
      ns['change_' + k] = pyqtSignal([type(v)])
    return super().__new__(cls, name, bases, ns)


class AmphSettings(QSettings, metaclass=SettingsMeta):
  change = pyqtSignal()
  DATA_DIR = DATA_DIR

  # Whenever types need to be checked on settings it will use the
  # types provided here, so always set a default of the type the
  # setting will have.
  defaults = {
    "typer_font": str(QFont("Arial", 14).toString()),
    "qt_style": "", # Will be set in __init__().
    "qt_css": "<none>",

    "text_force_ascii": False,
    
    "history": 30.0,
    "min_chars": 220,
    "max_chars": 600,
    "lesson_stats": 0, # show text/lesson in perf -- not used anymore
    "perf_group_by": 0,
    "perf_items": 100,
    "text_regex": r"",
    "db_name": '', # Will be set in __init__().
    "select_method": 0,
    "num_rand": 50,
    "graph_what": 3,
    "req_space": True,
    "show_last": True,
    "show_xaxis": False,
    "chrono_x": False,
    "dampen_graph": False,

    "minutes_in_sitting": 60.0,
    "dampen_average": 10,
    "def_group_by": 10,

    "use_lesson_stats": False,
    "auto_review": False,

    "min_wpm": 0.0,
    "min_acc": 0.0,
    "min_lesson_wpm": 0.0,
    "min_lesson_acc": 97.0,

    "quiz_right_fg": "#000000",
    "quiz_right_bg": "#ffffff",
    "quiz_wrong_fg": "#ffffff",
    "quiz_wrong_bg": "#000000",
    
    "group_month": 365.0,
    "group_week": 30.0,
    "group_day": 7.0,

    "ana_which": "wpm asc",
    "ana_what": 0,
    "ana_many": 30,
    "ana_count": 1,

    "gen_copies": 3,
    "gen_take": 2,
    "gen_mix": 'c',
    #"gen_stats": False,
    "str_clear": 's',
    "str_extra": 10,
    "str_what": 'e'
  }

  def __init__(self, *args):
    if cliopts.settings:
      super().__init__(cliopts.settings, QSettings.IniFormat)
    elif cliopts.local:
      super().__init__(str(DATA_DIR / 'amphetype.ini'), QSettings.IniFormat)
    else:
      super().__init__(QSettings.IniFormat, QSettings.UserScope, "amphetype", "amphetype")

    # Set some runtime defaults here.

    if cliopts.database:
      _dbname = cliopts.database
    elif cliopts.local:
      _dbname = str(DATA_DIR / get_default_db_name())
    else:
      pth = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
      if pth:
        pth = Path(pth)
        pth.mkdir(parents=True, exist_ok=True)
      else:
        pth = DATA_DIR
      _dbname = str(pth / get_default_db_name())
    
    self.defaults['db_name'] = _dbname

    assert QApplication.instance()
    self.defaults['qt_style'] = QApplication.instance().style().objectName().lower()

  def get(self, k):
    return self.value(k, self.defaults[k], type=type(self.defaults[k]))

  def getFont(self, k):
    qf = QFont()
    qf.fromString(self.get(k))
    return qf

  def getColor(self, k):
    return QColor(self.get(k))

  def set(self, k, v):
    p = self.get(k)
    if p == v:
      return
    w = v
    if isinstance(v, QColor):
      w = v.name()
    elif isinstance(v, QFont):
      w = str(v)
    self.setValue(k, v)
    self.change.emit()
    self.signal_for(k).emit(v)

  def signal_for(self, k):
    return getattr(self, 'change_' + k)




class SettingsColor(AmphButton):
  def __init__(self, key, text):
    self.key_ = key
    super(SettingsColor, self).__init__(Settings.get(key), self.pickColor)
    self.updateIcon()

  def pickColor(self):
    color = QColorDialog.getColor(Settings.getColor(self.key_), self)
    if not color.isValid():
      return
    Settings.set(self.key_, str(color.name()))
    self.updateIcon()

  def updateIcon(self):
    pix = QPixmap(32, 32)
    c = Settings.getColor(self.key_)
    pix.fill(c)
    self.setText(Settings.get(self.key_))
    self.setIcon(QIcon(pix))



# TODO: XXX. Perhaps input and format numbers in locale? Possible
# problems: innumerable. Many (I, for one) will probably want to input
# things as if in plain C locale and be annoyed if their Uruk-hai
# locale interferes/invalidates their input. Would be a misfeature
# until locale-switching is also in place.

# Unrelated: "I am writing a class to represent money, and one issue
# I've been running into is that "1.50" != str(1.50). str(1.50) equals
# 1.5, and all of a sudden, POOF. 45 cents have vanished and the
# amount is now 1 dollar and 5 cents." -StackOverflow user.

# LOCALE = QLocale()

# def float_to_string(val):
#   if round(val, 6) == int(val):
#     return LOCALE.toString(val, precision=1)
#   else:
#     return LOCALE.toString(val)

# def SettingsEdit(setting):
#   "Suitable QLineEdit() for given type and implied locale"
#   val = Settings.get(setting)
#   if isinstance(val, float):
#     pass
#   elif isinstance(val, int):
#     pass
#   else:
#     pass

# Set validators, QDoubleValidator, QIntValidator?

class SettingsEdit(AmphEdit):
  def __init__(self, setting):
    val = Settings.get(setting)
    self.setting = setting
    if isinstance(val, float):
      self.fmt = lambda x: str(round(x, 6))
      self.conv = float
    elif isinstance(val, int):
      self.fmt = str
      self.conv = int
    elif isinstance(val, str):
      self.fmt = lambda x: x
      self.conv = lambda x: x
    else:
      raise RuntimeError(f"instantiated with unknown type {type(val)}")

    super(SettingsEdit, self).__init__(self.fmt(val), self.updateVal)
    Settings.signal_for(setting).connect(lambda x: self.setText(self.fmt(x)))

  def updateVal(self):
    try:
      v = self.conv(self.text())
    except ValueError as err:
      QMessageBox.warning(self, "String Conversion Error", f"Couldn't convert setting value:\n{err}")
    else:
      Settings.set(self.setting, v)

class SettingsCombo(QComboBox):
  def __init__(self, setting, lst, *args):
    super(SettingsCombo, self).__init__(*args)

    prev = Settings.get(setting)
    self.idx2item = []
    for i in range(len(lst)):
      if isinstance(lst[i], str):
        # not a tuple, use index as key
        k, v = i, lst[i]
      else:
        k, v = lst[i]
      self.addItem(v)
      self.idx2item.append(k)
      if k == prev:
        self.setCurrentIndex(i)

    self.activated[int].connect(lambda x: Settings.set(setting, self.idx2item[x]))

    #self.connect(Settings, SIGNAL("change_" + setting),
    #      lambda x: self.setCurrentIndex(self.item2idx[x]))

class SettingsCheckBox(QCheckBox):
  def __init__(self, setting, *args):
    super(SettingsCheckBox, self).__init__(*args)
    self.setCheckState(Qt.Checked if Settings.get(setting) else Qt.Unchecked)
    self.stateChanged[int].connect(lambda x: Settings.set(setting, True if x == Qt.Checked else False))


def find_css_files():
  # XXX: cleanup / make consistent.
  places = [
    QStandardPaths.AppLocalDataLocation,
    QStandardPaths.AppDataLocation,
    QStandardPaths.AppConfigLocation,
    Settings.DATA_DIR / 'css',
  ]
  res = set()
  for p in places:
    if not isinstance(p, Path):
      pth = QStandardPaths.locate(p, 'css', QStandardPaths.LocateDirectory)
      if not pth:
        continue
      p = Path(pth)
    # print(f"scanning dir {p}")
    for f in list(p.glob('*.qss')) + list(p.glob('*.stylesheet')) + list(p.glob('*.css')):
      res.add(str(f))

  return set(res)
 


class SelectCSSBox(QComboBox):
  def __init__(self, *args):
    super().__init__(*args)

    Settings.signal_for('qt_css').connect(self.refresh)
    self.activated[int].connect(self.setIdx)
    self.refresh()

  def setIdx(self, idx):
    if idx == 0:
      Settings.set('qt_css', '<none>')
    elif idx <= len(self._files):
      Settings.set('qt_css', self._files[idx-1])
    else:
      # <select file>
      qf = QFileDialog(self, "Select CSS Theme")
      qf.setNameFilters(["QT CSS stylesheet (*.qss *.css *.stylesheet)", "All files (*)"])
      qf.setFileMode(QFileDialog.ExistingFile)
      qf.setAcceptMode(QFileDialog.AcceptOpen)
      qf.fileSelected['QString'].connect(self.setCustomCSS)
      qf.show()

  def setCustomCSS(self, fname):
    Settings.set('qt_css', fname)

  def refresh(self):
    cur = Settings.get('qt_css')
    _files = find_css_files()
    if cur not in _files and cur != '<none>':
      _files.add(cur)
    self._files = sorted(_files)
    
    self.clear()
    self.addItem('<none>')
    self.setCurrentIndex(0)
    for i,v in enumerate(self._files):
      self.addItem(v)
      if v == cur:
        self.setCurrentIndex(i+1)
    self.addItem('<select file...>')


class PreferenceWidget(QWidget):
  def __init__(self):
    super(PreferenceWidget, self).__init__()

    self.font_lbl = QLabel()

    self.style_box = SettingsCombo('qt_style', [(x.lower(), x.lower()) for x in QStyleFactory.keys()])

    self.setLayout(AmphBoxLayout([
      ["Typer font is", self.font_lbl, AmphButton("Change...", self.setFont), None],
      ["QT5 style is", self.style_box, 'and CSS theme is', SelectCSSBox(), None],
      None,

      [SettingsCheckBox("text_force_ascii", 'Force unicode to plain ASCII'), ('(‘fancy’ “quotes” → "normal" quotes, <code>æ</code> → <code>ae</code>, etc.)', 1)],
      [SettingsCheckBox('auto_review', "Automatically review slow and mistyped words after texts."),
        ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
      SettingsCheckBox('show_last', "Show last result(s) above text in the Typer."),
      SettingsCheckBox('use_lesson_stats', "Save key/trigram/word statistics from generated lessons."),
      [SettingsCheckBox('req_space', "Make SPACE mandatory before each session"),
        ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
      None,
      [AmphGridLayout([
        ["INPUT COLORS", "Text Color", "Background"],
        ["Correct Input", SettingsColor('quiz_right_fg', "Foreground"),
            SettingsColor('quiz_right_bg', "Background")],
        ["Wrong Input", SettingsColor('quiz_wrong_fg', "Foreground"),
            SettingsColor('quiz_wrong_bg', "Background")],
        [1+1j,1+2j,2+1j,2+2j]
      ]), None],
      None,
      ["Data is considered too old to be included in analysis after",
        SettingsEdit("history"), "days.", None],
      ["Try to limit texts and lessons to between", SettingsEdit("min_chars"),
        "and", SettingsEdit("max_chars"), "characters.", None],
      ["When selecting easy/difficult texts, scan a sample of",
        SettingsEdit('num_rand'), "texts.", None],
      ["When grouping by sitting on the Performance tab, consider results more than",
        SettingsEdit('minutes_in_sitting'), "minutes away to be part of a different sitting.", None],
      ["Group by", SettingsEdit('def_group_by'), "results when displaying last scores and showing last results on the Typer tab.", None],
      ["When smoothing out the graph, display a running average of", SettingsEdit('dampen_average'), "values", None]
    ]))

    self.updateFont()

  def setFont(self):
    font, ok = QFontDialog.getFont(Settings.getFont('typer_font'), self)
    Settings.set("typer_font", str(font.toString()))
    self.updateFont()

  def updateFont(self):
    self.font_lbl.setText(Settings.get("typer_font"))
    qf = Settings.getFont('typer_font')
    self.font_lbl.setFont(qf)



Settings = AmphSettings()

