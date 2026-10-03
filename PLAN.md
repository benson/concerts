# concerts

Timeline/map of every show Benson has filmed, each video tagged with band, song, date, venue, tour.

## Principle
Every avenue is automated. Benson reviews only clips where all signals fail (no GPS + transferred + unrecognizable).
Videos are the proof of attendance; tickets are evidence, not the source of truth.

## Data
- `D:\icloud-videos\YYYY\MM\DD\` — icloudpd download (videos only, nothing deleted from iCloud). Session cookie in `.icloud/`.
- `data/videos.json` — per-clip metadata (`scripts/extract.py`, ffprobe: local time+tz, GPS, model, duration).
- `data/tickets.json` — 87 Gmail ticket purchases 2014–2026 with status (bought/sold/cancelled), friend transfers in notes.
- `data/shows.json` — nights → sets → clips (`scripts/cluster.py`); `data/not-shows.json` — evening clusters rejected.
- `data/setlist-cache.json`, `data/geo-cache.json` — API caches.
- `.env` — `SETLISTFM_KEY` (2 req/s, 1440/day).

## Pipeline
1. Nights: clips split on 3h gaps, evening only, venue = ticket venue or OSM music venue near GPS median.
2. Lineup: ticket → setlist.fm (date+city, fuzzy venue) → web search (venue+date listings, tour posters, set times) → Gmail/Calendar extras.
3. Band per clip, fused with playing-order constraint:
   - Whisper transcript (band self-ID in banter) — highest precision
   - published set times × clip timestamp
   - audio embedding (CLAP) vs studio previews of candidate bands (iTunes Search previews)
   - vision: frames vs candidate band photos; lighting/lineup consistency to group sets
   - order/timing prior
4. Song: Whisper lyrics vs candidate songs, audio vs song previews, setlist.fm songs.
5. Calibrate each signal on nights with certain answers before trusting it.
6. No-GPS / transferred clips: match to nights by visual similarity; else review queue.
7. Ticket-only shows (no video, pre-2021 library) appear as ticket-only entries.

## Findings
- Library effectively starts mid-2021 (1 video in 2020). ~1,871 videos; avg ~58 MB.
- Shazam (shazamio) works on studio audio, 0/39 on live phone clips (clipped mic). Not usable directly.
- Single frames rarely show readable logos (Saint Vitus has no backdrop); frames do separate bands visually.
- Non-camera mp4s (saved from apps, screen recordings) have no model tag → excluded from show clustering.

- Whisper: 317/1602 clips have confident speech, ~35 banter hits (e.g. "We're Counterparts" 2022-12-14).
- CLAP audio, night-centered: separates bands within a night (+0.6..0.8 same band). Vs studio previews: weak, tiebreaker only.
- Frames: separate bands visually; identify only with close shots + reference photos.
- Venue lookup: bulk OSM download per 0.5° cell (`data/osm-venues.json`); per-point Overpass was too slow.
- setlist.fm matched 55/153 nights, often with tours + full setlists.

## State (2026-10-03)
- Download complete: 1,860 files, 116 GB. 153 nights (incl. `maybe_not_show`) → `data/nights/<id>/evidence.json` + `set<N>.jpg`.
- Resolver agents (brief: `docs/resolver-brief.md`) write `data/nights/<id>/resolved.json`.

## Next
- Collect resolved.json, audit a sample, then merge into `data/catalog.json`.
- Not yet used: Google Calendar; non-camera/transferred clips (269 without GPS) matching to nights; ticket-only shows.
- Then site.
