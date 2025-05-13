from amphetype import AmphetypeWindow, app, DB
import sys


def main_normal():
    w = AmphetypeWindow()
    w.show()
    r = app.exec_()
    DB.commit()
    return r


def main_portable():
    sys.argv.append("--local")
    return main_normal()
