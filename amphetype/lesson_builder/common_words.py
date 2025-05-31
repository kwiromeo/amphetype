import os
from typing import Iterable


def get_short_words() -> Iterable[str]:
  filepath = os.path.join(os.path.dirname(__file__), "google_10000_short_words.txt")
  with open(file=filepath, mode="r", encoding="utf-8") as file:
    found_words = [line.strip() for line in file]
  return found_words


def get_medium_words() -> Iterable[str]:
  filepath = os.path.join(os.path.dirname(__file__), "google_10000_medium_words.txt")
  with open(file=filepath, mode="r", encoding="utf-8") as file:
    found_words = [line.strip() for line in file]
  return found_words
