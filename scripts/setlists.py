"""Attach setlist.fm lineups/tours/songs to each night in data/shows.json (cached in data/setlist-cache.json)."""
import difflib, json, time, urllib.parse, urllib.request
from datetime import date as Date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
CACHE = DATA / "setlist-cache.json"
KEY = next(l.split("=", 1)[1].strip() for l in (BASE / ".env").read_text().splitlines() if l.startswith("SETLISTFM_KEY="))
UA = {"User-Agent": "concerts-timeline/0.1 (bensonperry.com)"}

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def get(url, headers):
    for attempt in range(6):
        time.sleep(1.0 + attempt * attempt * 3)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if e.code != 429 and e.code < 500:
                raise
    raise RuntimeError(f"gave up on {url}")


def city_for(lat, lon):
    key = f"city:{lat:.3f},{lon:.3f}"
    if key not in cache:
        time.sleep(1.1)
        a = get(f"https://nominatim.openstreetmap.org/reverse?format=json&zoom=10&lat={lat}&lon={lon}", UA).get("address", {})
        cache[key] = a.get("city_district") or a.get("borough") or a.get("city") or a.get("town") or a.get("village")
        CACHE.write_text(json.dumps(cache, indent=1))
    return cache[key]


def setlists_on(day, city):
    key = f"sl:{day}:{city}"
    if key not in cache:
        d = Date.fromisoformat(day).strftime("%d-%m-%Y")
        out, page = [], 1
        while True:
            q = urllib.parse.urlencode({"date": d, "cityName": city, "p": page})
            res = get(f"https://api.setlist.fm/rest/1.0/search/setlists?{q}",
                      {"x-api-key": KEY, "Accept": "application/json"})
            for s in res.get("setlist", []):
                out.append({
                    "artist": s["artist"]["name"],
                    "mbid": s["artist"].get("mbid"),
                    "venue": s["venue"]["name"],
                    "city": s["venue"]["city"]["name"],
                    "tour": (s.get("tour") or {}).get("name"),
                    "songs": [x["name"] for st in s["sets"].get("set", []) for x in st.get("song", []) if x.get("name")],
                    "url": s.get("url"),
                })
            if page * res.get("itemsPerPage", 20) >= res.get("total", 0):
                break
            page += 1
        cache[key] = out
        CACHE.write_text(json.dumps(cache, indent=1))
    return cache[key]


def norm(name):
    return (name or "").lower().replace("the ", "").replace("brooklyn", "").strip(" ,.-")


def main():
    shows = json.loads((DATA / "shows.json").read_text())
    for s in shows:
        if s["lat"] is None:
            continue
        cities = {c for c in (city_for(s["lat"], s["lon"]), "Brooklyn", "New York") if c}
        found = [x for c in cities for x in setlists_on(s["date"], c)]
        venues = sorted({x["venue"] for x in found})
        best = difflib.get_close_matches(norm(s["venue"]), [norm(v) for v in venues], n=1, cutoff=0.6)
        uniq = {}
        for x in found:
            if best and norm(x["venue"]) == best[0]:
                uniq.setdefault((x["artist"], x["venue"]), x)
        here = list(uniq.values())
        s["setlists"] = here
        if here and not s["venue"]:
            s["venue"] = here[0]["venue"]
    (DATA / "shows.json").write_text(json.dumps(shows, indent=1))
    hit = sum(1 for s in shows if s.get("setlists"))
    print(f"{hit}/{len(shows)} nights matched on setlist.fm")
    for s in shows:
        if s.get("setlists"):
            print(s["date"], s["venue"], [x["artist"] for x in s["setlists"]])


if __name__ == "__main__":
    main()
