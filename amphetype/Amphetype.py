# The order of the code and imports here is important (and a kludge).
# Due to being young and stupid I made the module files do weird
# initialization stuff on import, and some of them depend on each
# other.
import logging as log
import sys

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QKeySequence, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QShortcut, QTabWidget, QTextBrowser
from amphetype import *
from enum import Enum


class OperatingSystem(Enum):
  WINDOWS = "win"
  MAC = "mac"
  LINUX = "linux"
  OTHER = "other"


def _get_os_name() -> OperatingSystem:
  if sys.platform.startswith("win"):
    return OperatingSystem.WINDOWS
  elif sys.platform.startswith("darwin"):
    return OperatingSystem.MAC
  elif sys.platform.startswith("linux"):
    return OperatingSystem.LINUX
  else:
    return OperatingSystem.OTHER


# Init QT and set appname.
class AmphetypeApp(QApplication):
  def __init__(self, *args, **kwargs):
    super().__init__(sys.argv, *args, applicationName="amphetype", **kwargs)


app = AmphetypeApp()

# Import Config.py; this will do argument parsing and set up the
# global var "Settings".
from amphetype.Config import Settings

app.settings = Settings

# Only AFTER settings has been initialized, import database:
from amphetype.Data import DB

app.DB = DB

# After this we can do whatever we want.

from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *

from amphetype.lesson_builder.widget import AdvancedLessonGenerator
from amphetype.Config import GeneralOptions, TyperOptions
from amphetype.fwidgets import FStackedWidget
from amphetype.Lesson import LessonGenerator
from amphetype.Performance import PerformanceHistory
from amphetype.Quizzer import Quizzer
from amphetype.StatWidgets import StringStats
from amphetype.TextManager import TextManager
from amphetype.typer import TyperWindow
from amphetype.Widgets.Database import DatabaseWidget


class AmphetypeWindow(QMainWindow):
  def __init__(self, *args):
    super().__init__(*args)

    self.setWindowTitle("Amphetype")
    self.quitSc = QShortcut(QKeySequence("Ctrl+Q"), self)

    app_instance = QApplication.instance()
    assert (app_instance is not None), "application instance is none"
    self.quitSc.activated.connect(app_instance.quit)

    # Set default font size for the application based on the operating system
    current_os = _get_os_name()

    if current_os is OperatingSystem.WINDOWS:
      default_font = QFont("Segoe UI", 10)
    elif current_os is OperatingSystem.MAC:
      default_font = QFont("Helvetica Neue", 14)
    else:
      default_font = QFont("Arial", 10)

    self.setFont(default_font)

    tabs = QTabWidget()

    quizzer = Quizzer()
    typer = TyperWindow()
    quizzer_typer = FStackedWidget([quizzer, typer])
    tabs.addTab(quizzer_typer, "Typer")
    quizzer_typer.setCurrentIndex(Settings.get("which_typer"))
    Settings.signal_for("which_typer").connect(quizzer_typer.setCurrentIndex)

    text_mgr = TextManager()
    quizzer.wantText.connect(text_mgr.nextText)
    text_mgr.setText.connect(quizzer.setText)
    text_mgr.gotoText.connect(lambda: tabs.setCurrentIndex(0))
    tabs.addTab(text_mgr, "Sources")

    perf_hist = PerformanceHistory()
    text_mgr.refreshSources.connect(perf_hist.refreshSources)
    quizzer.statsChanged.connect(perf_hist.updateData)
    perf_hist.setText.connect(quizzer.setText)
    perf_hist.gotoText.connect(lambda: tabs.setCurrentIndex(0))
    tabs.addTab(perf_hist, "Performance")

    string_stat = StringStats()
    string_stat.lessonStrings.connect(lambda x: tabs.setCurrentIndex(4))
    tabs.addTab(string_stat, "Analysis")

    lesson_gen = LessonGenerator()
    string_stat.lessonStrings.connect(lesson_gen.addStrings)
    lesson_gen.newLessons.connect(lambda: tabs.setCurrentIndex(1))
    lesson_gen.newLessons.connect(text_mgr.addTexts)
    quizzer.wantReview.connect(lesson_gen.wantReview)
    lesson_gen.newReview.connect(text_mgr.newReview)
    tabs.addTab(lesson_gen, "Lesson Generator")

    # advanced_lesson_generator = AdvancedLessonGenerator()
    # tabs.addTab(advanced_lesson_generator, "Advanced Lesson Generator")

    perf_hist.setText.connect(text_mgr.emit_text)
    text_mgr.setText.connect(typer.setText)
    typer.wantText.connect(text_mgr.nextText)
    typer.wantReview.connect(lesson_gen.wantReview)
    typer.statsChanged.connect(perf_hist.updateData)

    db_widget = DatabaseWidget()
    tabs.addTab(db_widget, "Database")

    pw = QTabWidget()
    pw.addTab(GeneralOptions(), "General Options")
    pw.addTab(TyperOptions(), "Typer 2 Options (BETA)")
    tabs.addTab(pw, "Preferences")

    about_widget = AboutWidget()
    tabs.addTab(about_widget, "About/Help")

    self.setCentralWidget(tabs)

    text_mgr.nextText()

  def sizeHint(self):
    return QSize(650, 400)


class AboutWidget(QTextBrowser):
  def __init__(self, *args):
    try:
      about_filepath = Settings.DATA_DIR / "about.html"
      html = about_filepath.open(mode="r", encoding="UTF-8").read()
    except Exception:
      html = "Amphetype v.${VERSION}<br />about.html file missing or could not be loaded!"
    html = html.replace("${VERSION}", __version__)
    super(AboutWidget, self).__init__(*args)
    self.setHtml(html)
    self.setOpenExternalLinks(True)
    # self.setMargin(40)
    self.setReadOnly(True)


def set_qt_css(fname):
  if fname == "<none>":
    app.setStyleSheet("")
  else:
    if Path(fname).is_file():
      with Path(fname).open("r") as f:
        app.setStyleSheet(f.read())
    else:
      log.warning("file not found: %s", fname)


Settings.signal_for("qt_css").connect(set_qt_css)
set_qt_css(Settings.get("qt_css"))

Settings.signal_for("qt_style").connect(app.setStyle)
app.setStyle(Settings.get("qt_style"))
