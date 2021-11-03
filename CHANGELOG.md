# Changelog

## Unreleased

### Added
- Brand new typing interface with lots of added features.
- New input modes: insert mode vs overwrite mode.
- New input modes: strict mode vs lenient mode.
- Option for preventing backspacing over correct input.
- Show context around lesson text.
- Progress bar for lesson progress.

### Changed
- Typing now occurs in the same place as the text is.
- Alt/Ctrl/Meta + backspace now deletes back one word.
- Paragraphs are wrapped in markup and now have some spacing between
  them.

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
