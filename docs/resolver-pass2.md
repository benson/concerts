# Resolver pass 2 (hard nights)

Read `docs/resolver-brief.md` first; everything there still applies. These nights already have a `resolved.json` from pass 1 that left a `review` question or low-confidence/unnamed clips. Your job: push every one of them to medium or better, or prove it can't be done. Do NOT delegate to other agents.

Extra avenues pass 1 did not use (use all that fit):
- **Gmail (read-only)**: search the date range ±3 weeks for the venue, band names, promoter, "tickets", "guest list", forwarded flyers, friends' messages about the show. Load tools with ToolSearch `+d4a3519c search_threads get_thread`. Never send, label, or modify mail.
- **Google Calendar (read-only)**: events on that date. Load with ToolSearch `+2f218595 search_events list_events`. Never create or edit events.
- **Logos and photos**: when frames show a backdrop, banner, kick-drum head or projected logo, web-search the candidate bands' logos and compare. For people, use Wikipedia REST `originalimage` (exact URL, curl with a User-Agent) or Bandcamp/label press photos via WebFetch; compare against the set's frames. Pull extra full-resolution frames yourself if needed: `ffmpeg -ss <t> -i "D:/icloud-videos/<path>" -frames:v 1 -vf scale=-2:1200 <out.jpg>` into `C:\Users\benso\AppData\Local\Temp\concerts-frames\`.
- **Set times / running order**: venue + promoter Instagram/Facebook posts surfaced by web search, festival schedule pages, Reddit threads, review write-ups ("opened the night", "closed the night"), YouTube video titles from other attendees (title + upload often names band + venue + date).
- **Billing-order trap**: "headliner listed first, reverse for play order" is a heuristic, not a fact. setlist.fm list order is arbitrary. Confirm order from a write-up, set times, or visual ID when you can.

Update the existing `resolved.json` in place (same schema). Add an `"evidence_pass2"` string field summarizing what you found and where. Keep `review` only if after all of the above it is still a genuine coin flip, and make the question answerable at a glance.

Reply with one line per night: `night_id | change summary | lowest confidence now | review?`.
