"""Shared helpers for unboxing-num2 scripts."""
import json, os, subprocess

FPS_NUM, FPS_DEN = 30000, 1001
FRAME = FPS_DEN / FPS_NUM  # seconds per output frame (29.97)
W, H = 1080, 1920
HLG_TRC = "arib-std-b67"

X265 = ["-c:v", "libx265", "-preset", os.environ.get("UNBOX_X265_PRESET", "fast"),
        "-x265-params", "crf=16:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited",
        "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
        "-tag:v", "hvc1"]
AAC = ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2"]
# SDR (Rec.709) -> HLG container per BT.2408 (SDR white = 75% HLG). setparams first: after scale/crop
# the frame's colour tags are often unset and zscale then fails with "no path between colorspaces".
SDR_TO_HLG = ("setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv,"
              "zscale=t=linear:npl=203,format=gbrpf32le,"
              "zscale=p=bt2020:t=arib-std-b67:m=bt2020nc:r=limited:npl=203")


def snap(t):
    """Snap seconds to the 29.97 output frame grid."""
    return round(t / FRAME) * FRAME


def frames(t):
    return int(round(t / FRAME))


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        return None
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w  # display dimensions
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    return {
        "file": os.path.abspath(path),
        "duration": float(j["format"].get("duration", v.get("duration", 0)) or 0),
        "width": w, "height": h, "rotation": rot, "fps": round(fps, 3),
        "color_transfer": v.get("color_transfer", "unknown"),
        "hdr_hlg": v.get("color_transfer") == HLG_TRC,
        "landscape": w > h,
        "has_audio": a is not None,
        "codec": v.get("codec_name"),
        "size_mb": round(int(j["format"].get("size", 0)) / 1e6, 1),
    }


def load_edl(path):
    with open(path) as f:
        edl = json.load(f)
    edl["work_dir"] = os.path.expanduser(edl.get("work_dir", "~/unbox_work/" + edl["product"]))
    os.makedirs(os.path.join(edl["work_dir"], "shots"), exist_ok=True)
    return edl
