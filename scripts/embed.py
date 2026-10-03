"""Image (CLIP) + audio (CLAP) embeddings per camera clip -> data/embeddings/{clip,clap}.npz (incremental)."""
import json, subprocess, sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import ClapModel, ClapProcessor, CLIPModel, CLIPProcessor

ROOT = Path("D:/icloud-videos")
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "embeddings"
DEV = "cuda"


def frames(path, duration, n=4):
    out = []
    for k in range(n):
        t = duration * (k + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                              "-vf", "scale=336:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                             capture_output=True).stdout
        if raw:
            import io
            out.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return out


def audio(path, sr=48000, max_s=30):
    pcm = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-t", str(max_s), "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(pcm, dtype=np.float32)
    win = sr * 10
    return [a[i:i + win] for i in range(0, max(len(a) - win // 2, 1), win)] if len(a) else []


def load(name):
    f = OUT / f"{name}.npz"
    return dict(np.load(f)) if f.exists() else {}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flt = args[0] if args else ""
    OUT.mkdir(parents=True, exist_ok=True)
    vis, aud = load("clip"), load("clap")
    videos = [v for v in json.loads((DATA / "videos.json").read_text())
              if (v["model"] and v["local"] or "--all" in sys.argv) and flt in v["path"]
              and not (v["path"] in vis and v["path"] in aud)]
    clip_m = CLIPModel.from_pretrained("openai/clip-vit-large-patch14-336").to(DEV).eval().half()
    clip_p = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14-336")
    clap_m = ClapModel.from_pretrained("laion/larger_clap_music").to(DEV).eval()
    clap_p = ClapProcessor.from_pretrained("laion/larger_clap_music")
    for i, v in enumerate(videos):
        p = ROOT / v["path"]
        with torch.no_grad():
            imgs = frames(p, v["duration"] or 1)
            if imgs:
                x = clip_p(images=imgs, return_tensors="pt")["pixel_values"].to(DEV).half()
                e = clip_m.visual_projection(clip_m.vision_model(pixel_values=x).pooler_output).float()
                e = torch.nn.functional.normalize(e, dim=-1).mean(0)
                vis[v["path"]] = torch.nn.functional.normalize(e, dim=0).cpu().numpy()
            wins = audio(p)
            if wins:
                x = clap_p(audio=wins, sampling_rate=48000, return_tensors="pt").to(DEV)
                e = clap_m.audio_projection(clap_m.audio_model(input_features=x["input_features"], is_longer=x.get("is_longer")).pooler_output)
                e = torch.nn.functional.normalize(e, dim=-1).mean(0)
                aud[v["path"]] = torch.nn.functional.normalize(e, dim=0).cpu().numpy()
        if i % 25 == 24 or i == len(videos) - 1:
            np.savez(OUT / "clip.npz", **vis)
            np.savez(OUT / "clap.npz", **aud)
            print(f"{i + 1}/{len(videos)}", flush=True)


if __name__ == "__main__":
    main()
