#!/usr/bin/env python3
"""Step 0: verify the toolchain before editing. Usage: check_env.py
Exits 1 and prints exactly what is missing (never silently falls back to a different look)."""
import shutil, subprocess, sys

def out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout + subprocess.run(cmd, capture_output=True, text=True).stderr

problems = []
for tool in ("ffmpeg", "ffprobe"):
    if not shutil.which(tool):
        problems.append(f"{tool} not found (macOS: brew install ffmpeg)")
if not problems:
    if "libx265" not in out(["ffmpeg", "-hide_banner", "-encoders"]):
        problems.append("ffmpeg has no libx265 encoder")
    if "zscale" not in out(["ffmpeg", "-hide_banner", "-filters"]):
        problems.append("ffmpeg has no zscale filter (needs libzimg). Needed to place SDR clips in the HLG container; "
                        "iPhone HLG-only projects still work. Use an ffmpeg build with libzimg.")
try:
    import numpy  # noqa: F401
except ImportError:
    problems.append("python3 numpy missing (pip3 install numpy)")
print("OK: toolchain ready" if not problems else "\n".join("MISSING: " + p for p in problems))
sys.exit(1 if problems else 0)
