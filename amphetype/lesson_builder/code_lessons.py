from typing import Optional, List, Iterable
import more_itertools
from pathlib import Path
import re


class LessonExtractor:
  def __init__(self, filepath: str):
    processed_content = self._replace_triple_quotes(path=filepath)
    self._lines = processed_content.splitlines()
    self._lessons = None

  @property
  def lines(self) -> Optional[List[str]]:
    return self._lines

  def _replace_triple_quotes(self, path) -> str:
    """
    Reads a Python file and replaces all triple-quoted strings
    with the phrase `comment trimmed`.
    """
    try:
      with open(path, "r", encoding="utf-8") as file:
        content = file.read()

      # Regex explanation:
      # (?:"""|''') : Non-capturing group for triple double or single quotes
      # (.*?)       : Non-greedy match for any characters (including newlines via DOTALL)
      # (?:"""|''') : Closing triple quotes
      pattern = r'(?:"""|\'\'\')(.*?)(?:"""|\'\'\')'

      # We use flags=re.DOTALL so that the '.' matches newlines
      replaced_comment_msg = '"""comment trimmed"""'
      updated_content = re.sub(pattern, replaced_comment_msg, content, flags=re.DOTALL)

      return updated_content

    except FileNotFoundError:
      return "Error: The file was not found."
    except Exception as e:
      return f"An error occurred: {e}"

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
      lesson = "\n".join(trimmed_lesson)
      found_lessons.append(lesson)
    return found_lessons

  def get_lessons(self) -> Optional[Iterable]:
    lessons = self._create_lessons()
    if lessons is None:
      return None

    return list(lessons)


def create_id_from_path(filepath: str):
  path_parts = Path(filepath).parts

  assert len(path_parts) >= 2, "path is too short to create a lesson id"
  code_lesson_id = f"{path_parts[-2]}::{path_parts[-1]}"
  return code_lesson_id
