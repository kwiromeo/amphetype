# Amphetype Code Review — Possible Improvements

**Date:** 2026-07-10
**Scope:** Full codebase review of `amphetype/`, `tests/`, `_scripts/`, and project configuration.
**Method:** Four parallel read-only review agents covered: (1) core data/text modules, (2) GUI/widgets, (3) settings/text-management/lessons, (4) stats/tests/tooling. Findings were cross-referenced with direct file reads and PyQt5 best-practices research. No code was modified.

**Summary:** 67 findings across 7 themes. 6 High severity, 26 Medium, 35 Low.

---

## Table of Contents

1. [Correctness](#1-correctness)
2. [Performance](#2-performance)
3. [Error Handling](#3-error-handling)
4. [Maintainability](#4-maintainability)
5. [Design](#5-design)
6. [Testing](#6-testing)
7. [CI / Tooling](#7-ci--tooling)

---

## 1. Correctness

### C1. TextManager.nextText references non-existent `self.diff_eval` attribute — AttributeError on Difficult/Easy mode

- **Location:** `amphetype/TextManager.py:464, 466`
- **Evidence:** `text_record = min(text_records, key=self.diff_eval)` and `text_record = max(text_records, key=self.diff_eval)`. The attribute is set as `self.difficulty_evaluator` (lines 106, 282, 320) — there is no `self.diff_eval`. When `select_method` is 2 (Difficult) or 3 (Easy), this raises `AttributeError`.
- **Suggestion:** Rename to `self.diff_eval` consistently or change call sites to `self.difficulty_evaluator`.
- **Severity:** High

### C2. TextManager.nextText references undefined `self.defaultText` — AttributeError when no text found

- **Location:** `amphetype/TextManager.py:489`
- **Evidence:** `text_record = self.defaultText` — no `defaultText` attribute exists on `TextManager` or any base class. The class defines `empty_db_placeholder` (line 97-101) as a class-level tuple. When all selection strategies return None (empty database or all texts disabled), this crashes.
- **Suggestion:** Change `self.defaultText` to `self.empty_db_placeholder`.
- **Severity:** High

### C3. `_set_select` returns a lambda instead of assigning the difficulty evaluator

- **Location:** `amphetype/TextManager.py:298-299`
- **Evidence:** `if len(wpm_values) == 0: return lambda x: 1`. This is a signal handler (connected at line 133), so the return value is discarded. The `difficulty_evaluator` is never set in the empty-statistics case, leaving it as the initial `lambda x: 1`. The early return also skips `self.nextText()` (line 321), so the text doesn't refresh when switching to Difficult/Easy mode with no history.
- **Suggestion:** Replace `return lambda x: 1` with `self.difficulty_evaluator = lambda x: 1; self.nextText(); return`.
- **Severity:** Medium

### C4. `calc_text_difficulty` divides by zero for texts with ≤2 characters

- **Location:** `amphetype/TextManager.py:314`
- **Evidence:** `average_wpm = total_wpm / (len(text_content) - 2)`. If `text_content` has 0, 1, or 2 characters, the denominator is ≤0. Short texts (e.g., review lessons of a few characters) trigger `ZeroDivisionError` or produce nonsensical negative WPM.
- **Suggestion:** Guard: `if len(text_content) <= 2: return 1.0` before the division.
- **Severity:** Medium

### C5. `lesson_builder.create_lesson` always calls trigram lesson generator regardless of `item_kind`

- **Location:** `amphetype/lesson_builder/__init__.py:80`
- **Evidence:** `return _create_lesson_for_trigrams(stat_entries=sorted_stat_entries)` — the `item_kind` and `statistic_type` parameters are accepted but never dispatched on. `_create_lesson_for_keys` (line 83) and `_create_lesson_for_words` (line 124) are defined but never called. Users selecting "keys" or "words" in the statistics widget always get a trigram-based lesson.
- **Suggestion:** Add `if item_kind == StatisticKind.KEY: return _create_lesson_for_keys(...)` dispatch logic.
- **Severity:** High

### C6. `random.sample` with fixed k=150 crashes when source word pool is smaller

- **Location:** `amphetype/lesson_builder/__init__.py:119`
- **Evidence:** `lesson_words = random.sample(population=source_words, k=150)`. If fewer than 150 words match the trigrams, `random.sample` raises `ValueError: Sample larger than population`.
- **Suggestion:** `k = min(150, len(source_words))` before calling `random.sample`.
- **Severity:** Medium

### C7. Quizzer `log.warning` crashes — `log` is the `logging.log` function, not the module

- **Location:** `amphetype/Quizzer.py:4` (import) and `:236` (call)
- **Evidence:** `from logging import log` binds the function `logging.log(level, msg, ...)`. Line 236 calls `log.warning(f"timing for span ({s},{e}) summed to zero...")`. The `logging.log` function object has no `.warning` attribute → `AttributeError`. This fires in the exact situation the code warns about (near-zero timing span), turning a logged warning into an unhandled exception. `typer.py:1` correctly uses `import logging as log`.
- **Suggestion:** Change `Quizzer.py:4` to `import logging as log`, matching `typer.py`.
- **Severity:** Medium

### C8. Quizzer review-selection loop can index out of bounds

- **Location:** `amphetype/Quizzer.py:300-303`
- **Evidence:** `while ws[i][4] != 0: i += 1` — if every word in `ws` has a nonzero mistake count, the loop increments `i` past `len(ws)` → `IndexError`. Reached when `auto_review` is on and the user missed at least one word in every reviewed word. The newer `typer.py:687-694` fixed this with `u = sum(x[4] != 0 for x in ws)` + slice.
- **Suggestion:** Port the `typer.py` fix: `u = sum(x[4] != 0 for x in ws); u += (len(ws) - u) // 4; self.wantReview.emit([x[6] for x in ws[:u]])`.
- **Severity:** Medium

### C9. `_env_true` treats "no", "false", "off" as truthy

- **Location:** `amphetype/__init__.py:24-29`
- **Evidence:** `_env_true` returns `True` for any non-empty non-digit string. `AMPH_LOCAL=no`, `AMPH_LOCAL=false`, `AMPH_LOCAL=off` all enable local mode (used at line 67). Only `0`, `""`, and digit strings evaluate to False.
- **Suggestion:** Compare against an explicit falsy set: `return value.lower() not in {'', '0', 'no', 'false', 'off'}`.
- **Severity:** Medium

### C10. `regex_match` SQLite function crashes on NULL column values

- **Location:** `amphetype/Data.py:147-150`
- **Evidence:** `match()` does `self.regex_.search(x)` with `x` possibly `None` (SQLite NULL). `re.search(None)` raises `TypeError`. Used against `text` column in `TextManager.py:527, 532` — if any text row has a NULL text value, `executemany` fails.
- **Suggestion:** Guard: `if x is None: return 0` before `search`.
- **Severity:** Medium

### C11. `abbreviate` mishandles n < 3

- **Location:** `amphetype/Data.py:144-145`
- **Evidence:** `x[:n-3] + '...'` for `n==2` yields `x[:-1] + '...'` (longer than original). For `n==0` yields `x[:-3]`. Latent — sole caller uses `n=30`, but the function is a registered SQL function callable from any query.
- **Suggestion:** When `n < 3`, return `x[:n]` (hard truncate without ellipsis).
- **Severity:** Low

### C12. SentenceSplitter regex treats non-ASCII lowercase as sentence starts

- **Location:** `amphetype/Text.py:34`
- **Evidence:** The lookahead `(?= +(?:[^ a-z]|$))` uses ASCII-only `a-z`. Non-ASCII lowercase like `ê`, `é`, `ñ` satisfies `[^ a-z]`, so `"le chien. être"` splits at `"chien."` though `"être"` is lowercase. Affects French, Spanish, Portuguese, German (ß), etc.
- **Suggestion:** Use a Unicode-aware class (`[^\s a-zà-ÿ]` or `(?=\s+[A-ZÀ-ÝÜ])`), or test `not str.islower()` on the next word's first character outside the regex.
- **Severity:** Medium

### C13. LessonMiner.doIt divides by zero on empty input

- **Location:** `amphetype/Text.py:81`
- **Evidence:** `int(100 * i / len(self.paras))` with `self.paras` possibly `[]` for empty/whitespace-only file → `ZeroDivisionError`.
- **Suggestion:** Guard: `if not self.paras: return` before the loop.
- **Severity:** Low

### C14. CharEntry/RunStats `__repr__` display 0.0s timing as -1.0

- **Location:** `amphetype/timingtuple.py:111, 140`
- **Evidence:** `f'{self.timing or -1:.2f}'` — `timing == 0.0` is falsy, renders as `-1.00`, masking a real zero-duration keystroke. Misleading in debug output.
- **Suggestion:** Use `self.timing if self.timing is not None else -1`.
- **Severity:** Low

### C15. RunStats.**getitem** asserts positive slice step — stripped under `python -O`

- **Location:** `amphetype/timingtuple.py:199-200`
- **Evidence:** `s, _, d = idx.indices(len(self)); assert d > 0` — reversed slice `[::-1]` trips a bare `AssertionError` that is stripped under `python -O`, leaving undefined behavior.
- **Suggestion:** Handle `d < 0` explicitly or raise `ValueError`; don't rely on `assert` for slice validation.
- **Severity:** Low

### C16. meta.py `AMPH_DIR` semantics differ from `__init__.py`

- **Location:** `amphetype/meta.py:3` vs `amphetype/__init__.py:9-10`
- **Evidence:** `meta.py`: `AMPH_DIR = Path(__file__).parent` (package dir). `__init__.py`: `AMPH_DIR = Path(LIB_DIR).parent` (project root). Same name, different directories. `meta.py` has zero imports across the codebase (dead code).
- **Suggestion:** Delete `meta.py` (dead, duplicates `__version__`/`AMPH_DIR`/`DATA_DIR` from `__init__.py`), or have `__init__.py` import from it for a single source of truth.
- **Severity:** Low

### C17. `FBoxLayout` complex stretch uses `x` instead of `y`

- **Location:** `amphetype/layout.py:50-55`
- **Evidence:**

  ```python
  elif isinstance(x, complex):
      x, y = round(x.real), round(x.imag)
      if x: self.addSpacing(x)
      if y: self.addStretch(x)   # BUG: should be y
  ```

  The imaginary part (`y`) is computed but `addStretch` gets `x` (the spacing value). So a complex like `10+5j` adds spacing 10 and stretch 10 (instead of stretch 5). Compare `QtUtil.AmphGridLayout.addItemToGridLayout` (`:237-239`) which uses both `int(x.real)` and `int(x.imag)` correctly.
- **Suggestion:** Change `if y: self.addStretch(x)` to `if y: self.addStretch(y)`.
- **Severity:** Medium

### C18. `LessonDocument.onColor` rebuilds the whole document and destroys any in-progress run

- **Location:** `amphetype/typer.py:102-125` (`onColor`) and `:144-166` (`set_text`)
- **Evidence:** `onColor` ends with `if self._curtext is not None: self.set_text(*self._curtext)`. `set_text` calls `self.clear()` and re-inserts the entire display text, resetting `_run = None`. In `TyperWindow.__init__` (`:447-453`), every typer color and both `para_margin`/`para_lineheight` vars are connected to `doc.onColor`. Changing any color or dragging the paragraph-margin/line-height spinner mid-lesson wipes the user's current run and cursor position.
- **Suggestion:** For format-only changes, update `self.style_block`/style brushes and call `set_text` only when no run is active, or re-apply formats in place via a merge-format cursor. At minimum, skip the rebuild while `self.is_running()`.
- **Severity:** Medium

### C19. `code_lessons._replace_triple_quotes` returns error strings as content

- **Location:** `amphetype/lesson_builder/code_lessons.py:38-41`
- **Evidence:** On `FileNotFoundError`, returns `"Error: The file was not found."`. On any other exception, returns `f"An error occurred: {e}"`. These strings are then `.splitlines()` and processed as if they were code, creating "lessons" from error messages.
- **Suggestion:** Raise the exception or return `None` and have the caller skip the file, rather than embedding error text as lesson content.
- **Severity:** Medium

### C20. `AmphModel.hasChildren` reports children for sources that have none

- **Location:** `amphetype/QtUtil.py:53-59` (with `SourceModel`, `TextManager.py:33-77`)
- **Evidence:** `hasChildren` returns `True` for any top-level index purely based on `levels`, without checking whether `populateData` returns a non-empty list. A source with no enabled texts shows an expand arrow that expands to nothing.
- **Suggestion:** Override `hasChildren` in `SourceModel` to return `len(self.findList(parent)) > 0` for top-level parents.
- **Severity:** Low

### C21. `AmphModel.findList` mutates rows during read-only queries

- **Location:** `amphetype/QtUtil.py:85-96`
- **Evidence:** A read from `rowCount`/`data`/`index`/`hasChildren` appends the lazily-fetched child list onto the parent row in place, growing it from `cols+hidden` to `cols+hidden+1`. This mutates model data during what Qt treats as a read. A subclass adding a column or a formatter touching the last column would silently read the children list.
- **Suggestion:** Store children in a separate `dict[tuple, list]` keyed by `indexList(parent)` rather than appending into the data row.
- **Severity:** Low

### C22. `StatisticKind.TRIGRAM` typo in enum value

- **Location:** `amphetype/lesson_builder/__init__.py:12`
- **Evidence:** `TRIGRAM = "trigam"` — missing the second 'r'. `determine_statistic_kind` (line 53) compares against `str(StatisticKind.TRIGRAM)`, so it's internally consistent, but any external code or DB query comparing against the literal `"trigram"` will fail to match.
- **Suggestion:** Fix to `TRIGRAM = "trigram"`. Check DB column values for compatibility.
- **Severity:** Low

---

## 2. Performance

### P1. Schema-existence check via 5-table Cartesian product on every init

- **Location:** `amphetype/Data.py:122-125`
- **Evidence:** `fetchall('select * from result,source,statistic,text,mistake limit 1')` is run on every `AmphDatabase.__init__` purely to detect schema existence. This is a 5-table Cartesian product (though `LIMIT 1` short-circuits, the planner may still scan).
- **Suggestion:** Query `sqlite_master` for table names instead: `SELECT count(*) FROM sqlite_master WHERE type='table'`.
- **Severity:** Medium

### P2. `split_sentence` rebuilds whole string each iteration — O(n²)

- **Location:** `amphetype/Text.py:142`
- **Evidence:** `s.replace('\n', ' ')` allocates a fresh string each loop pass. For long sentences with many newlines, this is O(n²).
- **Suggestion:** Normalize whitespace once before the loop, or search both `' '` and `'\n'` without materializing the replacement.
- **Severity:** Low

### P3. `visc` computes timing list twice

- **Location:** `amphetype/timingtuple.py:257-266`
- **Evidence:** `visc` builds `xs = [t for t in self.timing if t is not None]` (full broadcast+filter via `datatuple.__getattr__`), then `median_err` iterates `self` again for `x.timing`.
- **Suggestion:** Compute `xs` once, pass into `median_err`, or fold the sum into the same pass.
- **Severity:** Low

### P4. `TyperWindow.moveEvent` re-applies the font on every window move pixel

- **Location:** `amphetype/typer.py:501-503`
- **Evidence:** `moveEvent` calls `self.updateFont()` which calls `self._doc.setDefaultFont(...)`. `moveEvent` fires on every pixel of window dragging, re-setting the document font and invalidating the document layout.
- **Suggestion:** Drop the `moveEvent` override, or guard it so the font is only applied when it actually changed. `showEvent` already applies the font on first show.
- **Severity:** Low

### P5. Per-keystroke `sig_position` → `setTextCursor` triggers extra viewport update

- **Location:** `amphetype/typer.py:248, 298` (emit) and `:343` (connect to `setTextCursor`)
- **Evidence:** `insert` and `backspace` end with `self.sig_position.emit(self.cursor)`, connected to `self.setTextCursor`. Combined with the `cursor.insertText`/`deleteChar`/`movePosition` calls, each keystroke produces multiple document mutations plus an explicit `setTextCursor` that re-syncs the viewport cursor and queues a repaint.
- **Suggestion:** Coalesce the position signal via a queued (idle) connection so rapid keystrokes collapse to one viewport update.
- **Severity:** Low

### P6. Both typers process every `setText` even when only one is visible

- **Location:** `amphetype/Amphetype.py:108, 115, 135` and `typer.py:513-523`, `Quizzer.py:187-191`
- **Evidence:** `text_mgr.setText` is connected to both `quizzer.setText` and `typer.setText`. `which_typer` only swaps which widget is *visible* — both stay alive and both rebuild their document/target on every new text. The hidden one's work is wasted.
- **Suggestion:** Gate `setText` handling on `isVisible()` / the stacked-widget's current index so the inactive typer skips the rebuild.
- **Severity:** Low

### P7. `common_words.get_short_words`/`get_medium_words` re-read files from disk on every call

- **Location:** `amphetype/lesson_builder/common_words.py:5-16`
- **Evidence:** Each call opens and reads the word list file. `_create_lesson_for_trigrams` (`__init__.py:89-91`) calls both functions every time a lesson is generated.
- **Suggestion:** Cache with `functools.lru_cache` or load once at module level.
- **Severity:** Low

### P8. `dampen` function silently returns empty list for short inputs

- **Location:** `amphetype/Performance.py:12-19`
- **Evidence:** `dampen(x, n=10)`: if `len(x) < n`, `sum(x[0:n])` works (partial sum), but `range(n, len(x))` is empty, so `ret` is `[]`. No error, but the graph shows no data. Callers may not expect this.
- **Suggestion:** Either document the behavior or handle `len(x) < n` by returning a single averaged value.
- **Severity:** Low

---

## 3. Error Handling

### E1. Broad `except Exception` masks real DB errors at init

- **Location:** `amphetype/Data.py:122-125`
- **Evidence:** `try: fetchall(...) except Exception: self.newDB()` — corrupt DB, locked file, disk error, malformed schema all swallowed and treated as schema-missing, invoking `newDB()` which can overwrite state.
- **Suggestion:** Catch `sqlite3.OperationalError` only (table-missing), log the exception, let others propagate.
- **Severity:** Medium

### E2. `newDB` uses `CREATE TABLE` without `IF NOT EXISTS` — partial schema causes crash

- **Location:** `amphetype/Data.py:160-169`
- **Evidence:** Five `CREATE TABLE` + `CREATE VIEW` with no `IF NOT EXISTS`. If some tables exist and some were dropped (partial schema), the detection `SELECT` fails → `newDB()` runs → existing tables raise `table already exists`, aborting init with a confusing error.
- **Suggestion:** Use `CREATE TABLE IF NOT EXISTS` for idempotent partial-schema repair.
- **Severity:** Medium

### E3. `main_normal` doesn't commit in `finally`; crash loses data

- **Location:** `amphetype/main.py:1-9`
- **Evidence:** `r = A.app.exec_(); A.DB.commit(); return r` — if `exec_` raises or the process is killed, `commit` is skipped. The global `DB` is never explicitly closed (`Data.py:222`), relying on interpreter teardown. Per PyQt5 docs, destructor order on exit is random, which can cause crashes or data loss.
- **Suggestion:** Wrap in `try/finally` to commit and close the DB on exit.
- **Severity:** Medium

### E4. `setRegex` doesn't validate pattern — invalid regex causes opaque failure

- **Location:** `amphetype/Data.py:141-142`
- **Evidence:** `self.regex_ = re.compile(x)` called from `TextManager.py:524` with `Settings.get('text_regex')`. An invalid regex raises `re.error` inside a SQL function during `executemany`, producing an opaque failure with no indication the user's regex pattern is at fault.
- **Suggestion:** Validate at the settings layer (reject invalid patterns with a user-facing error) or wrap with a clear error message identifying the bad pattern.
- **Severity:** Low

### E5. LessonMiner.**init** has no handling for bad/missing input files

- **Location:** `amphetype/Text.py:57-64`
- **Evidence:** `with codecs.open(fname, 'r', 'utf_8_sig')` — missing file raises `FileNotFoundError`, non-UTF-8 raises `UnicodeDecodeError`, both uncaught. The caller (`TextManager.py:370`) catches `Exception` and logs a generic error, but the user gets no specific feedback. `codecs.open` is also the legacy form of `open(..., encoding='utf-8-sig')`.
- **Suggestion:** Catch and emit a user-facing error via the progress signal; use builtin `open`.
- **Severity:** Low

### E6. `AboutWidget.__init__` does file I/O before `super().__init__`

- **Location:** `amphetype/Amphetype.py:159-171`
- **Evidence:** The `try/except` reads `about.html` and formats it *before* calling `super(AboutWidget, self).__init__(*args)`. If anything in the pre-`super` block raises an unexpected exception, the `QTextBrowser` base is never constructed.
- **Suggestion:** Call `super().__init__(*args)` first, then read the file inside a `try/except`.
- **Severity:** Low

### E7. `set_qt_css` opens stylesheet without explicit encoding and swallows errors broadly

- **Location:** `amphetype/Amphetype.py:174-186`
- **Evidence:** `with Path(fname).open("r") as f: app.setStyleSheet(f.read())` uses the platform default encoding (not UTF-8). Runs at import time, so a malformed CSS file can crash startup. Only the missing-file case is caught.
- **Suggestion:** Open with `encoding="utf-8"`, and wrap the read in `try/except OSError` with a fallback to `app.setStyleSheet("")`.
- **Severity:** Low

### E8. `code_lessons.create_id_from_path` uses `assert` for validation

- **Location:** `amphetype/lesson_builder/code_lessons.py:88`
- **Evidence:** `assert len(path_parts) >= 2, "path is too short to create a lesson id"` — stripped under `python -O`, leaving the function to silently produce a malformed ID from a single path component.
- **Suggestion:** Use `if len(path_parts) < 2: raise ValueError(...)`.
- **Severity:** Low

### E9. `DB.execute("vacuum")` inside cleanup may fail if transaction is open

- **Location:** `amphetype/Widgets/Database.py:158`
- **Evidence:** `VACUUM` cannot run inside a transaction. The preceding `DB.commit()` (line 157) closes the transaction, but if any implicit transaction was opened between commit and vacuum, it fails. No error handling.
- **Suggestion:** Ensure no open transaction, or wrap in try/except with a log message.
- **Severity:** Low

### E10. Quizzer `getStats` fallback for `req_space=False` fabricates timing from nonexistent DB row

- **Location:** `amphetype/Quizzer.py:131-148`
- **Evidence:** When `when[0] == -1`, it queries the median `time` for the first target char from `statistic`; if absent, `fetchone` returns a default, and `self.when[0] = self.when[1] - self.times[0]`. On the very first run for a new char (no statistics), this fabricates `when[0]` from a derived value, producing a negative or meaningless start time if `when[1]` is small. The downstream WPM (`12.0/spc`) is computed from a synthetic elapsed time.
- **Suggestion:** Guard the no-statistics case: skip the `times[0]` substitution or treat the first char as having the median of the current run.
- **Severity:** Low

---

## 4. Maintainability

### M1. Quizzer and TyperWindow duplicate the entire stats/recording/review pipeline

- **Location:** `amphetype/Quizzer.py:197-307` vs `amphetype/typer.py:564-708`
- **Evidence:** Both implement: insert a result row, fetch the last-N median aggregate, compute per-char/trigram/word `Statistic` + viscosity, `executemany_` into `statistic` and `mistake`, decide `is_lesson` thresholds, and the below-target replay / auto-review branch. The two copies have already diverged: Quizzer still has the `while ws[i][4] != 0` IndexError bug (C8) and the `log` import bug (C7); `typer.py` fixed both. AGENTS.md flags `Quizzer.py` as legacy.
- **Suggestion:** Extract the shared result/statistic/mistake/review logic into a single helper that both typers call, so fixes apply once. Alternatively, if Quizzer is truly legacy and `which_typer` defaults to the new one, plan its removal.
- **Severity:** Medium

### M2. `lesson_builder/widget.py` is a near-exact duplicate of `Lesson.py`

- **Location:** `amphetype/lesson_builder/widget.py:1-211` vs `amphetype/Lesson.py:1-215`
- **Evidence:** Both files define `StringListWidget`, `AdvancedLessonGenerator`/`LessonGenerator` with identical code (same imports, same methods, same signal names). `lesson_builder/widget.py` is the newer copy but both exist.
- **Suggestion:** Determine which is actually wired (grep for imports) and delete the other. If both are used, extract shared code into a base module.
- **Severity:** Medium

### M3. `lesson_builder/__init__.py` has dead/unreachable code

- **Location:** `amphetype/lesson_builder/__init__.py:83-84, 124-125`
- **Evidence:** `_create_lesson_for_keys` and `_create_lesson_for_words` always return `iter([])` and are never called (see C5). The `process_words` function (line 28) hardcodes `kind=StatisticKind.KEY` for all entries regardless of the `item_kind` parameter (line 42).
- **Suggestion:** Implement or remove. If removing, also remove the dispatch entries for keys/words from `create_lesson`.
- **Severity:** Medium

### M4. `meta.py` is dead code — zero imports across the entire codebase

- **Location:** `amphetype/meta.py:1-13`
- **Evidence:** Grep across `amphetype/`, `tests/`, `_scripts/` for `amphetype.meta`, `from .meta`, `import meta` returns zero imports. The file duplicates `__version__`/`AMPH_DIR`/`DATA_DIR` from `__init__.py` with different semantics (C16).
- **Suggestion:** Remove the file.
- **Severity:** Low

### M5. `TyperWindow.setDefaultText` is a dead stub

- **Location:** `amphetype/typer.py:509-511`
- **Evidence:** `def setDefaultText(self): log.error("setDefaultText() NOT IMPLEMENTED"); print("setDefaultText() NOT IMPLEMENTED")`. Grep finds no callers anywhere in the tree.
- **Suggestion:** Delete the method. `TextManager.empty_db_placeholder` / `nextText` now handle the "no text available" case.
- **Severity:** Low

### M6. `find_relative` ignores its `c` parameter

- **Location:** `amphetype/Text.py:121-133`
- **Evidence:** Docstring promises "find location of c" but body hardcodes `' '`: `a, b = s.find(' ', idx), s.rfind(' ', idx)`. `c` is never used; sole caller passes `' '`.
- **Suggestion:** Remove the `c` parameter and rename to `find_nearest_space`, or actually use `c`.
- **Severity:** Medium

### M7. `getTextContext` references module global `DB` from inside `AmphDatabase`

- **Location:** `amphetype/Data.py:194`
- **Evidence:** Inside an `AmphDatabase` method: `DB.fetchall(...)`. Every other method uses `self.fetchall`. Breaks if a second connection ever exists.
- **Suggestion:** Use `self.fetchall(...)`.
- **Severity:** Medium

### M8. Stateful SQL functions rely on undocumented ordering/reset contracts

- **Location:** `amphetype/Data.py:135-157`
- **Evidence:** `time_group`/`counter` mutate `self.lasttime_`/`self._count` across rows. Correctness depends on the caller resetting (`DB.resetTimeGroup()`/`DB.resetCounter()`) and the query being ordered by `w`/`time`. This contract is invisible at SQL call sites (`Performance.py:196, 200`).
- **Suggestion:** Document the ordering/reset requirement on the functions, or make them stateless (window/parameterized grouping) so query order can't corrupt grouping.
- **Severity:** Medium

### M9. Two parallel "require space" settings (`req_space` vs `require_space`)

- **Location:** `amphetype/Config.py:69` (`req_space: True`, global defaults) and `:106` (`require_space: True`, `typer_defaults`); used at `Quizzer.py:65,80,88` and `typer.py:384,539`
- **Evidence:** The Quizzer reads `Settings.get("req_space")`; TyperWindow reads `self.S["require_space"]` from the `typer` settings group. They are independent keys with independent values. The code itself comments: `typer.py:442` "I am so confused. Settings system must have gone through 3 totally different paradigms."
- **Suggestion:** Unify on a single setting (or make the typer group value fall back to the global `req_space`).
- **Severity:** Low

### M10. `Statistic.append` shadows `list.append` with extra keyword arg

- **Location:** `amphetype/Data.py:51-54`
- **Evidence:** `def append(self, x, flawed=False)` overrides `list.append`. Callers relying on the stdlib signature break; the `flawed` flag quietly extends stdlib method semantics.
- **Suggestion:** Rename to `add`/`insert_value`, or keep the stdlib signature and track `flawed_` via a separate method.
- **Severity:** Low

### M11. `# fmt: off` markers with no formatter configured

- **Location:** `amphetype/Text.py:13, 31`
- **Evidence:** `# fmt: off` / `#fmt: off` bracket abbreviations, but `pyproject.toml` configures ruff (which uses `# ruff: format: off`). The markers are inert noise.
- **Suggestion:** Remove the markers or update them to `# ruff: format: off` / `# ruff: format: on`.
- **Severity:** Low

### M12. Two `if __name__ == '__main__'` blocks in Text.py

- **Location:** `amphetype/Text.py:1-2, 195-199`
- **Evidence:** Top block imports `amphetype.Amphetype` to bootstrap `Settings`; bottom drives `LessonMiner`. Top-of-file import-as-main obscures the real entry point.
- **Suggestion:** Consolidate into one `__main__` block at the bottom.
- **Severity:** Low

### M13. `TyperWindow.updateLabel` hardcodes a one-shot "BETA viscosity" warning with mutable flag

- **Location:** `amphetype/typer.py:424, 544-557`
- **Evidence:** `self._viscosity_warning_shown = False` is flipped to `True` the first time `updateLabel` runs, embedding a permanent beta/viscosity warning into the label text. The flag resets on every app restart, so the warning reappears every session.
- **Suggestion:** Move to a one-time tooltip / About page / first-run dialog, or remove it once the new typer is no longer considered beta.
- **Severity:** Low

### M14. `AmphModel.data` ignores every role except DisplayRole and UserRole

- **Location:** `amphetype/QtUtil.py:105-128`
- **Evidence:** `if role != Qt.DisplayRole and role != Qt.UserRole: return QVariant()`. No `TextAlignmentRole`, `ToolTipRole`, `ForegroundRole`, `FontRole`, or `SizeHintRole`. Numeric columns inherit left-alignment with no right-alignment, and there's no way for subclasses to supply tooltips or color coding without overriding `data` wholesale.
- **Suggestion:** Factor the format/role dispatch so subclasses can declare per-column alignment, tooltips, or foreground brushes; at least default numeric columns to right alignment.
- **Severity:** Low

### M15. `AmphModel` does not emit insert/remove signals on lazy population

- **Location:** `amphetype/QtUtil.py:39-155`
- **Evidence:** `findList` lazily fetches and caches children inside `rowCount`/`hasChildren` calls without `beginInsertRows`/`endInsertRows`, relying on the view querying synchronously after expand. This happens to work with `QTreeView.expand()` but violates the model's contract.
- **Suggestion:** Eagerly populate children in `populateData` or emit `beginInsertRows`/`endInsertRows` when lazily attaching a child list.
- **Severity:** Low

### M16. `FStackedLayout` (layout.py) appears unused — duplicate of `FStackedWidget` (fwidgets.py)

- **Location:** `amphetype/fwidgets.py:26-51` and `amphetype/layout.py:4-29`
- **Evidence:** Both define `__init__`, `add`, `cycle`, `showFirst`, `showLast` with identical logic. `typer.py` and `Amphetype.py` use the widget version. Grep shows `FStackedWidget` is the one imported.
- **Suggestion:** Confirm `FStackedLayout` is unused and remove it.
- **Severity:** Low

### M17. `Config.py` has dead/noop settings

- **Location:** `amphetype/Config.py:61, 97`
- **Evidence:** `lesson_stats` (line 61) has comment "not used anymore". `gen_stats` (line 97) is commented out.
- **Suggestion:** Remove dead settings from the defaults dict.
- **Severity:** Low

### M18. `Lesson.py` `LessonGenerator` is legacy — barely wired or dead

- **Location:** `amphetype/Lesson.py:103-215`
- **Evidence:** The `LessonGenerator` class duplicates `lesson_builder/widget.py`'s `AdvancedLessonGenerator`. `StatWidgets.py:12` has a commented-out import `# from amphetype.Text import LessonGeneratorPlain`. The class may not be reachable in the current UI.
- **Suggestion:** Verify whether `LessonGenerator` is instantiated anywhere; if not, remove the file (M2).
- **Severity:** Low

### M19. Inconsistent viscosity definition across widgets

- **Location:** `amphetype/timingtuple.py:265-266` vs `amphetype/Quizzer.py:205`
- **Evidence:** `RunStats.median_err` is one-sided: `sum((max(0.0, x.timing - m))**2 ...)` (only slow-downs). Quizzer is two-sided: `sum(((x-spc)/spc)**2 ...)`. `typer.py:546` warns "Typer 2 uses a different measure for viscosity". Both stored in the same DB `viscosity` column, so historical data mixes two formulas.
- **Suggestion:** Standardize on one formula, or store a `viscosity_method` discriminator alongside the value.
- **Severity:** Low

### M20. `getSource` commits on update path but not insert path

- **Location:** `amphetype/Data.py:183-190`
- **Evidence:** Update branch: `self.execute(...); self.commit()`. Insert branch: `self.execute(...)` then `return self.getSource(source)` (recursive re-read) with no commit. Inconsistent commit behavior.
- **Suggestion:** Commit in both branches, or once at a higher level — pick one.
- **Severity:** Low

---

## 5. Design

### D1. `argparse` runs as import side effect

- **Location:** `amphetype/__init__.py:81`
- **Evidence:** `cli_options = _args_and_env()` executes at import time, parsing `sys.argv` and configuring logging. Any tool/test/notebook importing `amphetype` triggers argparse + logging side effects. `parse_known_args` silently swallows unexpected args.
- **Suggestion:** Defer to an explicit `init()` called from `main_normal()` so importing the package is side-effect-free.
- **Severity:** Medium

### D2. `AmphetypeWindow` holds no references to top-level widgets beyond Qt parenting

- **Location:** `amphetype/Amphetype.py:97-153`
- **Evidence:** `quizzer`, `typer`, `text_mgr`, `perf_hist`, `string_stat`, `lesson_gen`, `db_widget`, `tabs` are local variables. They survive only via Qt parenting and signal connections. This makes the window impossible to reach from tests/debug hooks without `findChild`.
- **Suggestion:** Store long-lived widgets as attributes (`self.text_mgr`, `self.typer`, etc.) if any test or future feature needs to drive them programmatically.
- **Severity:** Low

### D3. No PRAGMA tuning on SQLite connection

- **Location:** `amphetype/Data.py:222`
- **Evidence:** `sqlite3.connect(dbname, 5, 0, 'DEFERRED', False, AmphDatabase)` sets no journal mode, no FK enforcement, no synchronous level. A single-process app with frequent small writes would benefit from WAL + `synchronous=NORMAL` for better write throughput and crash safety.
- **Suggestion:** `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON` in `AmphDatabase.__init__`.
- **Severity:** Low

### D4. `settings.py` FBoolVar dispatches bool as int before checking bool strings

- **Location:** `amphetype/settings.py:90-98`
- **Evidence:** `FBoolVar.coerce` tries `int(val)` before checking bool string values. `QSettings` may store booleans as the string `"false"` or `"true"`; `int("false")` raises `ValueError`, falling through to the string check. But `int("1")` or `int("0")` returns before the explicit bool check, which is correct by accident. The control flow is fragile.
- **Suggestion:** Check bool strings first, then fall back to `int(val)`, with clear comments.
- **Severity:** Low

### D5. `settings.py` uses `assert` for lookup validation

- **Location:** `amphetype/settings.py` (FSettings `__getitem__`)
- **Evidence:** `assert` used to validate that a settings key exists. Stripped under `python -O`, leaving `KeyError` or `None` instead of a clear error.
- **Suggestion:** Use explicit `if key not in self: raise KeyError(key)`.
- **Severity:** Low

### D6. Dual color mechanisms in Config.py

- **Location:** `amphetype/Config.py:83-126`
- **Evidence:** Global defaults have `quiz_right_fg`/`quiz_right_bg`/`quiz_wrong_fg`/`quiz_wrong_bg` as string hex colors. `typer_color_defaults` has a separate set of color keys as `QColor` objects. Two different types, two different namespaces, two different code paths for color management.
- **Suggestion:** Unify the color settings system across both typers.
- **Severity:** Low

### D7. `TyperWidget.mousePressEvent`/`mouseReleaseEvent` overridden to `pass` — ambiguous focus behavior

- **Location:** `amphetype/typer.py:353-358`
- **Evidence:** `def mousePressEvent(self, e): pass` / `def mouseReleaseEvent(self, e): pass`. Comment says "Block mouse cursor movement. (Focus should still work.)" Swallowing `mousePressEvent` also skips `QTextEdit`'s default focus handling on click. The "should still work" hedge signals uncertainty.
- **Suggestion:** Call `self.setFocus()` explicitly in `mousePressEvent` before returning, instead of a bare `pass`.
- **Severity:** Low

### D8. Inconsistent Escape handling between Quizzer and TyperWidget

- **Location:** `amphetype/Quizzer.py:35-38` vs `amphetype/typer.py:370-371`
- **Evidence:** Quizzer emits `sigCancel` on Escape **and forwards the key to `QTextEdit.keyPressEvent`**. `TyperWidget` calls `self._lesson.reset()` on Escape and `evt.accept()`s it without forwarding. The two typers behave differently on Escape (cancel-to-new-text vs reset-current-text).
- **Suggestion:** Decide on one Escape semantic for both typers.
- **Severity:** Low

### D9. PyQt5 signal `connect()` with lambdas leaks references

- **Location:** Throughout `amphetype/Amphetype.py` (e.g., `:109, 116, 120, 125`)
- **Evidence:** Per PyQt5 documentation and mailing list discussions (riverbankcomputing.com, 2022), PyQt5's `connect()` holds a strong reference to non-bound-method callables (lambdas) and never releases them, even when the connection is destroyed. The codebase uses lambdas extensively in signal connections (e.g., `AmphetypeWindow.__init__`). These leak for the lifetime of the signal object.
- **Suggestion:** Use `pyqtSlot`-decorated methods or bound methods where possible; for one-off lambdas, consider `QTimer.singleShot` with `Qt.QueuedConnection` or explicit `disconnect()`. Not critical for a desktop app with short lifetime, but worth noting for long-running sessions.
- **Severity:** Low

---

## 6. Testing

### T1. Zero coverage for most modules

- **Location:** `tests/` (per AGENTS.md:190-193)
- **Evidence:** Existing tests cover: `timingtuple.py` (`test_timingtuple.py` — median, RunStats, CharEntry), `Data.py` SQL aggregates (`test_data_aggregates.py` — median, mean, first, abbreviate), and `TextManager._last_incomplete_text()` (`test_replay_smoke.py` — 7 scenarios). Not tested: `typer.py`, `Quizzer.py`, `Text.py` (SentenceSplitter), `Config.py`, `settings.py`, `Performance.py`, `StatWidgets.py`, `lesson_builder/`, `Widgets/Database.py`, `Widgets/Plotters.py`, `Amphetype.py`, `QtUtil.py`.
- **Suggestion:** High-value, low-effort tests to add:
  - `SentenceSplitter` vs decimals, abbreviations, Unicode (C12)
  - `_env_true` for falsy words (C9)
  - `abbreviate` for `n < 3` (C11)
  - `TextManager.nextText` for Difficult/Easy mode (C1, C2, C3, C4)
  - `lesson_builder.create_lesson` for keys/words dispatch (C5) and small word pool (C6)
  - `LessonDocument.insert`/`backspace` with a `QApplication` (headless)
  - Quizzer review-selection with all-mistakes word list (C8)
- **Severity:** Medium

### T2. No tests for TextManager selection strategies

- **Location:** `amphetype/TextManager.py:445-491`
- **Evidence:** `nextText` has 4 selection modes (random, in-order, difficult, easy), replay logic, and fallback behavior. Only `_last_incomplete_text` is tested. The bugs C1-C4 would be caught by selection-strategy tests.
- **Suggestion:** Add tests for each selection mode with in-memory SQLite, including edge cases (empty DB, all-disabled, short texts, no history).
- **Severity:** Medium

### T3. No tests for lesson_builder

- **Location:** `amphetype/lesson_builder/`
- **Evidence:** `create_lesson`, `process_words`, `_create_lesson_for_trigrams` are untested. C5 (always calls trigram generator) and C6 (`random.sample` oversample) would be caught by basic tests.
- **Suggestion:** Add tests with mock `StatisticEntry` lists for each `item_kind`.
- **Severity:** Medium

### T4. No tests for settings type coercion

- **Location:** `amphetype/settings.py`
- **Evidence:** `FBoolVar.coerce`, `FIntVar.coerce`, `FFloatVar.coerce` have no tests. The bool-to-int dispatch order (D4) is fragile and untested.
- **Suggestion:** Add tests for each `FVar` subclass with edge-case inputs (string "false", int 0, None, etc.).
- **Severity:** Low

---

## 7. CI / Tooling

### CI1. `pyproject.toml` has extensive `ty` rule suppressions that may hide real bugs

- **Location:** `pyproject.toml:110-164`
- **Evidence:** Three override blocks downgrade a total of 14 rules to `ignore` across `amphetype/**/*.py`:
  - `unresolved-attribute` (could hide C1 — `self.diff_eval` typo)
  - `no-matching-overload`
  - `unsupported-operator`
  - `invalid-method-override` (scoped to specific files)
  - `invalid-argument-type`
  - `unresolved-import`
  - `not-iterable`
  - `not-subscriptable`
  - `invalid-assignment`
  - `call-non-callable`
  - `call-top-callable`
  - `unknown-argument`
  - `deprecated`

  While the comments explain these are PyQt5 stub blind spots, the blanket `unresolved-attribute = "ignore"` across all `amphetype/**/*.py` would have caught C1 (`self.diff_eval` typo) and C2 (`self.defaultText` typo) if enabled.
- **Suggestion:** Narrow the overrides. At minimum, scope `unresolved-attribute` to only the files that actually have Qt enum issues, or use `# type: ignore[unresolved-attribute]` on specific lines rather than blanket suppression.
- **Severity:** Medium

### CI2. CI runs tests but AGENTS.md says it doesn't — documentation is stale

- **Location:** `.github/workflows/ci.yml` vs `AGENTS.md:194`
- **Evidence:** `ci.yml` runs `uv run ruff check`, `uv run ty check`, and `uv run pytest` on push/PR. AGENTS.md states "CI: Does not run tests — only roam-code analysis." This is outdated and misleading.
- **Suggestion:** Update AGENTS.md to reflect the current CI pipeline.
- **Severity:** Low

### CI3. CI does not run on macOS or Windows

- **Location:** `.github/workflows/ci.yml:5`
- **Evidence:** `runs-on: ubuntu-latest` only. The project supports macOS and Windows (per README), and `pyproject.toml` has platform-specific `pyqt5-qt5` constraints. Platform-specific issues (e.g., macOS focus behavior, Windows path handling) are not caught.
- **Suggestion:** Add a matrix strategy with `ubuntu-latest`, `macos-latest`, `windows-latest`.
- **Severity:** Low

### CI4. No coverage reporting in CI

- **Location:** `.github/workflows/ci.yml`
- **Evidence:** `pytest-cov` is a dev dependency (`pyproject.toml:37`), and `.coverage` exists locally, but CI runs bare `uv run pytest` with no `--cov` flag or reporting.
- **Suggestion:** Add `uv run pytest --cov=amphetype --cov-report=term-missing` to CI.
- **Severity:** Low

### CI5. `ruff` lint config is minimal — only E, W, F, B rules

- **Location:** `pyproject.toml:82-84`
- **Evidence:** `select = ["E", "W", "F", "B"]`. Missing valuable rule sets: `UP` (pyupgrade), `I` (isort/import sorting), `SIM` (simplifications), `RET` (return rules), `ARG` (unused arguments), `PTH` (pathlib usage).
- **Suggestion:** Consider enabling `UP`, `I`, `SIM` for additional automated quality checks.
- **Severity:** Low

### CI6. `lefthook.yml` runs ruff format but not ruff check

- **Location:** `lefthook.yml`
- **Evidence:** Pre-commit hook runs `ruff format --check` but not `ruff check`. Formatting issues are caught, but lint violations (B rules, unused imports) are not.
- **Suggestion:** Add `ruff check` to the pre-commit hook.
- **Severity:** Low

### CI7. SQL uses %-formatting instead of parameterization in several places

- **Location:** `amphetype/Performance.py:170, 196, 200`, `amphetype/StatWidgets.py:124`, `amphetype/Widgets/Database.py:141-143`, `amphetype/TextManager.py:458-459`
- **Evidence:**
  - `Performance.py:170`: `where.append("r.source = %d" % s)`
  - `Performance.py:196`: `group = "group by cast(counter()/%d as int)" % gn`
  - `Performance.py:200`: `group = "group by time_group(%f, r.w)" % mis`
  - `StatWidgets.py:124`: `order by %s limit %d` % (ord, limit)` — `ord` comes from `Settings.get("ana_which")`, a user-controlled setting string.
  - `Database.py:141-143`: `where w <= %f` % w, `cast(w/%f as int)` % g`
  - `TextManager.py:458`: `limit %d` % Settings.get("num_rand")`

  The `%d`/`%f` cases only emit numeric literals so are not exploitable, but `StatWidgets.py:124` interpolates a string (`ord`) into `ORDER BY` — if `ana_which` were ever set to an arbitrary string (e.g., via QSettings manipulation), it could inject SQL. All bypass parameterization.
- **Suggestion:** Parameterize where possible (use `?` placeholders). For `ORDER BY` clauses where parameterization isn't supported, validate `ord` against a whitelist of allowed sort strings (which `StatWidgets.py:49-58` already defines as `_statistic_options`).
- **Severity:** Medium

---

## Appendix: Files Reviewed

| Module                                     | Reviewed By             |
|--------------------------------------------|-------------------------|
| `amphetype/__init__.py`                    | ReviewCoreData          |
| `amphetype/meta.py`                        | ReviewCoreData          |
| `amphetype/main.py`                        | ReviewCoreData          |
| `amphetype/timingtuple.py`                 | ReviewCoreData          |
| `amphetype/Data.py`                        | ReviewCoreData          |
| `amphetype/Text.py`                        | ReviewCoreData          |
| `amphetype/typer.py`                       | ReviewGuiWidgets        |
| `amphetype/Quizzer.py`                     | ReviewGuiWidgets        |
| `amphetype/Amphetype.py`                   | ReviewGuiWidgets        |
| `amphetype/QtUtil.py`                      | ReviewGuiWidgets        |
| `amphetype/layout.py`                      | ReviewGuiWidgets        |
| `amphetype/fwidgets.py`                    | ReviewGuiWidgets        |
| `amphetype/Config.py`                      | ReviewSettingsTextMgmt  |
| `amphetype/settings.py`                    | ReviewSettingsTextMgmt  |
| `amphetype/TextManager.py`                 | ReviewSettingsTextMgmt  |
| `amphetype/Lesson.py`                      | ReviewSettingsTextMgmt  |
| `amphetype/lesson_builder/__init__.py`     | ReviewSettingsTextMgmt  |
| `amphetype/lesson_builder/code_lessons.py` | ReviewSettingsTextMgmt  |
| `amphetype/lesson_builder/widget.py`       | ReviewSettingsTextMgmt  |
| `amphetype/lesson_builder/common_words.py` | ReviewSettingsTextMgmt  |
| `amphetype/Performance.py`                 | ReviewStatsTestsTooling |
| `amphetype/StatWidgets.py`                 | ReviewStatsTestsTooling |
| `amphetype/Widgets/Database.py`            | ReviewStatsTestsTooling |
| `amphetype/Widgets/Plotters.py`            | ReviewStatsTestsTooling |
| `tests/test_timingtuple.py`                | ReviewStatsTestsTooling |
| `tests/test_data_aggregates.py`            | ReviewStatsTestsTooling |
| `tests/test_replay_smoke.py`               | ReviewStatsTestsTooling |
| `tests/conftest.py`                        | ReviewStatsTestsTooling |
| `.github/workflows/ci.yml`                 | ReviewStatsTestsTooling |
| `.github/workflows/roam.yml`               | ReviewStatsTestsTooling |
| `pyproject.toml`                           | ReviewStatsTestsTooling |
| `Taskfile.yml`                             | ReviewStatsTestsTooling |
| `lefthook.yml`                             | ReviewStatsTestsTooling |

---

## Severity Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| **High** | 6 | C1 (diff_eval typo), C2 (defaultText typo), C5 (lesson builder ignores item_kind), C7 (Quizzer log crash), C8 (Quizzer IndexError), + C1/C2 cause AttributeError on common paths |
| **Medium** | 26 | C3, C4, C6, C9, C10, C12, C17, C18, C19, P1, E1, E2, E3, M1, M2, M3, M6, M7, M8, D1, T1, T2, T3, CI1, CI7 |
| **Low** | 35 | All remaining findings |

**Top 5 recommendations to fix first:**

1. **C1 + C2** — Fix `self.diff_eval` → `self.difficulty_evaluator` and `self.defaultText` → `self.empty_db_placeholder`. These cause `AttributeError` on the Difficult/Easy selection modes and when no text is found.
2. **C5 + C6** — Implement `item_kind` dispatch in `create_lesson` and guard `random.sample` against small pools. Lesson generation is currently broken for keys/words and crashes on small word lists.
3. **C7** — Fix `Quizzer.py` log import from `from logging import log` to `import logging as log`. Latent crash on near-zero timing.
4. **E1 + E2** — Narrow the DB init `except Exception` to `OperationalError` and add `IF NOT EXISTS` to `CREATE TABLE`. Prevents data loss on corrupt/partial schemas.
5. **CI1** — Narrow `ty` rule suppressions, especially `unresolved-attribute`, which would have caught C1 and C2 automatically.
