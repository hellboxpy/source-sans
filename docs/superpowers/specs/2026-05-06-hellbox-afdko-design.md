# hellbox-afdko design

**Date:** 2026-05-06
**Goal:** Replace `build.sh` in the Source Sans project with a Hellbox pipeline,
achieving 1:1 equivalency and enabling speed comparison between the two approaches.

## Scope

Static instance builds only. Variable font pipeline (`buildVFs.py`) is deferred
pending a fork/join DSL extension in hellbox core
(see `hellbox/design/pipeline-multi-file.md`).

## Package: `hellbox-afdko`

A new hellbox plugin wrapping AFDKO tools via their Python APIs. Lives at
`hellboxpy/hellbox-afdko`, following the same conventions as the other plugins.

### Dependencies

- `hellbox`
- `afdko >= 4.0`
- `requires-python = ">=3.11"`

### Structure

```
hellbox-afdko/
  src/hellbox/jobs/afdko/
    __init__.py
    make_otf.py
    otf2ttf.py
    ttf_componentizer.py
  tests/
    test_make_otf.py
    test_otf2ttf.py
    test_ttf_componentizer.py
  pyproject.toml
  .github/workflows/
    test.yml
    release.yml
    publish.yml
```

## Chutes

All chutes invoke AFDKO via the Python API (`from afdko import <tool>; <tool>.main([...])`),
consistent with the approach used in `hellbox-ttfautohint`.

### `MakeOTF`

Wraps `makeotf`. Takes a UFO directory, produces an OTF.

Parameters (all boolean, default `False`):
- `release` → `-r` (subroutinization + applied glyph order)
- `filter_glyphs` → `-gs` (filter output to GOADB glyphs only)
- `omit_mac_names` → `-omitMacNames`

### `Otf2Ttf`

Wraps `otf2ttf`. Takes an OTF, produces a TTF. No parameters.

### `TtfComponentizer`

Wraps `ttfcomponentizer`. Takes a TTF, returns a componentized copy. No parameters.

## Hellfile.py (source-sans)

Installed from local path (`hellbox-afdko` is not on PyPI yet).

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

`hell run build` is the direct equivalent of `./build.sh`.

## Testing

Each chute has a unit test that runs against a real UFO fixture (one instance
from source-sans). Tests use `fontTools.ttLib.TTFont` to assert output validity
(correct table presence) rather than byte equality.

- `test_make_otf.py` — UFO in → OTF out, asserts `CFF ` table present
- `test_otf2ttf.py` — OTF in → TTF out, asserts `glyf` table present
- `test_ttf_componentizer.py` — TTF in → TTF out, runs without error, output is valid

## Out of scope

- Variable font build (deferred — see `hellbox/design/pipeline-multi-file.md`)
- WOFF2 output (not in `build.sh`)
- Hinting (not in `build.sh`)
- PyPI publication (install from path for now)
