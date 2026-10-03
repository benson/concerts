"""Per-night evidence bundle for the resolver agents -> data/nights/<date>/{evidence.json, set<N>.jpg}."""
import json, subprocess
from pathlib import Path

import numpy as np

ROOT = Path("D:/icloud-videos")
DATA = Path(__file__).resolve().parent.parent / "data"
NIGHTS = DATA / "nights"


def sheet(clips, videos, out):
    """Up to 6 frames across the set's clips, side by side, 600px tall."""
    picks = []
    for c in clips:
        d = videos[c]["duration"] or 2
        picks += [(c, d * 0.3), (c, d * 0.7)] if len(clips) <= 3 else [(c, d * 0.5)]
    picks = picks[:6]
    tmp = []
    for i, (c, t) in enumerate(picks):
        f = out.parent / f"_f{i}.jpg"
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{t:.2f}", "-i", str(ROOT / c), "-frames:v", "1",
                        "-vf", "scale=-2:600", str(f)])
        if f.exists():
            tmp.append(f)
    if not tmp:
        return None
    args = sum([["-i", str(f)] for f in tmp], [])
    flt = "".join(f"[{i}]scale=-2:600[s{i}];" for i in range(len(tmp))) + \
          "".join(f"[s{i}]" for i in range(len(tmp))) + f"hstack=inputs={len(tmp)}" if len(tmp) > 1 else "scale=-2:600"
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", *args, "-filter_complex", flt, "-frames:v", "1", str(out)])
    for f in tmp:
        f.unlink()
    return str(out)


def main():
    shows = json.loads((DATA / "shows.json").read_text())
    videos = {v["path"]: v for v in json.loads((DATA / "videos.json").read_text())}
    trans = json.loads((DATA / "transcripts.json").read_text(encoding="utf-8"))
    aud = dict(np.load(DATA / "embeddings" / "clap.npz"))
    tickets = json.loads((DATA / "tickets.json").read_text())

    seen = {}
    for s in shows:
        seen[s["date"]] = seen.get(s["date"], 0) + 1
        s["night_id"] = s["date"] if seen[s["date"]] == 1 else f'{s["date"]}-{seen[s["date"]]}'
        d = NIGHTS / s["night_id"]
        d.mkdir(parents=True, exist_ok=True)
        sets = []
        for i, st in enumerate(s["sets"]):
            speech = {c: " / ".join(x["text"] for x in trans.get(c, {}).get("segments", []) if x["p"] > -0.8)
                      for c in st["clips"]}
            sets.append({
                "set": i, "start": st["start"][11:16], "end": st["end"][11:16],
                "clips": [{"path": c, "time": videos[c]["local"][11:19], "seconds": round(videos[c]["duration"] or 0),
                           "speech": speech[c] or None} for c in st["clips"]],
                "frames": sheet(st["clips"], videos, d / f"set{i}.jpg"),
            })
        # audio similarity between sets, centered on the night (separates bands; ~+0.6 same band, <0 different)
        embs = [np.mean([aud[c] for c in st["clips"] if c in aud], 0) if any(c in aud for c in st["clips"]) else None
                for st in s["sets"]]
        ok = [e for e in embs if e is not None]
        sim = None
        if len(ok) > 1:
            mu = np.mean(ok, 0)
            X = [None if e is None else (e - mu) / np.linalg.norm(e - mu) for e in embs]
            sim = [[None if a is None or b is None else round(float(a @ b), 2) for b in X] for a in X]
        ev = {
            "night_id": s["night_id"], "date": s["date"],
            "maybe_not_show": s.get("maybe_not_show"), "nearest_place": s.get("nearest_place"), "venue": s["venue"], "lat": s["lat"], "lon": s["lon"],
            "tickets": [t for t in tickets["purchases"] if t["date"] == s["date"]],
            "setlist_fm": s.get("setlists"),
            "sets": sets,
            "set_audio_similarity": sim,
        }
        (d / "evidence.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(shows), "nights written to", NIGHTS)


if __name__ == "__main__":
    main()
