# hellbox-afdko Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `hellbox-afdko` plugin package wrapping AFDKO's `makeotf`, `otf2ttf`, and `ttfcomponentizer` tools, then replace `source-sans/build.sh` with a `Hellfile.py` that replicates the static instance build pipeline.

**Architecture:** Three chutes (`MakeOTF`, `Otf2Ttf`, `TtfComponentizer`) each call their AFDKO Python API directly. Tests use the `Upright/Instances/Regular/font.ufo` from the sibling `source-sans` repo as a fixture. The source-sans `Hellfile.py` chains all three chutes into a single `build` task.

**Tech Stack:** Python 3.11+, AFDKO ≥ 4.0, hellbox, fontTools (for test assertions), uv, pytest

---

### Task 1: Package scaffold

**Files:**
- Create: `hellbox-afdko/pyproject.toml`
- Create: `hellbox-afdko/src/hellbox/jobs/afdko/__init__.py`
- Create: `hellbox-afdko/.github/workflows/test.yml`
- Create: `hellbox-afdko/.github/workflows/release.yml`
- Create: `hellbox-afdko/.github/workflows/publish.yml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /Users/jack/code/hellboxpy/hellbox-afdko/src/hellbox/jobs/afdko
mkdir -p /Users/jack/code/hellboxpy/hellbox-afdko/tests
mkdir -p /Users/jack/code/hellboxpy/hellbox-afdko/.github/workflows
```

- [ ] **Step 2: Create `pyproject.toml`**

`hellbox-afdko/pyproject.toml`:
```toml
[project]
name = "hellbox-afdko"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "hellbox",
    "afdko>=4.0",
]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
exclude = ["hellbox", "hellbox.jobs"]

[dependency-groups]
dev = ["pytest", "fonttools"]

[tool.uv.sources]
hellbox = { git = "https://github.com/hellboxpy/hellbox.git" }
```

- [ ] **Step 3: Create empty `__init__.py`**

`hellbox-afdko/src/hellbox/jobs/afdko/__init__.py`:
```python
```

(Empty for now — exports added in Task 5.)

- [ ] **Step 4: Create CI workflow stubs**

`hellbox-afdko/.github/workflows/test.yml`:
```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    uses: hellboxpy/gh-actions/.github/workflows/test.yml@main
```

`hellbox-afdko/.github/workflows/release.yml`:
```yaml
name: Release
on:
  push:
    branches: [main]
jobs:
  release-please:
    uses: hellboxpy/gh-actions/.github/workflows/release.yml@main
```

`hellbox-afdko/.github/workflows/publish.yml`:
```yaml
name: Publish
on:
  release:
    types: [published]
jobs:
  publish:
    uses: hellboxpy/gh-actions/.github/workflows/publish.yml@main
```

- [ ] **Step 5: Initialise git and commit scaffold**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git init
git add .
git commit -m "chore: initial package scaffold"
```

---

### Task 2: Test fixture

**Files:**
- Create: `hellbox-afdko/tests/conftest.py`

- [ ] **Step 1: Create `conftest.py`**

`hellbox-afdko/tests/conftest.py`:
```python
from pathlib import Path
import pytest

# Resolve the sibling source-sans repo
_SOURCE_SANS = Path(__file__).parent.parent.parent / "source-sans"
_UFO = _SOURCE_SANS / "Upright" / "Instances" / "Regular" / "font.ufo"


@pytest.fixture(scope="session")
def ufo_path():
    if not _UFO.exists():
        pytest.skip("source-sans repo not found at expected sibling path")
    return _UFO
```

- [ ] **Step 2: Install dev dependencies**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv sync
```

Expected: uv resolves hellbox from git, installs afdko, pytest, fonttools.

- [ ] **Step 3: Verify fixture is found**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/ --collect-only
```

Expected: pytest collects 0 items (no tests yet) with no errors or skips.

- [ ] **Step 4: Commit**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git add tests/conftest.py uv.lock
git commit -m "test: add UFO fixture via source-sans sibling path"
```

---

### Task 3: `MakeOTF` chute

**Files:**
- Create: `hellbox-afdko/src/hellbox/jobs/afdko/make_otf.py`
- Create: `hellbox-afdko/tests/test_make_otf.py`

- [ ] **Step 1: Write the failing test**

`hellbox-afdko/tests/test_make_otf.py`:
```python
from fontTools.ttLib import TTFont
from hellbox.jobs.afdko.make_otf import MakeOTF


def test_make_otf_produces_valid_otf(ufo_path, tmp_path):
    from hellbox.source_file import SourceFile
    file = SourceFile(ufo_path, ufo_path, tmp_path)

    chute = MakeOTF()
    result = chute.process(file)

    assert result.content_path.exists()
    assert result.content_path.suffix == ".otf"
    font = TTFont(str(result.content_path))
    assert "CFF " in font


def test_make_otf_release_mode(ufo_path, tmp_path):
    from hellbox.source_file import SourceFile
    file = SourceFile(ufo_path, ufo_path, tmp_path)

    chute = MakeOTF(release=True, omit_mac_names=True)
    result = chute.process(file)

    assert result.content_path.exists()
    font = TTFont(str(result.content_path))
    assert "CFF " in font
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_make_otf.py -v
```

