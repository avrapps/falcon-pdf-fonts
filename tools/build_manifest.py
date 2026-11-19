#!/usr/bin/env python3
"""
Regenerate v<N>/manifest.json from the font files in v<N>/.

Each face entry is read from the font itself (no hand-written metadata):
family, weight (OS/2 usWeightClass), italic (OS/2 fsSelection / head macStyle),
embedding licence flag (OS/2 fsType), and Unicode coverage (cmap formats 4 / 12,
as merged [start, end] ranges). The app uses `coverage` to pick which face to
download before downloading it, and verifies `sha256` after download.

Usage:  python3 tools/build_manifest.py [--schema 1]
No third-party dependencies.
"""

import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tables(d):
    n = struct.unpack(">H", d[4:6])[0]
    out = {}
    for i in range(n):
        tag, _cs, off, ln = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
        out[tag.decode("latin-1")] = (off, ln)
    return out


def family_name(d, t):
    off, _ = t["name"]
    count, strings = struct.unpack(">HH", d[off + 2:off + 6])
    best, best_score = "", -1
    for i in range(count):
        p, _e, lang, nid, ln, o = struct.unpack(">6H", d[off + 6 + 12 * i:off + 18 + 12 * i])
        if nid not in (1, 16):
            continue
        raw = d[off + strings + o:off + strings + o + ln]
        if p in (0, 3):
            text = raw.decode("utf-16-be", "replace")
        elif p == 1:
            text = raw.decode("mac_roman", "replace")
        else:
            continue
        score = (4 if nid == 16 else 0) + (2 if p == 3 else 0) + (1 if lang == 0x409 or p == 1 else 0)
        if score > best_score:
            best, best_score = text, score
    return best


def coverage(d, t):
    off, _ = t["cmap"]
    n = struct.unpack(">H", d[off + 2:off + 4])[0]
    sub4 = sub12 = None
    for i in range(n):
        p, e, so = struct.unpack(">HHI", d[off + 4 + 8 * i:off + 12 + 8 * i])
        if not (p == 0 or (p == 3 and e in (1, 10))):
            continue
        st = off + so
        fmt = struct.unpack(">H", d[st:st + 2])[0]
        if fmt == 12:
            sub12 = st
        elif fmt == 4 and sub4 is None:
            sub4 = st
    ranges = []
    if sub12 is not None:
        groups = struct.unpack(">I", d[sub12 + 12:sub12 + 16])[0]
        for g in range(groups):
            a, b, _ = struct.unpack(">III", d[sub12 + 16 + 12 * g:sub12 + 28 + 12 * g])
            ranges.append([a, b])
    elif sub4 is not None:
        segx2 = struct.unpack(">H", d[sub4 + 6:sub4 + 8])[0]
        segs = segx2 // 2
        ends = struct.unpack(">%dH" % segs, d[sub4 + 14:sub4 + 14 + segx2])
        starts = struct.unpack(">%dH" % segs, d[sub4 + 16 + segx2:sub4 + 16 + 2 * segx2])
        for a, b in zip(starts, ends):
            if a != 0xFFFF:
                ranges.append([a, b])
    ranges.sort()
    merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def face_entry(path):
    d = path.read_bytes()
    t = tables(d)
    os2 = t["OS/2"][0]
    weight = struct.unpack(">H", d[os2 + 4:os2 + 6])[0]
    fs_type = struct.unpack(">H", d[os2 + 8:os2 + 10])[0]
    fs_selection = struct.unpack(">H", d[os2 + 62:os2 + 64])[0]
    mac_style = struct.unpack(">H", d[t["head"][0] + 44:t["head"][0] + 46])[0]
    family = family_name(d, t)
    lower = family.lower()
    family_class = "mono" if "mono" in lower else ("serif" if "serif" in lower and "sans" not in lower else "sans")
    if fs_type & 0x0002 or fs_type & 0x0200:
        sys.exit(f"{path.name}: licence flag fsType={fs_type:#06x} does not allow embedding")
    if "glyf" not in t:
        sys.exit(f"{path.name}: no TrueType outlines (glyf); the app only embeds TrueType faces")
    return {
        "id": path.stem,
        "file": path.name,
        "bytes": len(d),
        "sha256": hashlib.sha256(d).hexdigest(),
        "family": family,
        "familyClass": family_class,
        "weight": weight,
        "italic": bool(fs_selection & 1 or mac_style & 2),
        "fsType": fs_type,
        "license": "OFL-1.1",
        "coverage": coverage(d, t),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", type=int, default=1)
    args = ap.parse_args()
    folder = ROOT / f"v{args.schema}"
    faces = [face_entry(p) for p in sorted(folder.glob("*.ttf"))]
    if not faces:
        sys.exit(f"no .ttf files in {folder}")
    manifest = {
        "schemaVersion": args.schema,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "faces": faces,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {folder / 'manifest.json'}: {len(faces)} faces")


if __name__ == "__main__":
    main()
