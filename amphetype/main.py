

def main_normal():
  import amphetype.Amphetype as A
  import amphetype.Config as S
  
  w = A.AmphetypeWindow()
  w.show()
  r = A.app.exec_()
  A.DB.commit()
  return r


def main_portable():
  import sys
  sys.argv.append('--local')
  return main_normal()
  