Expected: FAIL — `ImportError: cannot import name 'MakeOTF'`

- [ ] **Step 3: Implement `MakeOTF`**

`hellbox-afdko/src/hellbox/jobs/afdko/make_otf.py`:
```python
from hellbox import Hellbox
from hellbox.chutes.chute import Chute
from hellbox.source_file import SourceFile


class MakeOTF(Chute):
    def __init__(
        self,
        release: bool = False,
        filter_glyphs: bool = False,
        omit_mac_names: bool = False,
    ) -> None:
        self.release = release
        self.filter_glyphs = filter_glyphs
        self.omit_mac_names = omit_mac_names

    def process(self, file: SourceFile) -> SourceFile:
        from afdko import makeotf

        Hellbox.info(f"Building OTF: {file.name}")
        copy = file.copy(name=file.stem + ".otf")
        args = ["-f", str(file.content_path), "-o", str(copy.content_path)]
        if self.release:
            args += ["-r"]
        if self.filter_glyphs:
            args += ["-gs"]
        if self.omit_mac_names:
            args += ["-omitMacNames"]
        result = makeotf.main(args)
        if result and result != 0:
            raise RuntimeError(f"makeotf failed with exit code {result}")
        return copy
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_make_otf.py -v
```

Expected: PASS — both tests green.

- [ ] **Step 5: Commit**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git add src/hellbox/jobs/afdko/make_otf.py tests/test_make_otf.py
git commit -m "feat: add MakeOTF chute"
```

---

### Task 4: `Otf2Ttf` chute

**Files:**
- Create: `hellbox-afdko/src/hellbox/jobs/afdko/otf2ttf.py`
- Create: `hellbox-afdko/tests/test_otf2ttf.py`

- [ ] **Step 1: Write the failing test**

`hellbox-afdko/tests/test_otf2ttf.py`:
```python
from fontTools.ttLib import TTFont
from hellbox.jobs.afdko.make_otf import MakeOTF
from hellbox.jobs.afdko.otf2ttf import Otf2Ttf


def test_otf2ttf_produces_valid_ttf(ufo_path, tmp_path):
    from hellbox.source_file import SourceFile

    # Build OTF first, then convert
    ufo_file = SourceFile(ufo_path, ufo_path, tmp_path)
    otf_file = MakeOTF().process(ufo_file)

    chute = Otf2Ttf()
    result = chute.process(otf_file)

    assert result.content_path.exists()
    assert result.content_path.suffix == ".ttf"
    font = TTFont(str(result.content_path))
    assert "glyf" in font
    assert "CFF " not in font
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_otf2ttf.py -v
```

Expected: FAIL — `ImportError: cannot import name 'Otf2Ttf'`

- [ ] **Step 3: Implement `Otf2Ttf`**

`hellbox-afdko/src/hellbox/jobs/afdko/otf2ttf.py`:
```python
from hellbox import Hellbox
from hellbox.chutes.chute import Chute
from hellbox.source_file import SourceFile


class Otf2Ttf(Chute):
    def process(self, file: SourceFile) -> SourceFile:
        from afdko import otf2ttf

        Hellbox.info(f"Converting to TTF: {file.name}")
        copy = file.copy(name=file.stem + ".ttf")
        result = otf2ttf.main([str(file.content_path), "-o", str(copy.content_path)])
        if result and result != 0:
            raise RuntimeError(f"otf2ttf failed with exit code {result}")
        return copy
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_otf2ttf.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git add src/hellbox/jobs/afdko/otf2ttf.py tests/test_otf2ttf.py
git commit -m "feat: add Otf2Ttf chute"
```

---

### Task 5: `TtfComponentizer` chute

**Files:**
- Create: `hellbox-afdko/src/hellbox/jobs/afdko/ttf_componentizer.py`
- Create: `hellbox-afdko/tests/test_ttf_componentizer.py`

- [ ] **Step 1: Write the failing test**

`hellbox-afdko/tests/test_ttf_componentizer.py`:
```python
from fontTools.ttLib import TTFont
from hellbox.jobs.afdko.make_otf import MakeOTF
from hellbox.jobs.afdko.otf2ttf import Otf2Ttf
from hellbox.jobs.afdko.ttf_componentizer import TtfComponentizer


