"""Per-character typing-run statistics and aggregation helpers.

A `RunStats` is a tuple of `CharEntry` objects (one per character of the
target text) augmented with the typing cursor's `index`, an optional
`started` timestamp from `amphetype.timer`, and helpers for the metrics
the rest of the app reads: per-second speed, fault count, viscosity,
trigram/word slicing, etc.
"""
from __future__ import annotations

import logging as log
import re
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

from amphetype import timer

T = TypeVar("T")


# A `RunStats` is composed of `CharEntry` rows; declaring the forward
# reference as a string keeps the module importable without a cycle and
# lets `RunStats.__class_getitem__` remain implicit.
def median(values: Iterable[float]) -> float | None:
    """Return the median of a non-empty iterable of floats, or `None` if empty."""
    sorted_values = sorted(values)
    n = len(sorted_values)
    if not n:
        return None
    mid = n // 2
    if n % 2:
        return float(sorted_values[mid])
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


class datatuple(tuple[T, ...]):
    """A `tuple` subclass that broadcasts attribute access and fancy indexing."""

    def __getattr__(self, key: str) -> tuple[Any, ...]:
        return tuple(getattr(x, key) for x in self)

    def __getitem__(self, idx: int | slice | tuple[Any, ...] | list[int]) -> Any:
        if isinstance(idx, tuple):
            return type(self)(x for x, cond in zip(self, idx, strict=True) if cond)
        if isinstance(idx, list):
            return type(self)(self[i] for i in idx)
        result = super().__getitem__(idx)
        if isinstance(idx, slice):
            return type(self)(result)
        return result

    def split(self, pred: Callable[[T], bool] | T) -> Iterator[datatuple[T]]:
        """Yield successive groups of items separated by items matching `pred`.

        `pred` may be a unary callable or a sentinel value compared with `==`.
        """
        if not callable(pred):
            sentinel = pred
            pred = lambda x, s=sentinel: x == s  # noqa: E731
        current: list[T] = []
        for item in self:
            if pred(item):
                yield type(self)(current)
                current = []
            else:
                current.append(item)
        yield type(self)(current)


class CharEntry:
    """Per-character state for a single target character during a typing run."""

    __slots__ = ("char", "inserts", "timing", "mistakes", "first", "first_any", "last", "errors")

    char: str
    inserts: int
    timing: float | None
    mistakes: int
    first: float | None
    first_any: float | None
    last: float | None
    errors: str

    def __init__(self, char: str) -> None:
        self.char = char
        self.inserts = 0
        self.first = None
        self.first_any = None
        self.last = None
        self.timing = None
        self.mistakes = 0
        self.errors = ""

    def visited(self) -> bool:
        return self.first is not None

    def visit(self, correct: bool, last_time: float | None) -> None:
        now = timer()
        if self.first_any is None:
            self.first_any = now
        if correct:
            self.last = now
            if self.first is None:
                self.first = now
            if self.timing is None and last_time is not None:
                self.timing = self.first - last_time
        else:
            self.mistakes += 1

    def __repr__(self) -> str:
        return f'["{self.char}"+{self.inserts} {self.timing or -1:.2f}s m:{self.mistakes}]'


