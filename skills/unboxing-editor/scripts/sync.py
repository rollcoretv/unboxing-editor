#!/usr/bin/env python3
"""Step 3: audio sync of extra cameras to the main clip.
Usage: sync.py <main_clip> <other_clip> [<other_clip> ...]
Prints offset_s for each: main_time = other_time + offset_s. Accept only when conf > ~3;
otherwise match a visible event (tape rip, box snap) by eye on strips."""
import subprocess, sys, numpy as np

SR, ENV = 4000, 100

def envelope(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    if x.size < SR:
        return None
    hop = SR // ENV
    n = x.size // hop
    e = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-3
    d = np.diff(np.log(e), prepend=np.log(e[0]))
    d[d < 0] = 0  # positive log-diff = onsets
    return d - d.mean()

main = envelope(sys.argv[1])
for other in sys.argv[2:]:
    o = envelope(other)
    if main is None or o is None:
        print(f"{other}: no usable audio"); continue
    n = 1 << int(np.ceil(np.log2(main.size + o.size)))
    cc = np.fft.irfft(np.fft.rfft(main, n) * np.conj(np.fft.rfft(o, n)), n)
    lag = int(np.argmax(cc)); peak = cc[lag]
    srt = np.sort(np.abs(cc))[::-1]
    conf = peak / (srt[49] + 1e-9)
    if lag > n // 2:
        lag -= n
    print(f"{other}: offset_s={lag / ENV:+.2f} conf={conf:.1f} {'OK' if conf > 3 else 'WEAK - verify visually'}")
