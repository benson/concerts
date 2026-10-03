# Audit + fix

Do NOT delegate to other agents. Context: `docs/resolver-brief.md`. A first audit of 12 nights found ~7% of medium/high band labels wrong, concentrated where play order was inferred from reversed billing with no set times, logo, review, or visual check (e.g. BAT/Black Tusk swapped on 2025-10-25; a "member" identified who died years earlier).

For each night: read `data/nights/<id>/evidence.json`, the `set<N>.jpg` strips, and `resolved.json`. Independently try to break it:
- Confirm running order from set times, reviews/recaps ("opened", "closed"), other attendees' YouTube titles, promoter/venue posts, setlist.fm notes. Do not accept "billing reversed" without corroboration when a second source exists.
- Look for logos/banners/screens in frames; pull extra full-res frames when useful: `ffmpeg -ss <t> -i "D:/icloud-videos/<path>" -frames:v 1 -vf scale=-2:1200 <out>` into `C:\Users\benso\AppData\Local\Temp\concerts-audit\`.
- Check member IDs against current lineups (people leave, die, get replaced).
- Non-show clips (empty stage, changeover screens, street) must be `not_show`, not tagged as a band.
- Songs only with evidence; tours exactly as sourced (no invented suffixes).

Then FIX `resolved.json` in place (same schema), adjusting confidence up when you found corroboration and down/review only when genuinely uncertain. Add field `"audit"`: short summary of what you checked, what changed, sources.

If `data/nights/<id>/audit.json` already exists, apply its fixes (verify them first) and do the same `"audit"` summary.

Reply with one line per night: `id | changed? | what | lowest confidence now`. End with a count of band labels changed.
