"""Attach non-camera clips (sent/saved, no metadata) to show nights or tickets -> data/orphans.json."""
import glob, json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

DATA = Path(__file__).resolve().parent.parent / "data"
PROMPTS = ["a phone video of a band playing live on stage at a concert",
           "a crowd at a rock show", "a phone video at home", "a screen recording of a phone app",
           "a video of food or a restaurant", "a video outdoors in nature", "a video of a pet",
           "a video of a street or a car", "a video of people at a party"]


def main():
    vis = dict(np.load(DATA / "embeddings" / "clip.npz"))
    m = CLIPModel.from_pretrained("openai/clip-vit-large-patch14-336").eval()
    p = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14-336")
    with torch.no_grad():
        t = m.text_projection(m.text_model(**p(text=PROMPTS, return_tensors="pt", padding=True)).pooler_output)
        T = torch.nn.functional.normalize(t, dim=-1).numpy()

    nights = {}
    for f in glob.glob(str(DATA / "nights" / "*" / "resolved.json")):
        r = json.loads(Path(f).read_text(encoding="utf-8"))
        if r.get("is_show"):
            nights[r["night_id"]] = r
    tickets = json.loads((DATA / "tickets.json").read_text())["purchases"]

    out = []
    for v in json.loads((DATA / "videos.json").read_text()):
        if v["model"] or v["path"] not in vis:
            continue
        e = vis[v["path"]]
        probs = np.exp(100 * (T @ e)); probs /= probs.sum()
        concert = float(probs[:2].sum())
        filed = date(*map(int, v["path"][:10].split("/")))
        best = None
        for nid, r in nights.items():
            d = date.fromisoformat(r["date"])
            if not timedelta(0) <= filed - d <= timedelta(days=3):
                continue
            clips = [c for c, x in r["clips"].items() if not x.get("not_show") and c in vis]
            if clips:
                sim = max(float(vis[c] @ e) for c in clips)
                if best is None or sim > best[0]:
                    best = (sim, nid)
        tk = [t for t in tickets if t["status"] != "cancelled"
              and timedelta(0) <= filed - date.fromisoformat(t["date"]) <= timedelta(days=3)]
        if best and best[0] >= 0.8:
            out.append({"path": v["path"], "night_id": best[1], "sim": round(best[0], 3), "concert": round(concert, 2)})
        elif concert >= 0.6 and tk:
            out.append({"path": v["path"], "ticket": {k: tk[0][k] for k in ("date", "venue", "lineup")},
                        "concert": round(concert, 2)})
        elif concert >= 0.6:
            out.append({"path": v["path"], "unplaced": True, "concert": round(concert, 2)})
    (DATA / "orphans.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for o in out:
        print(o["path"], "->", o.get("night_id") or (o.get("ticket") or {}).get("venue") or "unplaced",
              o.get("sim", ""), o["concert"])


if __name__ == "__main__":
    main()
