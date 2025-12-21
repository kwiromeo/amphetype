from typing import Optional, List, Iterable
import more_itertools
from pathlib import Path
import re


class LessonExtractor:
  def __init__(self, filepath: str):
    processed_content = self._replace_long_comments(path=filepath)
    stripped_content = self._remove_leading_comments(processed_content)
    self._lines = stripped_content.splitlines()
    self._lessons = None

  @property
  def lines(self) -> Optional[List[str]]:
    return self._lines

  def _replace_long_comments(self, path):
    """
    Reads a Python file, counts the lines in triple-quoted strings,
    and replaces them with 'trimmed comments' if they have 4 or more lines.
    """
    try:
      with open(path, "r", encoding="utf-8") as file:
        content = file.read()

      # Regex explanation:
      # ("""|''') : Captures the opening triple quotes (double or single)
      # (.*?)     : Non-greedy match for the content
      # \1        : Backreference ensures the closing quotes match the opening ones
      pattern = r'("""|\'\'\')(.*?)\1'

      def replacer(match):
        full_match = match.group(0)
        num_lines = len(full_match.splitlines())

        if num_lines <= 3:
          # Keep the original string if it's 3 lines or less
          return full_match
        else:
          # Replace with the specified phrase (wrapped in quotes for valid syntax)
          return '"""trimmed comments"""'

      # re.DOTALL is required to let the '.' match newline characters
      updated_content = re.sub(pattern, replacer, content, flags=re.DOTALL)

      return updated_content

    except FileNotFoundError:
      return "Error: File not found."
    except Exception as e:
      return f"An error occurred: {e}"

  def _remove_leading_comments(self, code_string: str) -> str:
    """
    Removes comments and empty lines from the beginning of a string,
    stopping at the first line of functional code.
    """
    lines = code_string.splitlines()
    first_code_index = 0

    # Iterate through the lines to find the start of the code
    for index, line in enumerate(lines):
      # Strip whitespace to check if the line is empty or a comment
      stripped_line = line.lstrip()

      # If the line is NOT a comment and NOT empty, we found the start
      if stripped_line and not stripped_line.startswith("#"):
        first_code_index = index
        break

    # Join and return only from the first code line onwards
    return "\n".join(lines[first_code_index:])

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
