# falcon-pdf-fonts

Fallback fonts that **Falcon PDF** downloads on demand for **Edit > Text**.

When a user types a character the PDF's own font can't draw (for example a Cyrillic or
Polish letter in a document whose embedded font was trimmed to Latin), the app tries, in order:

1. the PDF's own font,
2. a standard PDF font (Helvetica / Times / Courier; Western European characters only),
3. a font installed on the device, if its licence allows embedding,
4. **a face from this repo**, downloaded once and cached.

The chosen face is embedded in the edited PDF, so the document looks the same everywhere.
Design: `PDFViewer/docs/tasks/edit-text-rebuild.md` (§2.3) in the main app repo.

## Contents

```
v1/manifest.json        face index: id, file, bytes, sha256, family, familyClass,
                        weight, italic, fsType, license, Unicode coverage ranges
v1/<face-id>.ttf        the font files
tools/build_manifest.py regenerates v1/manifest.json from the font files
LICENSE                 SIL Open Font License 1.1 (Liberation fonts)
```

`v<N>/` is the manifest **schema** version. The app pins its schema version, reads
`v<N>/manifest.json`, picks a face by `familyClass` / `weight` / `italic` / `coverage`,
downloads it and checks `sha256`.

### Faces (v1)

**Liberation 2.1.5**: Sans, Serif and Mono, each in Regular, Bold, Italic and Bold Italic
(12 faces, ~0.3–0.4 MB each). Liberation has the same character widths as Arial/Helvetica,
Times New Roman and Courier New, so edited paragraphs wrap like the originals. Coverage:
Latin (including Central European and Vietnamese), Greek, Cyrillic.

Not included yet: Chinese/Japanese/Korean (needs font trimming in the app first, as
whole CJK fonts are ~16 MB), and scripts that need text shaping (Indic, Arabic, Thai).

## How the app downloads

Through the jsDelivr CDN, pinned to a tag (same pattern as `falcon-pdf-strings`):

```
https://cdn.jsdelivr.net/gh/avrapps/falcon-pdf-fonts@<tag>/v1/manifest.json
https://cdn.jsdelivr.net/gh/avrapps/falcon-pdf-fonts@<tag>/v1/<file>
```

## Updating

1. Add or replace `.ttf` files in `v1/` (TrueType outlines only; licence must allow embedding).
2. `python3 tools/build_manifest.py` (it refuses fonts whose licence flag forbids embedding).
3. Commit on a branch, open a PR, merge, then move the release tag the app pins.

## Licence

The fonts are licensed under the **SIL Open Font License 1.1** (see `LICENSE`).
"Liberation" is a Reserved Font Name: the files are redistributed unmodified. Embedding
them in documents is permitted by the OFL.
