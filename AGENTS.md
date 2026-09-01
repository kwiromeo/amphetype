# Repository Guidelines

## Project Overview

Amphetype is a typing practice and analysis application with a PyQt5 GUI. Originally created ~12 years ago on Google Code, it was resurrected and ported from Python 2/Qt4 to Python 3/Qt5. Users import text sources (books, code, word lists), type them in a rich-text widget, and get detailed per-character/trigram/word statistics (WPM, accuracy, viscosity). Licensed GPL-3.0.

## Architecture & Data Flow

### Startup Sequence

```text
amphetype/main.py:main_normal()
  → amphetype/Amphetype.py module-level init
    → AmphetypeApp (QApplication subclass) — module global `app`
    → Config.py → AmphSettings singleton `Settings`
    → Data.py → AmphDatabase singleton `DB` (SQLite)
  → AmphetypeWindow builds tabbed UI, wires signal/slot connections
  → app.exec_() enters Qt event loop
```

### Data Flow

```text
Text import → LessonMiner (sentence splitting) → SQLite (source/text tables)
  → TextManager.nextText() selects by strategy (random/in-order/easy/difficult)
  → TyperWidget/LessonDocument (rich-text, per-character coloring)
  → RunStats (per-character timing, mistakes, inserts)
  → Analysis: WPM/accuracy/viscosity → result/statistic/mistake tables
  → PerformanceHistory / StringStats display
```

### Key Modules

| Module                          | Role                                                                 |
|---------------------------------|----------------------------------------------------------------------|
| `amphetype/main.py`             | Entry point — `main_normal()`, `main_portable()`                     |
| `amphetype/Amphetype.py`        | App bootstrap, main window, tab wiring                               |
| `amphetype/Config.py`           | Settings system — typed defaults, reactive signals                   |
| `amphetype/settings.py`         | FSettings framework — typed FVar hierarchy with auto-persistence     |
| `amphetype/Data.py`             | SQLite layer — 5 tables, custom aggregates (median, mean, first)     |
| `amphetype/typer.py`            | New Typer 2 widget — rich-text, per-character coloring, progress bar |
| `amphetype/Quizzer.py`          | Legacy typer — simpler char-by-char validation                       |
| `amphetype/TextManager.py`      | Text/source management, selection strategies, replay logic           |
| `amphetype/Text.py`             | Text processing — SentenceSplitter, LessonMiner                      |
| `amphetype/timingtuple.py`      | Core data model — CharEntry, RunStats, viscosity calculation         |
| `amphetype/Performance.py`      | Performance history tree + graph plotting                            |
| `amphetype/StatWidgets.py`      | Key/trigram/word statistics analysis                                 |
| `amphetype/Lesson.py`           | Legacy lesson generator                                              |
| `amphetype/lesson_builder/`     | Newer lesson builder — trigram/key/word-based, code lessons          |
| `amphetype/QtUtil.py`           | Reusable Qt base classes — AmphModel, AmphTree, layout helpers       |
| `amphetype/layout.py`           | Declarative layout DSL — FBoxLayout, FStackedLayout                  |
| `amphetype/Widgets/Database.py` | Import/export, DB maintenance                                        |
| `amphetype/Widgets/Plotters.py` | Custom bar charts via QGraphicsScene                                 |

### Architectural Patterns

- **Signal/slot orchestration**: `AmphetypeWindow` wires all cross-widget communication via `pyqtSignal`. No direct coupling between widgets.
- **Global singletons**: `app` (AmphetypeApp), `Settings` (AmphSettings), `DB` (AmphDatabase) — imported directly by modules. Import order is carefully managed.
- **No async, no threading**: Everything runs on the Qt main event loop. The only deferred pattern is `QTimer.singleShot(500, ...)` for debounced text handling.
- **Reactive settings**: `Settings.signal_for("key").connect(callback)` — UI updates reactively when settings change.
- **Declarative layouts**: `FBoxLayout` accepts nested lists/tuples — widgets, strings (→QLabel), ints (spacing), None (stretch), sub-lists (nested layouts).

## Key Directories

| Path                        | Purpose                                                         |
|-----------------------------|-----------------------------------------------------------------|
| `amphetype/`                | Main package — all source modules                               |
| `amphetype/lesson_builder/` | Advanced lesson generation (newer)                              |
| `amphetype/Widgets/`        | Sub-widgets (Database, Plotters)                                |
| `tests/`                    | Test files (currently 1 smoke test)                             |
| `data/`                     | Bundled data — QSS themes, word lists, sample texts, icons      |
| `data/css/`                 | Qt stylesheet themes (9 themes, MIT licensed from GTRONICK/QSS) |
| `data/texts/`               | Public-domain literary texts (11 files, one paragraph per line) |
| `data/wordlists/`           | Frequency-sorted word lists (5 files, 10-50 most common)        |
| `_scripts/`                 | Utility scripts (marimo notebook, clipboard export)             |
| `.github/workflows/`        | CI — roam-code analysis only (no test/build/deploy)             |

## Development Commands

```bash
# Run the app
task run-app
# Equivalent: python -c 'from amphetype.main import main_normal; main_normal()'

# Build standalone executable (macOS .app)
task build-app
# Equivalent: pyinstaller --clean amphetype-mac.spec

# Clean build artifacts
task clean-build

# Run tests (no test runner configured)
python tests/test_replay_smoke.py

# List all task commands
task --list-all
```

