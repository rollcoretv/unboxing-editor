#!/usr/bin/env python3
"""Step 8: write <out_dir>/<Product>_Unboxing.fcpxml (FCPXML 1.10) referencing the ORIGINAL clips.
Usage: fcpxml.py edl.json [--mac-root /Users/x/...]  (use --mac-root only if source paths in edl differ from Mac paths)
Hook -> gap (renders black) -> rest. Audio fade-out on the last clip; the video fade is left as a marker
('Fade out Xs') because FCP applies it with one drag of the clip's opacity handle."""
import argparse, os, urllib.parse
from xml.sax.saxutils import escape
from common import load_edl, probe, frames, FPS_DEN, FPS_NUM, W, H

ap = argparse.ArgumentParser(); ap.add_argument("edl"); ap.add_argument("--mac-root")
a = ap.parse_args()
edl = load_edl(a.edl); shots = edl["shots"]
fade = float(edl.get("fade_s", 0.7)); black = float(edl.get("black_s", 0.3))

def ft(t):  # seconds -> frame-snapped rational on the sequence grid
    return f"{frames(t) * FPS_DEN}/{FPS_NUM}s"

def raw(t):  # un-snapped source time
    return f"{int(round(t * 30000))}/30000s"

def url(path):
    if a.mac_root:
        path = os.path.join(a.mac_root, os.path.basename(path))
    return "file://" + urllib.parse.quote(path)

res = [f'<format id="rSeq" name="FFVideoFormatRateUndefined" frameDuration="{FPS_DEN}/{FPS_NUM}s" '
       f'width="{W}" height="{H}" colorSpace="9-18-9"/>']
info = {}
for k, s in edl["sources"].items():
    p = probe(s["file"]); info[k] = p
    fd = f"{int(round(100000 / p['fps']))}/100000s" if p["fps"] else f"{FPS_DEN}/{FPS_NUM}s"
    cs = ' colorSpace="9-18-9"' if p["hdr_hlg"] else ' colorSpace="1-1-1 (Rec. 709)"'
    res.append(f'<format id="f_{k}" frameDuration="{fd}" width="{p["width"]}" height="{p["height"]}"{cs}/>')
    res.append(f'<asset id="a_{k}" name="{escape(os.path.basename(s["file"]))}" start="0s" duration="{raw(p["duration"])}" '
               f'hasVideo="1" hasAudio="{1 if p["has_audio"] else 0}" format="f_{k}" audioSources="1" '
               f'audioChannels="2" audioRate="48000"><media-rep kind="original-media" src="{url(s["file"])}"/></asset>')

hooks = [i for i, s in enumerate(shots) if s.get("stage") == "hook"]
order = hooks + ["black"] + [i for i in range(len(shots)) if i not in hooks]
spine, off = [], 0
for n, i in enumerate(order):
    if i == "black":
        d = frames(black); spine.append(f'<gap name="Black" offset="{off * FPS_DEN}/{FPS_NUM}s" start="3600s" '
                                         f'duration="{d * FPS_DEN}/{FPS_NUM}s"/>'); off += d; continue
    s = shots[i]; p = info[s["src"]]; sp = float(s.get("speed", 1.0)); d = frames(float(s["dur"]))
    inner = []
    start = float(s["in"])
    if sp != 1.0:
        ad = p["duration"]
        inner.append(f'<timeMap><timept time="0s" value="0s" interp="linear"/>'
                     f'<timept time="{raw(ad / sp)}" value="{raw(ad)}" interp="linear"/></timeMap>')
        start = start / sp
    if edl["sources"][s["src"]].get("landscape", p["landscape"]):
        cw = p["height"] * 9 / 16
        x0 = s.get("crop_x0"); x0 = (p["width"] - cw) / 2 if x0 is None else float(x0)
        P = (p["width"] / 2 - (x0 + cw / 2)) * (H / p["height"]) / H * 100
        inner.append(f'<adjust-conform type="fill"/><adjust-transform position="{P:.3f} 0"/>')
    else:
        inner.append('<adjust-conform type="fill"/>')
    last = n == len(order) - 1
    if last and fade > 0:
        inner.append(f'<adjust-volume><param name="amount" value="0dB"><fadeOut type="easeIn" duration="{ft(fade)}"/></param></adjust-volume>')
        inner.append(f'<marker start="{ft(start + (frames(float(s["dur"])) * FPS_DEN / FPS_NUM) - fade)}" duration="{FPS_DEN}/{FPS_NUM}s" value="Fade out {fade}s"/>')
    note = escape(s.get("note", "") or f'{s.get("stage", "")}')
    spine.append(f'<asset-clip ref="a_{s["src"]}" offset="{off * FPS_DEN}/{FPS_NUM}s" name="{i:03d} {note}" '
                 f'start="{ft(start)}" duration="{d * FPS_DEN}/{FPS_NUM}s" format="f_{s["src"]}" tcFormat="NDF">'
                 + "".join(inner) + '</asset-clip>')
    off += d

name = f"{edl['product']}_Unboxing"
xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">\n<resources>\n'
       + "\n".join(res) + '\n</resources>\n<library><event name="Unboxing"><project name="' + escape(name) + '">'
       f'<sequence format="rSeq" duration="{off * FPS_DEN}/{FPS_NUM}s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">'
       '<spine>\n' + "\n".join(spine) + '\n</spine></sequence></project></event></library>\n</fcpxml>\n')
out_dir = os.path.expanduser(edl.get("out_dir") or os.path.dirname(next(iter(edl["sources"].values()))["file"]))
out = os.path.join(out_dir, name + ".fcpxml")
open(out, "w").write(xml)
print(f"OUT {out}  ({len(spine)} items, {off * FPS_DEN / FPS_NUM:.2f}s)")
