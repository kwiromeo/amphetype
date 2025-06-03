import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Optional

from . import common_words


class StatisticKind(StrEnum):
  KEY = "key"
  WORD = "word"
  TRIGRAM = "trigam"
  UNKNOWN = "unknown"


@dataclass
class StatisticEntry:
  item: str
  speed: float
  accuracy: float
  viscosity: float
  count: int
  mistakes: int
  impact: int
  kind: StatisticKind


def process_words(words, item_kind, statistic_type) -> Optional[Iterable[StatisticEntry]]:
  if not words:
    return None

  stat_entries = list()
  for word in words:
    stat_entry = StatisticEntry(
      item=word[0],
      speed=word[1],
      accuracy=word[2],
      viscosity=word[3],
      count=word[4],
      mistakes=word[5],
      impact=word[6],
      kind=StatisticKind.KEY,
    )
    stat_entries.append(stat_entry)

  return stat_entries


def determine_statistic_kind(stat_kind_str: str) -> StatisticKind:
  if stat_kind_str == str(StatisticKind.KEY):
    return StatisticKind.KEY

  if stat_kind_str == str(StatisticKind.TRIGRAM):
    return StatisticKind.TRIGRAM

  if stat_kind_str == str(StatisticKind.WORD):
    return StatisticKind.WORD

  return StatisticKind.UNKNOWN


def create_lesson(issues_list, item_kind, statistic_type) -> Iterable[str]:
  """
  `create_lesson` takes in the issues listed in the statistic widget and returns a customized
  list of words to work on improving typing speed
  """

  if issues_list is None:
    return []

  # get list of statistics
  stat_entries = process_words(words=issues_list, item_kind=item_kind, statistic_type=statistic_type)

  # sort statistics by viscosity
  def get_viscosity(entry: StatisticEntry):
    return entry.viscosity

  sorted_stat_entries = sorted(stat_entries, key=get_viscosity)

  return _create_lesson_for_trigrams(stat_entries=sorted_stat_entries)


def _create_lesson_for_keys(issues_list, item_kind, statistic_type) -> Iterable[str]:
  pass


def _create_lesson_for_trigrams(stat_entries: Iterable[StatisticEntry]) -> Iterable[str]:
  # get source words
  short_words = common_words.get_short_words()
  # newlist = [expression for item in iterable if condition == True]
  medium_words = [word for word in common_words.get_medium_words() if len(word) <= 7]

  source_list = []
  source_list.extend(short_words)
  source_list.extend(medium_words)

  # find words that contains the most key/trigrams/words
  found_matches = dict()

  for entry in stat_entries:
    query = entry.item.strip().lower()
    for word in source_list:
      if query in word:
        query_matches = found_matches.get(query)

        # if there are no entries for the query at this time, create a list with the first entry
        if query_matches is None:
          found_matches[query] = [word]
        else:
          query_matches.append(word)

  # create custom sentences/lessons from the matches
  lesson_words_set = set()
  for _, match_list in found_matches.items():
    lesson_words_set.update(match_list)

  lesson_words = list(lesson_words_set)

  random.shuffle(lesson_words)

  return lesson_words


def _create_lesson_for_words(issues_list, item_kind, statistic_type) -> Iterable[str]:
  pass
