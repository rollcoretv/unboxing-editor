#!/usr/bin/env python3
"""Step 2/4: contact sheets with burned timestamps (seconds of the SOURCE clip).
  coarse: sheets.py coarse <clip> <out.jpg> [--every 3] [--tile 128]
  strip:  sheets.py strip  <clip> <out.jpg> --start S --end E [--every 0.5] [--tile 200]
Uses one fast input-seek per frame in parallel, so it works for long-GOP 4K (Sony/DJI) and iPhone alike.
Sheets are for judging action/framing only; HLG frames look flat, that is expected."""
import argparse, os, subprocess, tempfile, math
from concurrent.futures import ThreadPoolExecutor
from common import probe

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["coarse", "strip"])
ap.add_argument("clip"); ap.add_argument("out")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float)
ap.add_argument("--every", type=float)
ap.add_argument("--tile", type=int)
ap.add_argument("--cols", type=int)
ap.add_argument("--jobs", type=int, default=4)
a = ap.parse_args()

p = probe(a.clip)
end = min(a.end or p["duration"], p["duration"] - 0.05)
every = a.every or (3.0 if a.mode == "coarse" else 0.5)
tile = a.tile or (128 if a.mode == "coarse" else 200)
times = [a.start + i * every for i in range(int((end - a.start) / every) + 1)]
cols = a.cols or (12 if a.mode == "coarse" else 20)  # strip: 40 frames -> 2 rows of 20
tmp = tempfile.mkdtemp(prefix="sheet_")

def grab(i_t):
    i, t = i_t
    dst = os.path.join(tmp, f"{i:05d}.jpg")
    vf = (f"scale=-2:{tile}," if p["height"] >= p["width"] else f"scale=-2:{tile},") + \
         f"drawtext=text='{t:.1f}':x=4:y=4:fontsize={max(12, tile // 8)}:fontcolor=yellow:box=1:boxcolor=black@0.6"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", a.clip, "-frames:v", "1",
                    "-vf", vf, "-q:v", "4", dst], check=False)
    return dst

with ThreadPoolExecutor(a.jobs) as ex:
    list(ex.map(grab, enumerate(times)))
rows = math.ceil(len(times) / cols)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%05d.jpg"),
                "-vf", f"tile={cols}x{rows}:padding=2:color=gray", "-frames:v", "1", "-q:v", "3", a.out], check=True)
print(f"{a.out}: {len(times)} frames, {a.start:.1f}-{end:.1f}s every {every}s, {cols}x{rows}")
