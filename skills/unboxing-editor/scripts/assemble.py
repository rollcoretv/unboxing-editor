#!/usr/bin/env python3
"""Steps 7+9: assemble hook -> black -> rest (stream copy) and verify.
Usage: assemble.py edl.json
Writes <out_dir>/<Product>_Unboxing.mp4 and <work_dir>/review.jpg (middle frame of every shot, labelled)."""
import os, re, subprocess, sys
from common import load_edl, probe

edl = load_edl(sys.argv[1]); work = edl["work_dir"]; shots = edl["shots"]
sd = os.path.join(work, "shots")
missing = [i for i in range(len(shots)) if not os.path.exists(os.path.join(sd, f"{i:03d}.mp4"))]
if missing or not os.path.exists(os.path.join(sd, "black.mp4")):
    sys.exit(f"not rendered yet: {missing or ''} {'black' if not os.path.exists(os.path.join(sd, 'black.mp4')) else ''}")
hooks = [i for i, s in enumerate(shots) if s.get("stage") == "hook"]
if not hooks or hooks[0] != 0:
    sys.exit("edl must start with the hook shot(s) (stage='hook')")
order = [f"{i:03d}.mp4" for i in hooks] + ["black.mp4"] + [f"{i:03d}.mp4" for i in range(len(shots)) if i not in hooks]
lst = os.path.join(work, "concat.txt")
open(lst, "w").write("".join(f"file '{os.path.join(sd, n)}'\n" for n in order))
out_dir = os.path.expanduser(edl.get("out_dir") or os.path.dirname(next(iter(edl["sources"].values()))["file"]))
out = os.path.join(out_dir, f"{edl['product']}_Unboxing.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                "-movflags", "+faststart", out], check=True)

p = probe(out)
vol = subprocess.run(["ffmpeg", "-i", out, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
mean = re.search(r"mean_volume: ([-\d.]+)", vol)
nb = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                     "stream=nb_read_packets", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
# review sheet
tmp = os.path.join(work, "review"); os.makedirs(tmp, exist_ok=True)
for k, n in enumerate(order):
    f = os.path.join(sd, n); d = probe(f)["duration"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d / 2:.3f}", "-i", f, "-frames:v", "1", "-vf",
                    f"scale=-2:240,drawtext=text='{n[:-4]}':x=4:y=4:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6",
                    os.path.join(tmp, f"{k:03d}.jpg")], check=False)
cols = 10; rows = -(-len(order) // cols)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", os.path.join(tmp, "%03d.jpg"), "-vf",
                f"tile={cols}x{rows}:padding=2:color=gray", "-frames:v", "1", os.path.join(work, "review.jpg")], check=False)
print(f"OUT {out}\nduration {p['duration']:.2f}s  frames {nb}  shots {len(shots)} (+black)  "
      f"hlg={p['hdr_hlg']}  audio_mean={mean.group(1) if mean else 'NONE'} dB\nreview {work}/review.jpg")
