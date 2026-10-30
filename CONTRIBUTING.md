# Contributing to SMS2Clip

Thanks for helping improve SMS2Clip. The project is Windows-specific and currently targets Windows 10/11 x64.

## Before opening an issue

- Search existing issues first.
- Include the SMS2Clip version, Windows version, and exact steps to reproduce.
- Do not post real verification codes, access tokens, private ntfy topics, or personal SMS content. Use redacted examples.
- Report security vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Development setup

1. Install Python 3.10 or newer.
2. Clone the repository.
3. Create and activate a virtual environment.
4. Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the application from source:

```powershell
python -m SMS2Clip.gui
```

## Checks before submitting a pull request

```powershell
ruff check SMS2Clip tests
ruff format --check SMS2Clip tests
python -m unittest discover -s tests -v
```

For packaging changes, also run:

```powershell
.\build.ps1
```

## Pull requests

- Keep changes focused and explain the user-visible behavior.
- Add or update tests for behavior changes.
- Preserve the existing Chinese and English UI coverage.
- Avoid committing generated binaries, user configuration, logs, clipboard history, tokens, or private topics.
- Update README files when setup, configuration, or user-facing behavior changes.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
