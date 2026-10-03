"""Merge resolved nights, orphan clips and ticket-only shows -> site/data/catalog.json."""
import glob, json
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "site" / "data" / "catalog.json"


def clip_id(path):
    return path.rsplit(".", 1)[0].replace("/", "_")


def main():
    videos = {v["path"]: v for v in json.loads((DATA / "videos.json").read_text())}
    evidence = {}
    for f in glob.glob(str(DATA / "nights" / "*" / "evidence.json")):
        e = json.loads(Path(f).read_text(encoding="utf-8"))
        evidence[e["night_id"]] = e
    shows = {}
    for f in sorted(glob.glob(str(DATA / "nights" / "*" / "resolved.json"))):
        r = json.loads(Path(f).read_text(encoding="utf-8"))
        if not r.get("is_show"):
            continue
        ev = evidence.get(r["night_id"], {})
        clips = []
        for p, x in r["clips"].items():
            if x.get("not_show"):
                continue
            v = videos.get(p, {})
            clips.append({"id": clip_id(p), "time": (v.get("local") or "")[11:16] or None,
                          "seconds": round(v.get("duration") or 0), "band": x.get("band"),
                          "song": x.get("song"), "confidence": x.get("confidence")})
        clips.sort(key=lambda c: (c["time"] is None, c["time"] or "", c["id"]))
        shows[r["night_id"]] = {
            "id": r["night_id"], "date": r["date"], "venue": r.get("venue"), "city": r.get("city"),
            "lat": ev.get("lat"), "lon": ev.get("lon"), "event": r.get("event"),
            "lineup": sorted(r.get("lineup") or [], key=lambda b: b.get("play_order") or 99),
            "clips": clips,
        }

    orph = DATA / "orphans.json"
    for o in []:  # clips other people sent stay out of the public site
        if o.get("night_id") in shows:
            shows[o["night_id"]]["clips"].append({"id": clip_id(o["path"]), "time": None,
                                                  "seconds": round(videos[o["path"]]["duration"] or 0),
                                                  "band": None, "song": None, "confidence": None, "shared": True})

    dates = {s["date"] for s in shows.values()}
    for t in json.loads((DATA / "tickets.json").read_text())["purchases"]:
        if t["status"] in ("sold", "cancelled", "postponed") or t["date"] in dates or t["date"] > str(date.today()):
            continue
        sid = f'{t["date"]}-ticket'
        clips = [{"id": clip_id(o["path"]), "time": None, "seconds": round(videos[o["path"]]["duration"] or 0),
                  "band": None, "song": None, "confidence": None, "shared": True}
                 for o in []
                 if (o.get("ticket") or {}).get("date") == t["date"]]
        shows[sid] = {"id": sid, "date": t["date"], "venue": t["venue"], "city": None, "lat": None, "lon": None,
                      "event": None, "lineup": [{"band": b, "play_order": None, "tour": None} for b in t["lineup"]],
                      "clips": clips, "ticket_only": not clips}

    venues = {}
    for s in shows.values():
        if s["lat"] is not None and s["venue"]:
            venues.setdefault(s["venue"], [s["lat"], s["lon"]])
    for s in shows.values():  # ticket-only shows at a venue we have coordinates for
        if s["lat"] is None and s["venue"] in venues:
            s["lat"], s["lon"] = venues[s["venue"]]

    out = sorted(shows.values(), key=lambda s: s["date"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f'{len(out)} shows ({sum(1 for s in out if s.get("ticket_only"))} ticket-only), '
          f'{sum(len(s["clips"]) for s in out)} clips')


if __name__ == "__main__":
    main()
