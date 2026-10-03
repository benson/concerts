"""Thumbnails (site/media/t) + 720p H.264 proxies (D:/concerts-proxies) for every show clip. Incremental."""
import glob, json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROOT = Path("D:/icloud-videos")
THUMBS = BASE / "site" / "media" / "t"
PROXIES = Path("D:/concerts-proxies")


def clip_id(path):
    return path.rsplit(".", 1)[0].replace("/", "_")


def show_clips():
    out = set()
    for f in glob.glob(str(BASE / "data" / "nights" / "*" / "resolved.json")):
        r = json.loads(Path(f).read_text(encoding="utf-8"))
        if r.get("is_show"):
            out |= {p for p, x in r["clips"].items() if not x.get("not_show")}
    return sorted(out)


TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,")


def video_filter(src, height):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                        "-of", "csv=p=0", str(src)], capture_output=True, text=True)
    hdr = r.stdout.strip().strip(",") in ("arib-std-b67", "smpte2084")
    scale = f"scale=-2:'min({height},ih)'"
    return f"{scale}," + (TONEMAP if hdr else "") + "format=yuv420p"


def make(path):
    cid, src = clip_id(path), ROOT / path
    thumb, proxy = THUMBS / f"{cid}.jpg", PROXIES / f"{cid}.mp4"
    if not thumb.exists():
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", "1", "-i", str(src), "-frames:v", "1",
                        "-vf", video_filter(src, 360), "-q:v", "4", str(thumb)])
    if not proxy.exists():
        tmp = proxy.with_suffix(".part.mp4")
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                            "-vf", video_filter(src, 720), "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "30", "-fpsmax", "30",
                            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)])
        if r.returncode == 0:
            tmp.rename(proxy)
    return path


def main():
    THUMBS.mkdir(parents=True, exist_ok=True)
    PROXIES.mkdir(parents=True, exist_ok=True)
    clips = show_clips()
    with ThreadPoolExecutor(8) as pool:
        for i, _ in enumerate(pool.map(make, clips)):
            if i % 50 == 49:
                print(f"{i + 1}/{len(clips)}", flush=True)
    print(f"done {len(clips)}")


if __name__ == "__main__":
    main()
