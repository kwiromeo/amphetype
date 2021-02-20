# Changelog

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
