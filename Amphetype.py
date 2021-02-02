
from PyQt5.QtWidgets import *
import sys

# Do this first of all.
app = QApplication(sys.argv)
app.setApplicationName('amphetype')

# Set up logging.
import logging as log
log.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


import os

# Get command-line --database argument before importing
# modules which count on database support
from Config import Settings

import optparse
opts = optparse.OptionParser()
opts.add_option("-d", "--database", metavar="FILE", help="use database FILE")
v = opts.parse_args()[0]

if v.database is not None:
  Settings.set('db_name', v.database)

from Data import DB
from Quizzer import Quizzer
from StatWidgets import StringStats
from TextManager import TextManager
from Performance import PerformanceHistory
from Config import PreferenceWidget
from Lesson import LessonGenerator
from Widgets.Database import DatabaseWidget

from PyQt5.QtCore import *
from PyQt5.QtGui import *


QApplication.setStyle('cleanlooks')


class TyperWindow(QMainWindow):
  def __init__(self, *args):
    super(TyperWindow, self).__init__(*args)

    self.setWindowTitle("Amphetype")

    self.quitSc = QShortcut(QKeySequence('Ctrl+Q'), self)
    self.quitSc.activated.connect(QApplication.instance().quit)
    
    tabs = QTabWidget()

    quiz = Quizzer()
    tabs.addTab(quiz, "Typer")

    tm = TextManager()
    quiz.wantText.connect(tm.nextText)
    tm.setText.connect(quiz.setText)
    tm.gotoText.connect(lambda: tabs.setCurrentIndex(0))
    tabs.addTab(tm, "Sources")

    ph = PerformanceHistory()
    tm.refreshSources.connect(ph.refreshSources)
    quiz.statsChanged.connect(ph.updateData)
    ph.setText.connect(quiz.setText)
    ph.gotoText.connect(lambda: tabs.setCurrentIndex(0))
    tabs.addTab(ph, "Performance")

    st = StringStats()
    st.lessonStrings.connect(lambda x: tabs.setCurrentIndex(4))
    tabs.addTab(st, "Analysis")

    lg = LessonGenerator()
    st.lessonStrings.connect(lg.addStrings)
    lg.newLessons.connect(lambda: tabs.setCurrentIndex(1))
    lg.newLessons.connect(tm.addTexts)
    quiz.wantReview.connect(lg.wantReview)
    lg.newReview.connect(tm.newReview)
    tabs.addTab(lg, "Lesson Generator")

    dw = DatabaseWidget()
    tabs.addTab(dw, "Database")

    pw = PreferenceWidget()
    tabs.addTab(pw, "Preferences")

    ab = AboutWidget()
    tabs.addTab(ab, "About/Help")

    self.setCentralWidget(tabs)

    tm.nextText()

  def sizeHint(self):
    return QSize(650, 400)

class AboutWidget(QTextBrowser):
  def __init__(self, *args):
    html = "about.html file missing!"
    try:
      html = open("about.html", "r").read()
    except:
      pass
    super(AboutWidget, self).__init__(*args)
    self.setHtml(html)
    self.setOpenExternalLinks(True)
    #self.setMargin(40)
    self.setReadOnly(True)


_default_style = app.style()
def set_theme(thm):
  app.setStyle('doesntexist')
  app.setStyleSheet('')
  if thm == '<default>':
    pass
  elif thm.startswith('QT:'):
    app.setStyle(thm[3:])
  elif thm.startswith('CSS:'):
    with open(thm[4:], 'r') as f:
      app.setStyleSheet(f.read())
  else:
    log.warn("Unknown style: %s", thm)
      
Settings.signal_for('qt_theme').connect(set_theme)
set_theme(Settings.get('qt_theme'))

w = TyperWindow()

w.show()

app.exec_()

print("exit")
DB.commit()


