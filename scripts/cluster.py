"""Group camera clips into nights and sets, match venues + tickets -> data/shows.json."""
import json, math, statistics, time, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
GEO_CACHE = DATA / "geo-cache.json"
UA = {"User-Agent": "concerts-timeline/0.1 (bensonperry.com)"}

NIGHT_GAP = timedelta(hours=3)     # a longer gap starts a new night
SET_GAP = timedelta(minutes=12)    # a longer gap inside a night starts a new set
VENUE_RADIUS_M = 250

geo = json.loads(GEO_CACHE.read_text()) if GEO_CACHE.exists() else {}


def fetch(url, data=None, tries=4):
    for attempt in range(tries):
        time.sleep(1.1 + attempt * 5)  # nominatim/overpass politeness
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            err = e
    raise err


def geocode(query):
    if query not in geo:
        res = fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q="
                    + urllib.parse.quote(query))
        geo[query] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
        GEO_CACHE.write_text(json.dumps(geo, indent=1))
    return geo[query]


def venue_coords(tk):
    city = ", ".join((tk.get("venue_address") or "Brooklyn, NY").split(", ")[-2:])
    return geocode(f'{tk["venue"]}, {city}') or geocode(tk["venue_address"] or tk["venue"])


MUSIC_KINDS = ("music_venue", "nightclub", "concert_hall", "theatre", "events_venue", "stadium", "bandstand")


VENUES = DATA / "osm-venues.json"
osm = json.loads(VENUES.read_text()) if VENUES.exists() else {}
KINDS_RE = "nightclub|music_venue|bar|pub|theatre|events_venue|arts_centre|concert_hall|stadium|bandstand"


def region_venues(lat, lon):
    """All named venue-like OSM features in the 0.5-degree cell around a point (one bulk query per cell)."""
    cell = f"{math.floor(lat * 2) / 2},{math.floor(lon * 2) / 2}"
    if cell not in osm:
        s_, w = map(float, cell.split(","))
        bbox = f"({s_ - 0.05},{w - 0.05},{s_ + 0.55},{w + 0.55})"
        q = (f'[out:json][timeout:180];(nwr{bbox}[name][amenity~"^({KINDS_RE})$"];'
             f'nwr{bbox}[name][leisure~"^({KINDS_RE})$"];);out center;')
        res = fetch("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": q}).encode())
        osm[cell] = [[el["tags"]["name"], el.get("center", el)["lat"], el.get("center", el)["lon"],
                      el["tags"].get("amenity") or el["tags"].get("leisure")] for el in res.get("elements", [])]
        VENUES.write_text(json.dumps(osm))
    return osm[cell]


def nearby_venue(lat, lon):
    best = None
    for name, vlat, vlon, kind in region_venues(lat, lon):
        d = dist(lat, lon, vlat, vlon)
        if d > VENUE_RADIUS_M:
            continue
        rank = (kind not in MUSIC_KINDS, d)
        if best is None or rank < best[0]:
            best = (rank, name, round(d), kind)
    return {"name": best[1], "meters": best[2], "kind": best[3]} if best else None


def dist(a_lat, a_lon, b_lat, b_lon):
    r = 6371000
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def split(items, gap):
    groups = []
    for it in items:
        if groups and it["t"] - groups[-1][-1]["t"] <= gap:
            groups[-1].append(it)
        else:
            groups.append([it])
    return groups


def main():
    clips = []
    for v in json.loads((DATA / "videos.json").read_text()):
        if not v["model"] or not v["local"]:
            continue  # saved/screen-recorded, not shot on camera
        v["t"] = datetime.strptime(v["local"], "%Y-%m-%dT%H:%M:%S%z")
        clips.append(v)
    clips.sort(key=lambda v: v["t"])

    tickets = json.loads((DATA / "tickets.json").read_text())["purchases"]
    for tk in tickets:
        tk["coords"] = venue_coords(tk) if tk.get("venue") else None

    shows, rejected = [], []
    for night in split(clips, NIGHT_GAP):
        start = night[0]["t"]
        evening = [c for c in night if c["t"].hour >= 17 or c["t"].hour < 4]
        if len(night) < 2 or not evening:
            continue
        # a show after midnight belongs to the previous date
        date = (start - timedelta(hours=4)).date().isoformat()
        gps = [c for c in night if c["lat"] is not None]
        lat = statistics.median(c["lat"] for c in gps) if gps else None
        lon = statistics.median(c["lon"] for c in gps) if gps else None

        ticket = None
        for tk in tickets:
            if tk["date"] != date:
                continue
            if lat is None or not tk["coords"] or dist(lat, lon, *tk["coords"]) < 1500:
                ticket = tk
                break
        near = nearby_venue(lat, lon) if lat is not None and not ticket else None
        if ticket:
            venue = ticket["venue"]
        elif near and (near["kind"] in MUSIC_KINDS or near["meters"] <= 60):
            venue = near["name"]
        else:
            rejected.append({"date": date, "lat": lat, "lon": lon, "clips": len(night), "near": near})
            venue = None

        sets = split(night, SET_GAP)
        lineup = list(reversed(ticket["lineup"])) if ticket else []  # listed headliner-first
        if lineup and len(sets) == len(lineup):
            match = "exact"
        elif lineup:
            match = "count-mismatch"
        else:
            match = "no-lineup"

        shows.append({
            "date": date,
            "maybe_not_show": venue is None,
            "nearest_place": near,
            "venue": venue,
            "lat": lat, "lon": lon,
            "ticket": {k: ticket[k] for k in ("lineup", "seller", "status")} if ticket else None,
            "match": match,
            "sets": [{
                "band": lineup[i] if match == "exact" else None,
                "start": s[0]["local"], "end": s[-1]["local"],
                "clips": [c["path"] for c in s],
            } for i, s in enumerate(sets)],
        })

    GEO_CACHE.write_text(json.dumps(geo, indent=1))
    (DATA / "shows.json").write_text(json.dumps(shows, indent=1))
    (DATA / "not-shows.json").write_text(json.dumps(rejected, indent=1))
    print(f"{len(rejected)} evening clusters set aside as not-a-show")
    by = {}
    for s in shows:
        by[s["match"]] = by.get(s["match"], 0) + 1
    print(f"{len(shows)} candidate nights:", by)
    for s in shows:
        print(s["date"], s["venue"], f'{len(s["sets"])} sets /',
              len(s["ticket"]["lineup"]) if s["ticket"] else "-", "bands", s["match"])


if __name__ == "__main__":
    main()
