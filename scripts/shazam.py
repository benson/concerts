"""Identify the song in each camera clip -> data/shazam.json (incremental). Args: optional path filter."""
import asyncio, json, subprocess, sys, tempfile
from pathlib import Path
from shazamio import Shazam

ROOT = Path("D:/icloud-videos")
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "shazam.json"


def audio_snippet(video, start, seconds=12):
    tmp = Path(tempfile.gettempdir()) / f"shz_{video.stem}_{start}.ogg"
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", str(start), "-t", str(seconds), "-i", str(video),
                    "-vn", "-ac", "1", "-ar", "16000", str(tmp)], check=False)
    return tmp


async def identify(shazam, v):
    video = ROOT / v["path"]
    dur = v["duration"] or 0
    # try a few offsets: loud live audio often only matches on some windows
    for start in sorted({0, max(0, int(dur / 2) - 6), max(0, int(dur) - 14)}):
        snip = audio_snippet(video, start)
        if not snip.exists():
            continue
        try:
            res = await shazam.recognize(str(snip))
        finally:
            snip.unlink(missing_ok=True)
        track = res.get("track")
        if track:
            return {"artist": track.get("subtitle"), "title": track.get("title"),
                    "album": next((m["text"] for s in track.get("sections", []) if s.get("type") == "SONG"
                                   for m in s.get("metadata", []) if m.get("title") == "Album"), None),
                    "offset": start}
    return None


async def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    videos = [v for v in json.loads((DATA / "videos.json").read_text())
              if v["model"] and flt in v["path"] and v["path"] not in done]
    shazam = Shazam()
    for i, v in enumerate(videos):
        try:
            done[v["path"]] = await identify(shazam, v)
        except Exception as e:
            print("error", v["path"], e)
            continue
        hit = done[v["path"]]
        print(v["path"], "->", f'{hit["artist"]} - {hit["title"]}' if hit else "no match", flush=True)
        if i % 10 == 9:
            OUT.write_text(json.dumps(done, indent=1))
    OUT.write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