def test_ttfcomponentizer_produces_valid_ttf(ufo_path, tmp_path):
    from hellbox.source_file import SourceFile

    ufo_file = SourceFile(ufo_path, ufo_path, tmp_path)
    otf_file = MakeOTF().process(ufo_file)
    ttf_file = Otf2Ttf().process(otf_file)

    chute = TtfComponentizer()
    result = chute.process(ttf_file)

    assert result.content_path.exists()
    assert result.content_path.suffix == ".ttf"
    font = TTFont(str(result.content_path))
    assert "glyf" in font
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_ttf_componentizer.py -v
```

Expected: FAIL — `ImportError: cannot import name 'TtfComponentizer'`

- [ ] **Step 3: Implement `TtfComponentizer`**

`hellbox-afdko/src/hellbox/jobs/afdko/ttf_componentizer.py`:
```python
from hellbox import Hellbox
from hellbox.chutes.chute import Chute
from hellbox.source_file import SourceFile


class TtfComponentizer(Chute):
    def process(self, file: SourceFile) -> SourceFile:
        from afdko import ttfcomponentizer

        Hellbox.info(f"Componentizing: {file.name}")
        copy = file.copy()
        result = ttfcomponentizer.main([str(copy.content_path)])
        if result and result != 0:
            raise RuntimeError(f"ttfcomponentizer failed with exit code {result}")
        return copy
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/test_ttf_componentizer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git add src/hellbox/jobs/afdko/ttf_componentizer.py tests/test_ttf_componentizer.py
git commit -m "feat: add TtfComponentizer chute"
```

---

### Task 6: Wire up exports and run full test suite

**Files:**
- Modify: `hellbox-afdko/src/hellbox/jobs/afdko/__init__.py`

- [ ] **Step 1: Add exports to `__init__.py`**

`hellbox-afdko/src/hellbox/jobs/afdko/__init__.py`:
```python
from hellbox.jobs.afdko.make_otf import MakeOTF
from hellbox.jobs.afdko.otf2ttf import Otf2Ttf
from hellbox.jobs.afdko.ttf_componentizer import TtfComponentizer

__all__ = ["MakeOTF", "Otf2Ttf", "TtfComponentizer"]
```

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
uv run pytest tests/ -v
```

Expected: 4 tests PASS.

- [ ] **Step 3: Commit**

```bash
cd /Users/jack/code/hellboxpy/hellbox-afdko
git add src/hellbox/jobs/afdko/__init__.py
git commit -m "feat: export MakeOTF, Otf2Ttf, TtfComponentizer from package"
```

---

### Task 7: Create GitHub remote and push

- [ ] **Step 1: Create repo on GitHub**

```bash
gh repo create hellboxpy/hellbox-afdko --public --source /Users/jack/code/hellboxpy/hellbox-afdko --push
```

Expected: repo created and all commits pushed to `main`.

---

### Task 8: Wire up source-sans

**Files:**
- Modify: `source-sans/pyproject.toml`
- Modify: `source-sans/Hellfile.py`

- [ ] **Step 1: Update `source-sans/pyproject.toml`**

`source-sans/pyproject.toml`:
```toml
[project]
name = "source-sans"
version = "0.1.0"
description = "Source Sans 3 font build"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "hellbox",
    "hellbox-afdko",
]

[tool.uv.sources]
hellbox = { git = "https://github.com/hellboxpy/hellbox.git" }
hellbox-afdko = { path = "../hellbox-afdko", editable = true }
```

- [ ] **Step 2: Sync dependencies**

```bash
cd /Users/jack/code/hellboxpy/source-sans
uv sync
```

Expected: hellbox installed from git, hellbox-afdko installed as editable from path.

- [ ] **Step 3: Write `Hellfile.py`**

`source-sans/Hellfile.py`:
```python
from hellbox import Hellbox
from hellbox.jobs.afdko import MakeOTF, Otf2Ttf, TtfComponentizer

with Hellbox("build") as task:
    task.describe("Build static OTF and TTF instances from UFO sources.")
    task.clean("target/OTF")
    task.clean("target/TTF")
    task.read(
        "Upright/Instances/*/font.ufo",
        "Italic/Instances/*/font.ufo",
    ) >> MakeOTF(release=True, filter_glyphs=True, omit_mac_names=True) \
      >> task.write("target/OTF") \
      >> Otf2Ttf() \
      >> TtfComponentizer() \
      >> task.write("target/TTF")

Hellbox.default = "build"
```

- [ ] **Step 4: Run the hellbox build**

```bash
cd /Users/jack/code/hellboxpy/source-sans
hell run build
```

Expected: 14 fonts built (7 upright + 7 italic), `target/OTF/` contains 14 `.otf` files, `target/TTF/` contains 14 `.ttf` files.

- [ ] **Step 5: Smoke-check outputs match build.sh**

```bash
# Count output files
ls /Users/jack/code/hellboxpy/source-sans/target/OTF/*.otf | wc -l
ls /Users/jack/code/hellboxpy/source-sans/target/TTF/*.ttf | wc -l
```

Expected: 14 each.

- [ ] **Step 6: Commit**

```bash
cd /Users/jack/code/hellboxpy/source-sans
git add Hellfile.py pyproject.toml uv.lock
git commit -m "feat: replace build.sh with hellbox pipeline"
```
