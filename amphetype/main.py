def main_normal():
  # in-function import: main_portable() appends --local to sys.argv before
  # the package parses CLI options, so the import must stay inside the call.
  import amphetype.Amphetype as A

  A.bootstrap()
  w = A.AmphetypeWindow()
  w.show()
  r = A.app.exec_()
  A.app.DB.commit()
  return r


def main_portable():
  import sys

  sys.argv.append("--local")
  return main_normal()


if __name__ == "__main__":
  main_normal()
