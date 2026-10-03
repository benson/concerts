"""Guess clips whose phone rotation flag was wrong: score each thumbnail at 0/90/180/270 with CLIP -> data/orientation.json."""
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

BASE = Path(__file__).resolve().parent.parent
UPRIGHT = ["an upright photo of a band performing on stage", "an upright photo of a crowd at a concert",
           "an upright photo of a room with lights on the ceiling"]
WRONG = ["a sideways rotated photo", "an upside down photo"]


def main():
    m = CLIPModel.from_pretrained("openai/clip-vit-large-patch14-336").to("cuda").eval()
    p = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14-336")
    with torch.no_grad():
        t = m.text_projection(m.text_model(**p(text=UPRIGHT + WRONG, return_tensors="pt", padding=True).to("cuda")).pooler_output)
        T = torch.nn.functional.normalize(t, dim=-1)
    ids = [c["id"] for s in json.loads((BASE / "site/data/catalog.json").read_text(encoding="utf-8")) for c in s["clips"]]
    out = {}
    for cid in ids:
        img = Image.open(BASE / f"site/media/t/{cid}.jpg").convert("RGB")
        rots = [img, img.rotate(-90, expand=True), img.rotate(180), img.rotate(90, expand=True)]  # clockwise turns
        with torch.no_grad():
            x = p(images=rots, return_tensors="pt")["pixel_values"].to("cuda")
            e = torch.nn.functional.normalize(m.visual_projection(m.vision_model(pixel_values=x).pooler_output), dim=-1)
            logits = 100 * e @ T.T
            score = (logits[:, :len(UPRIGHT)].logsumexp(1) - logits[:, len(UPRIGHT):].logsumexp(1)).tolist()
        best = max(range(4), key=lambda k: score[k])
        out[cid] = {"turn": best * 90, "margin": round(score[best] - score[0], 2), "scores": [round(s, 2) for s in score]}
    (BASE / "data/orientation.json").write_text(json.dumps(out, indent=1))
    flagged = {k: v for k, v in out.items() if v["turn"] and v["margin"] > 1.0}
    print(len(flagged), "clips look rotated")
    for k, v in sorted(flagged.items(), key=lambda kv: -kv[1]["margin"]):
        print(k, v["turn"], v["margin"])


if __name__ == "__main__":
    main()
