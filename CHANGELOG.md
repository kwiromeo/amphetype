# Changelog

## Unreleased

### Added
- New beta typing interface with lots of added features.
- New input modes: insert mode vs overwrite mode (Typer 2).
- New input modes: strict mode vs lenient mode (Typer 2).
- Option for preventing backspacing over correct input (Typer 2).
- Show context around lesson text (Typer 2).
- Progress bar for lesson progress (Typer 2).
- Probably a lot more that I've forgotten to note here.
- Buttons for deleting all statistics and results within last minute/hour/day.
- Configurable line height and paragraph separation (Typer 2).

### Changed
- Fixed two crashes that could occur (Typer 1).
- Changed how viscosity is calculated (Typer 2 ONLY): in the new model only
  inputs slower than the median measure (of its kind) get assigned any
  viscosity.
- Typing now occurs in the same place as the input text (Typer 2).
- Alt/Ctrl/Meta + backspace now deletes back one word.
- Paragraphs are wrapped in markup and now have some spacing between
  them.
- Changed to using perf_counter() -- hopefully leading to better timing data.
- Colors are more configurable (Typer 2).
- Added option to break sentences when importing text.
- Min/max lesson size now actually works more like expected.

## 1.0.1 - 2021-02-20

No change, just a re-upload to PyPI as previous didn't contain data
files.

## 1.0.0 - 2021-02-19

Made an executive decision to call this version 1.0, even though it's
arbitrary. First version of the resurrected project with a Windows
installer.

### Changed
- Resurrected old project from Python 2.
- Restructured into a PyPi package.
- Database file is now stored in user-local app directory by default.

### Added
- Added theme support (customizable with CSS).
- Added option to remove unicode from texts (enforce plain ASCII).
- Added command-line parameter "--local" for running portable version.

### Fixed
- Fixed several bugs in lesson generation.
