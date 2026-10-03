"""Read time/GPS/duration from every downloaded video into data/videos.json (incremental)."""
import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "D:/icloud-videos")
OUT = Path(__file__).resolve().parent.parent / "data" / "videos.json"
VIDEO_EXT = {".mov", ".mp4", ".m4v"}


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
                       capture_output=True, text=True)
    fmt = json.loads(r.stdout or "{}").get("format", {})
    tags = fmt.get("tags", {})
    lat = lon = None
    m = re.match(r"([+-]\d+\.\d+)([+-]\d+\.\d+)", tags.get("com.apple.quicktime.location.ISO6709", ""))
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "local": tags.get("com.apple.quicktime.creationdate"),
        "utc": tags.get("creation_time"),
        "lat": lat,
        "lon": lon,
        "duration": float(fmt["duration"]) if fmt.get("duration") else None,
        "size": int(fmt["size"]) if fmt.get("size") else path.stat().st_size,
        "model": tags.get("com.apple.quicktime.model"),
    }


def main():
    known = {v["path"]: v for v in json.loads(OUT.read_text())} if OUT.exists() else {}
    todo = [p for p in ROOT.rglob("*")
            if p.suffix.lower() in VIDEO_EXT
            and str(p.relative_to(ROOT)).replace("\\", "/") not in known]
    with ThreadPoolExecutor(8) as pool:
        for v in pool.map(probe, todo):
            known[v["path"]] = v
    videos = sorted(known.values(), key=lambda v: v["utc"] or "")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(videos, indent=1))
    print(f"{len(todo)} new, {len(videos)} total, "
          f"{sum(1 for v in videos if v['lat'] is None)} without GPS")


if __name__ == "__main__":
    main()
