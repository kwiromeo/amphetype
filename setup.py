
# from distutils.core import setup
# import py2exe

# setup(
#       windows=[{"script" : "Amphetype.py"}],
#         options={"py2exe" :
#             {"includes" : ["sip"],
#             "dist_dir": "Amphetype"}},
#         data_files=[('txt', glob.glob('txt/*.txt')),
#             ('', ['about.html', "gpl.txt"]),
#             ('txt/wordlists', glob.glob('txt/wordlists/*.txt'))]
#     )

from setuptools import setup
from glob import glob
from pathlib import Path
import sys


setup(
  name='amphetype',
  description='advanced typing practice tool',
  version='0.9.0',
  long_description=open('README.md', 'r').read(),
  url='https://gitlab.com/franksh/amphetype',
  author='Frank S. Hestvik',
  author_email='tristesse@gmail.com',
  license='GPL3',
  packages=['amphetype', 'amphetype.Widgets'],
  install_requires=['PyQt5', 'translitcodec', 'editdistance'],
  # include_package_data=True,
  entry_points={
    'gui_scripts': ['amphetype = amphetype:main'],
  },
  package_data={
    "amphetype": [
      "data/texts/*.txt",
      "data/css/*.qss",
      "data/about.html",
      "data/wordlists/*.txt"
    ],
  },
  # include_package_data=True,
  # install_requires=['appdirs'],
  # data_files=[
  #   ('amphetype', [x for x in glob('data/**/*', recursive=True) if Path(x).is_file()]),
  # ],
)

