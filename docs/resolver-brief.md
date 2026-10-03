# Resolver brief

You resolve "nights" from Benson's phone videos into tagged concert data. Do NOT delegate to other agents; do the work yourself. Never modify files other than the `resolved.json` files you are told to write. Never send email or post anything; Gmail is read-only if you use it.

## Input per night
`C:\Users\benso\Projects\concerts\data\nights\<night_id>\evidence.json` and `set<N>.jpg` frame strips (one strip per set; read them as images).

Fields:
- `venue`, `lat/lon`: from ticket or nearest OSM music venue. `maybe_not_show: true` means no venue was found near the GPS: decide whether this was a show at all (DIY spaces, festivals, outdoor stages are often missing from OSM) or something else (home, family trip, party, sports, comedy).
- `tickets`: Gmail ticket purchases for that date (status bought/sold/cancelled; notes may list fuller lineups). A ticket proves a purchase, not attendance; the videos prove attendance.
- `setlist_fm`: setlists logged at a fuzzy-matched venue that date, with tour names and songs. Can include acts from a different room/event at the same venue; check.
- `sets`: clips grouped by time gaps (>12 min = new group). A group is NOT necessarily one band: a band may span two groups (long gap mid-set) and two bands can fall in one group (short changeover). Also not every band was filmed, and some groups may be non-show clips (street, food, friends).
- `speech`: Whisper transcript, confident segments only. Screamed vocals rarely transcribe; banter like "we're Counterparts from Hamilton" is near-certain evidence when present.
- `set_audio_similarity`: cosine similarity between groups' audio embeddings, centered on the night. Roughly +0.5..+0.8 = same band, below 0 = different band. Use it to merge/split groups into bands.

## Method (in order)
1. **Identify the show.** Venue + date → full bill, billing order, and if possible set times and tour. Sources in priority: ticket (and ticket notes), setlist.fm, then web search (`<venue> <Month D YYYY>`, DICE/Songkick/Bandsintown/venue/promoter pages, BrooklynVegan, Lambgoat, tour posters for the headliner's tour that month, Instagram set-times posts if indexed). Festivals publish schedules with stage times; use them with clip timestamps. Record source URLs.
2. **Count distinct bands on video.** Merge/split time groups using audio similarity and the frames (lighting colors, stage setup, number/appearance of members, instruments). Exclude non-show clips (mark them `not_show`).
3. **Name each band.** Combine: playing order (openers first, headliner last; billing order usually lists headliner first; co-headliners: check), set times if found, timing from doors, speech hits, and visual comparison against reference photos (Wikipedia REST API `https://en.wikipedia.org/api/rest_v1/page/summary/<Title>` → `originalimage.source`; download with curl using the exact URL it returns and a User-Agent header, to `C:\Users\benso\AppData\Local\Temp\concerts-refs\`; compare vocalist/guitarist hair, build, tattoos, shirtlessness, instruments). Only invoke photos when order/timing leaves real doubt.
4. **Songs (best effort).** Only tag a song when there's evidence: speech names it, recognizable clean lyrics match a song, or a festival/one-song-set certainty. setlist.fm song lists bound the candidates but are not themselves evidence of which clip is which song. Leave `song: null` otherwise.
5. **Tour**: setlist.fm `tour` or web sources.

## Output
Write `C:\Users\benso\Projects\concerts\data\nights\<night_id>\resolved.json`:
```json
{
  "night_id": "...", "date": "YYYY-MM-DD",
  "is_show": true,
  "event": "event/tour name or null",
  "venue": "canonical venue name", "city": "Brooklyn, NY",
  "lineup": [{"band": "...", "play_order": 1, "tour": "... or null"}],
  "clips": {"<path>": {"band": "... or null", "song": "... or null", "not_show": false,
                       "confidence": "high|medium|low", "why": "short reason"}},
  "sources": ["url", "..."],
  "review": null,
  "notes": "short"
}
```
`play_order` 1 = first on stage. Include every lineup band even if not filmed.

Confidence: high = direct evidence (speech, set times + timestamp, unambiguous single-band night, distinctive visual match); medium = consistent order/timing inference with no contradiction; low = guess.

`review`: set ONLY when the night is genuinely unresolvable from all available evidence — e.g. no GPS + no matching date + nothing recognizable, or a clip whose band can't be narrowed past a coin flip after trying everything. Then give a one-line question for Benson ("Which band is the purple-lit set at 21:40: Carnifex or All Shall Perish?"). Medium-confidence inferences do NOT need review.

When done with your batch, reply with one line per night: `night_id | is_show | venue | bands filmed | lowest confidence | review?`.
