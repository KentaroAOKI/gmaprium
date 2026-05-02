# PyPI Release

## Prerequisites

Install release tools:

```bash
python -m pip install -e ".[dev]"
```

Create a real `~/.pypirc` from `.pypirc.example`, or pass tokens through environment variables. Do not commit real tokens.

## Build

```bash
rm -rf dist
python -m build
python -m twine check dist/*
```

## TestPyPI

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI in a clean environment:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gmaprium
python -c "import gmaprium; print(gmaprium.__file__)"
```

## PyPI

After TestPyPI validation:

```bash
python -m twine upload dist/*
```

## Versioning Checklist

1. Update `version` in `pyproject.toml`.
2. Run `pytest`.
3. Run `python -m build`.
4. Run `python -m twine check dist/*`.
5. Upload to TestPyPI first.
6. Upload to PyPI.
