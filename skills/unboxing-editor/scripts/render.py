#!/usr/bin/env python3
"""Step 6: render shots from edl.json into <work_dir>/shots/NNN.mp4 (+ black.mp4).
Usage: render.py edl.json [--only 0-6] [--jobs 2] [--force]
Skips shots already rendered (so it can be re-run in small batches under a call time limit).
The LAST shot gets the fade-out (video to black + audio) baked in, so assembly stays a stream copy."""
import argparse, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from common import load_edl, probe, snap, X265, AAC, SDR_TO_HLG, W, H

ap = argparse.ArgumentParser()
ap.add_argument("edl"); ap.add_argument("--only"); ap.add_argument("--jobs", type=int, default=2)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
edl = load_edl(a.edl)
shots = edl["shots"]
work = edl["work_dir"]
fade = float(edl.get("fade_s", 0.7))
info = {k: probe(s["file"]) for k, s in edl["sources"].items()}


def atempo(sp):
    parts = []
    while sp > 2.0:
        parts.append("atempo=2.0"); sp /= 2.0
    parts.append(f"atempo={sp:.4f}")
    return ",".join(parts)


def cmd_for(i, s):
    src = edl["sources"][s["src"]]; p = info[s["src"]]
    sp = float(s.get("speed", 1.0)); dur = snap(float(s["dur"])); t_in = float(s["in"])
    last = i == len(shots) - 1
    vf = []
    if sp != 1.0:
        vf.append(f"setpts=PTS/{sp}")
    vf.append("fps=30000/1001")
    if src.get("landscape", p["landscape"]):
        x0 = s.get("crop_x0")
        x = str(int(x0)) if x0 is not None else "(iw-ih*9/16)/2"
        vf.append(f"crop=ih*9/16:ih:{x}:0")
        vf.append(f"scale={W}:{H}:flags=lanczos")
    else:  # vertical: keep framing, only fit to 1080x1920 (centre-crop if aspect differs)
        vf.append(f"scale={W}:{H}:flags=lanczos:force_original_aspect_ratio=increase,crop={W}:{H}")
    if not p["hdr_hlg"]:
        vf.append(SDR_TO_HLG)
    vf.append("format=yuv420p10le")
    af = []
    if sp != 1.0:
        af.append(atempo(sp))
    af.append("aresample=48000,aformat=channel_layouts=stereo")
    if last and fade > 0:
        st = max(0.0, dur - fade)
        vf.append(f"fade=t=out:st={st:.3f}:d={fade:.3f}")
        af.append(f"afade=t=out:st={st:.3f}:d={fade:.3f}")
    c = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t_in:.3f}", "-t", f"{dur * sp + 0.2:.3f}", "-i", src["file"]]
    if p["has_audio"]:
        amap = "0:a:0"
    else:
        c += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]; amap = "1:a:0"
    c += ["-map", "0:v:0", "-map", amap, "-vf", ",".join(vf), "-af", ",".join(af),
          "-t", f"{dur:.4f}"] + X265 + AAC + [os.path.join(work, "shots", f"{i:03d}.mp4")]
    return c


def black_cmd():
    d = snap(float(edl.get("black_s", 0.3)))
    return ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:r=30000/1001",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", "format=yuv420p10le",
            "-t", f"{d:.4f}"] + X265 + AAC + [os.path.join(work, "shots", "black.mp4")]


idx = range(len(shots))
if a.only:
    lo, _, hi = a.only.partition("-")
    idx = range(int(lo), int(hi or lo) + 1)
jobs = []
for i in idx:
    out = os.path.join(work, "shots", f"{i:03d}.mp4")
    if a.force or not os.path.exists(out):
        jobs.append((f"{i:03d}", cmd_for(i, shots[i])))
if a.force or not os.path.exists(os.path.join(work, "shots", "black.mp4")):
    jobs.append(("black", black_cmd()))

def run(job):
    # Write to .part and rename only on success: a render killed by a call time limit or an ffmpeg
    # error must never leave a file that later batches would skip as "already rendered".
    name, c = job; t = time.time(); final = c[-1]; part = final[:-4] + ".part.mp4"
    r = subprocess.run(c[:-1] + [part], capture_output=True, text=True)
    if r.returncode == 0:
        os.replace(part, final)
    elif os.path.exists(part):
        os.remove(part)
    return name, r.returncode, time.time() - t, r.stderr[-400:]

fail = 0
with ThreadPoolExecutor(a.jobs) as ex:
    for name, rc, dt, err in ex.map(run, jobs):
        print(f"{name}: {'ok' if rc == 0 else 'FAIL'} {dt:.0f}s" + ("" if rc == 0 else " " + err))
        fail += rc != 0
done = sum(os.path.exists(os.path.join(work, "shots", f"{i:03d}.mp4")) for i in range(len(shots)))
print(f"rendered {done}/{len(shots)} shots" + (f", {fail} failed" if fail else ""))
sys.exit(1 if fail else 0)
