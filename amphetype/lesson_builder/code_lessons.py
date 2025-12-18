from typing import Optional, List, Iterable
import more_itertools
from pathlib import Path


class LessonExtractor:
  def __init__(self, filepath: str):
    self._lines = None
    with open(file=filepath, mode="r", encoding="utf_8_sig") as file:
      self._lines = file.readlines()

    self._lessons = None

  @property
  def lines(self) -> Optional[List[str]]:
    return self._lines

  def _trim_prefix_space(self, lines: List[str]) -> List[str]:
    space_length = []

    for line in lines:
      full_length = len(line)
      trimmed_length = len(line.lstrip())
      diff = full_length - trimmed_length
      space_length.append(diff)

    shortest = min(space_length)

    trimmed_lines = []
    for line in lines:
      updated_line = line[shortest:]
      trimmed_lines.append(updated_line)

    return trimmed_lines

  def _create_lessons(self) -> Optional[Iterable[str]]:
    if not self._lines:
      return None

    found_split = more_itertools.split_at(self._lines, lambda x: x.strip() == "")

    found_lessons = []
    for split in found_split:
      if len(split) == 0:
        continue

      trimmed_lesson = self._trim_prefix_space(split)
      lesson = "".join(trimmed_lesson)
      found_lessons.append(lesson)
    return found_lessons

  def get_lessons(self) -> Optional[Iterable]:
    lessons = self._create_lessons()
    if lessons is None:
      return None

    return list(lessons)


def create_id_from_path(filepath: str):
  path_parts = Path(filepath).parts

  assert len(path_parts) >= 2, "path is too short to create pseudo part"
  pseudo_path = f"{path_parts[-2]}::{path_parts[-1]}"
  return pseudo_path
