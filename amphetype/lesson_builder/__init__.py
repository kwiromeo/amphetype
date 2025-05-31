from dataclasses import dataclass
from enum import StrEnum


class ItemKind(StrEnum):
  KEY = "key"
  WORD = "word"
  TRIGRAM = "trigam"


# ["Item", "Speed", "Accuracy", "Viscosity", "Count", "Mistakes", "Impact"]
# ['cti', 8.784638188611064, 0.0, 1271.3593084907586, 1, 1, 3.7320265937071344]
@dataclass
class ItemStatistic:
  item: str
  speed: float
  accuracy: float
  viscosity: float
  count: int
  mistakes: int
  impact: int
  kind: ItemKind


def process_words(words, item_kind, statistic_type) -> None:
  print(f"item kind: {item_kind}")
  print(f"statistic_type: {statistic_type}")
  for word in words:
    problem_item = ItemStatistic(
      item=word[0],
      speed=word[1],
      accuracy=word[2],
      viscosity=word[3],
      count=word[4],
      mistakes=word[5],
      impact=word[6],
      kind=ItemKind.KEY,
    )

    print(problem_item)