class RunStats(datatuple[CharEntry]):
    """A `datatuple` of `CharEntry` plus the live cursor (`index`, `started`)."""

    index: int
    started: float | None

    @staticmethod
    def make(text: str, started: float | None = None) -> RunStats:
        assert len(text) > 0
        run = RunStats(CharEntry(c) for c in text)
        run.started = started
        return run

    def __new__(cls, entries: Iterable[CharEntry]) -> RunStats:
        self = super().__new__(cls, entries)
        idx = 0
        while idx < len(self) and self[idx].last is not None:
            idx += 1
        self.index = idx
        self.started = None
        return self

    def __repr__(self) -> str:
        return "\n".join(
            [
                " ".join(f"{c.char:^5s}" for c in self),
                " ".join(f"{c.timing or -1:5.2f}" for c in self),
            ]
        )

    def is_complete(self) -> bool:
        return self.index >= len(self) and bool(self.previous) and self.previous.last is not None

    def has_started(self) -> bool:
        return self.started is not None

    @property
    def current(self) -> CharEntry | None:
        if self.index >= len(self):
            return None
        return tuple.__getitem__(self, self.index)

    @property
    def previous(self) -> CharEntry | None:
        if self.index == 0:
            return None
        return tuple.__getitem__(self, self.index - 1)

    @property
    def next(self) -> CharEntry | None:
        if self.index >= len(self) - 1:
            return None
        return tuple.__getitem__(self, self.index + 1)

    @property
    def ending(self) -> bool:
        return self.index >= len(self) - 1

    @property
    def start_end(self) -> tuple[float | None, float | None]:
        if not len(self):
            return (None, None)
        return (self.started, tuple.__getitem__(self, -1).last)

    @property
    def text(self) -> str:
        return "".join(c.char for c in self)

    @property
    def duration(self) -> float | None:
        if self.started is None or not self.is_complete():
            return None
        p = self.previous
        return (p.last if p else 0) - (self.started or 0)


    @property
    def per_sec(self) -> float | None:
        if self.duration is None:
            return None
        return len(self) / self.duration

    def __getitem__(self, idx: int | slice) -> RunStats:
        result = super().__getitem__(idx)
        if isinstance(idx, slice):
            s, _, d = idx.indices(len(self))
            assert d > 0
            if s - d == -1:
                result.started = self.started
            elif 0 <= s - d < len(self):
                result.started = tuple.__getitem__(self, s - d).last
        return result

    def last_was_error(self) -> bool:
        if self.current and self.current.inserts > 0:
            return True
        if self.previous and self.previous.last is None:
            return True
        return False

    def pop_char(self) -> str | None:
        if self.current is None or self.current.inserts == 0:
            self.index -= 1
            return self.current.char if self.current is not None else None
        self.current.inserts -= 1
        return None

    def visit(self, correct: bool) -> None:
        if self.previous:
            self.current.visit(correct, self.previous.last)
        else:
            self.current.visit(correct, self.started)

    def advance(self, real: bool = True) -> None:
        if not real:
            self.current.inserts += 1
            return
        self.index += 1
        # Interpolate a reasonable start time if one wasn't set.
        if self.started is None and self.is_complete():
            self.fix_start()

    def fix_start(self) -> None:
        if self.started is not None or not self.is_complete():
            return
        i = 0
        while i < len(self) and tuple.__getitem__(self, i).last is None:
            i += 1
        med = self.median_timing
        if i == len(self) or med is None:
            log.error("cannot fixup broken run, all times are invalid:\n%s", self)
            return
        self.started = tuple.__getitem__(self, i).last - (i + 1) * med

    @property
    def median_timing(self) -> float | None:
        return median(t for t in self.timing if t is not None)

    @property
    def faults(self) -> int:
        return sum(1 for c in self if c.mistakes > 0)

    @property
    def visc(self) -> float | None:
        xs = [t for t in self.timing if t is not None]
        if len(xs) < 3:
            return None
        m = median(xs)
        assert m is not None  # len(xs) >= 3 implies m is not None
        return self.median_err(m)

    def median_err(self, m: float) -> float:
        return sum((max(0.0, x.timing - m)) ** 2 for x in self if x.timing is not None)

    def result(self, accuracy: bool = False) -> tuple[float | None, float | None, float]:
        acc = 1.0 - self.faults / len(self) if accuracy else float(self.faults != 0)
        return (self.per_sec * 12.0 if self.per_sec is not None else None, self.visc, acc)

    @property
    def stats(self) -> tuple[float | None, float | None, bool]:
        return (1.0 / self.per_sec if self.per_sec is not None else None, self.visc, self.faults != 0)

    def timed_ngrams(self, n: int, complete: bool = True) -> Iterator[RunStats]:
        for i in range(n, len(self)):
            gram = self[i - n : i]
            if not complete or gram.is_complete():
                yield gram

    def timed_words(self, complete: bool = True) -> Iterator[RunStats]:
        for m in re.finditer(r"\w+(?:['-]\w+)*", self.text):
            word = self[m.start() : m.end()]
            if len(word) >= 4 and (not complete or word.is_complete()):
                yield word
