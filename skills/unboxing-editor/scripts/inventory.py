#!/usr/bin/env python3
"""Step 1: probe every video in a folder. Usage: inventory.py <folder> [work_dir]
Prints a table and writes inventory.json into work_dir (default ~/unbox_work/<folder name>)."""
import json, os, sys
from common import probe

EXT = (".mov", ".mp4", ".m4v", ".mts", ".mxf", ".avi", ".mkv")
folder = sys.argv[1]
work = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/unbox_work/" + os.path.basename(os.path.normpath(folder)))
os.makedirs(work, exist_ok=True)
rows = {}
for name in sorted(os.listdir(folder)):
    if name.startswith(".") or not name.lower().endswith(EXT):
        continue
    try:
        p = probe(os.path.join(folder, name))
    except Exception as e:
        print(f"!! {name}: {e}")
        continue
    if p:
        rows[name] = p
print(f"{'file':40} {'dur':>7} {'WxH':>11} {'fps':>7} {'trc':>13} {'aud':>4} {'MB':>7}")
for n, p in rows.items():
    print(f"{n[:40]:40} {p['duration']:7.1f} {p['width']:>5}x{p['height']:<5} {p['fps']:7.2f} "
          f"{p['color_transfer'][:13]:>13} {'y' if p['has_audio'] else 'n':>4} {p['size_mb']:7.0f}")
json.dump(rows, open(os.path.join(work, "inventory.json"), "w"), indent=1)
print(f"\n{len(rows)} clips, {sum(p['duration'] for p in rows.values()):.0f}s total -> {work}/inventory.json")
