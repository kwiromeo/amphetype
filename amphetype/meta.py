
from pathlib import Path

AMPH_DIR = Path(__file__).parent
DATA_DIR = AMPH_DIR / 'data'

with (AMPH_DIR / 'VERSION').open('rt') as f:
  __version__ = f.read().strip()

__all__ = (
  '__version__', # NB! Forced export of __version__.
  'AMPH_DIR',
  'DATA_DIR',
)

