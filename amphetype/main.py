def main_normal():
  # in-function import: see AGENTS.md#imports
  import amphetype.Amphetype as A

  w = A.AmphetypeWindow()
  w.show()
  r = A.app.exec_()
  A.DB.commit()
  return r


def main_portable():
  import sys

  sys.argv.append("--local")
  return main_normal()


if __name__ == "__main__":
  main_normal()
