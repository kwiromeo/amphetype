def main_normal():
  # TODO (Romeo K. 05.13.2025): due to the imports in Amphetype.py
  # it's better to import within the function than at the top of
  # the function. Proceed carefully when editing imports
  import amphetype.Amphetype as A
  import amphetype.Config as S

  w = A.AmphetypeWindow()
  w.show()
  r = A.app.exec_()
  A.DB.commit()
  return r


def main_portable():
  import sys

  sys.argv.append("--local")
  return main_normal()