## Code Conventions & Common Patterns

### Naming

| Element           | Convention            | Examples                                               |
|-------------------|-----------------------|--------------------------------------------------------|
| Modules           | PascalCase            | `TextManager.py`, `Quizzer.py`, `StatWidgets.py`       |
| Classes           | PascalCase            | `AmphetypeWindow`, `LessonDocument`, `RunStats`        |
| Methods           | snake_case            | `nextText()`, `update_sources_list()`, `force_ascii()` |
| Signals           | camelCase             | `wantText`, `statsChanged`, `setText`, `sigDone`       |
| Private attrs     | `_leading_underscore` | `_replay_pending`, `_current_lesson`                   |
| Constants         | UPPER_CASE            | `RETURN_CHAR`, `PARA_SEP`, `LIB_DIR`                   |
| Custom widgets    | `Amph` prefix         | `AmphModel`, `AmphTree`, `AmphButton`                  |
| Framework widgets | `F` prefix            | `FVar`, `FSettings`, `FBoxLayout`                      |
| Settings keys     | snake_case            | `typer_font`, `min_wpm`, `select_method`               |
| DB columns        | lowercase             | `wpm`, `accuracy`, `viscosity`, `text_id`              |

### Imports

- Explicit imports from Qt modules: `from PyQt5.QtCore import ...`
- Intra-package: `from amphetype.X import Y`
- Some modules import at function level to avoid circular imports (e.g., `main.py` imports Amphetype inside `main_normal()`)

### Error Handling

- `try/except Exception: pass` — silent skip on duplicate inserts, file processing failures
- `logging` module throughout — `log.error()`, `log.warning()`, `log.info()`
- Assertions for invariants
- Guard clauses: early returns on None/invalid data
- No custom exceptions — built-in only
- No formatter/linter config in project

### Database Patterns

- Raw SQL strings throughout — no ORM
- `DB.fetchone(sql, default, *args)` — custom helper with default value
- `DB.executemany_()` — thin wrapper around `executemany`
- Custom SQLite aggregates registered at connection time (median, mean, first)
- Custom SQLite functions (regex_match, abbreviate, time_group, counter, ifelse)
- Schema created on first use via `newDB()` if tables don't exist

### Settings Patterns

```python
Settings.get("key")           # typed access
Settings.set("key", value)    # typed set
Settings.signal_for("key").connect(callback)  # reactive
Settings.getFont("typer_font")  # font deserialization
```

### Type Hints

- Minimal — some newer code uses `Optional`, `Iterable`, `List[str]`
- Older code has none
- `# noqa` comments for import-related lint suppression

## Important Files

| File                        | Purpose                                                |
|-----------------------------|--------------------------------------------------------|
| `amphetype/main.py`         | Entry point — `main_normal()`, `main_portable()`       |
| `amphetype/Amphetype.py`    | App bootstrap, main window, signal wiring              |
| `amphetype/Config.py`       | Settings defaults and UI                               |
| `amphetype/settings.py`     | FSettings framework (typed variables, persistence)     |
| `amphetype/Data.py`         | SQLite database layer                                  |
| `amphetype/typer.py`        | New Typer 2 widget (rich-text, per-character coloring) |
| `amphetype/Quizzer.py`      | Legacy typer widget                                    |
| `amphetype/TextManager.py`  | Text/source management, selection, replay              |
| `amphetype/timingtuple.py`  | Core data model — CharEntry, RunStats                  |
| `amphetype/lesson_builder/` | Advanced lesson generation                             |
| `pyproject.toml`            | Build config, dependencies                             |
| `Taskfile.yml`              | Dev task runner                                        |
| `amphetype-mac.spec`        | PyInstaller spec for macOS build                       |
| `data/css/*.qss`            | Qt stylesheet themes                                   |
| `data/texts/*.txt`          | Bundled typing practice texts                          |
| `data/wordlists/*.txt`      | Frequency-sorted word lists                            |

## Runtime/Tooling Preferences

- **Python**: >=3.13
- **Package manager**: `uv` (Astral) — `uv.lock` is the source of truth; `requirements.txt` is a frozen pinfile
- **Build system**: setuptools (>=61.0) with `setuptools.build_meta` backend
- **GUI framework**: PyQt5 (5.15.11) — Qt5 only, no Qt6 support
- **Key runtime deps**: `translitcodec` (text normalization), `polyleven` (Levenshtein distance), `more-itertools`
- **Dev deps**: `pyinstaller` (bundling), `marimo` (notebooks), `paperclip` (clipboard), `djlint` (HTML lint)
- **Platform support**: Linux, macOS, Windows
- **CI**: GitHub Actions — roam-code analysis only (no test/build/deploy in CI)
- **Editor config**: VS Code (tabSize: 2, ruler: 100, typeCheckingMode: standard), Zed (ty + ruff)

## Testing & QA

- **No test framework**: Tests are raw Python files with `assert` statements, run via `python tests/test_replay_smoke.py`
- **Coverage**: None — no coverage tool configured, no coverage in CI
- **Test scope**: Minimal — 1 smoke test covering `TextManager._last_incomplete_text()` query logic (7 scenarios with in-memory SQLite)
- **What's not tested**: All other modules, GUI behavior, file I/O, integration flows
- **CI**: Does not run tests — only roam-code analysis (fitness scoring, PR risk assessment)
- **Linting**: No project-wide linter/formatter configured; `ty` and `ruff` available in Zed config
