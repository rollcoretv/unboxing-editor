# Unboxing Editor (Claude Code plugin)

Turns a folder of raw unboxing / product clips into a short **cut-only 9:16 rough cut** (Reels, Shorts, TikTok), then hands you an **FCPXML** to finish in Final Cut Pro.

Claude does the editorial judgment (hook, story order, best takes, trimming); bundled scripts do the ffmpeg work. Footage never leaves your machine: Claude only sees small contact sheets.

## Install

```
/plugin marketplace add rollcoretv/unboxing-editor
/plugin install unboxing-editor@unboxing-editor-marketplace
```

## Use

Point Claude at a folder of clips:

> Make an unboxing reel from ~/Movies/OsmoPocket

You get `<Product>_Unboxing.mp4` and `<Product>_Unboxing.fcpxml` next to the clips. Arabic works too ("سو مونتاج فتح صندوق لهذا المجلد").

## Requirements

- macOS (the FCPXML targets Final Cut Pro; the MP4 path works anywhere ffmpeg does)
- `ffmpeg` and `ffprobe` with **libx265** and **zscale (libzimg)**: `brew install ffmpeg`
- Python 3 with `numpy` (`pip3 install numpy`)

Claude runs `scripts/check_env.py` first and tells you what is missing.

## Output spec

1080x1920, 29.97 fps, HEVC 10-bit HLG (BT.2020), AAC 256k. iPhone HLG stays HLG; SDR clips are placed in HLG per BT.2408.

## Default style

Hard cuts only, original audio, no text/music/LUTs/stabilisation, black frame after the hook, fade-out at the end, shortest edit that tells the whole story. See `skills/unboxing-editor/SKILL.md` to adapt it.

## Notes

- Raw footage is never modified; scratch goes to `~/unbox_work/<Product>`.
- 4K x265 rendering is slow (roughly 20-30 s per shot); `UNBOX_X265_PRESET` changes the preset (default `fast`).

## License

MIT
