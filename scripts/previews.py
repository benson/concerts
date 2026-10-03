"""Fetch iTunes 30s previews for an artist and embed them with CLAP -> data/embeddings/artists.npz."""
import json, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

import numpy as np
import torch
from transformers import ClapModel, ClapProcessor

DATA = Path(__file__).resolve().parent.parent / "data"
DIR = DATA / "previews"
OUT = DATA / "embeddings" / "artists.npz"
_model = None


def clap():
    global _model
    if _model is None:
        _model = (ClapModel.from_pretrained("laion/larger_clap_music").to("cuda").eval(),
                  ClapProcessor.from_pretrained("laion/larger_clap_music"))
    return _model


def tracks(artist, n=8):
    q = urllib.parse.urlencode({"term": artist, "entity": "song", "limit": 50})
    res = json.loads(urllib.request.urlopen(f"https://itunes.apple.com/search?{q}", timeout=30).read())["results"]
    want = artist.lower().replace("the ", "")
    hits = [r for r in res if r.get("previewUrl") and r["artistName"].lower().replace("the ", "") == want]
    seen, out = set(), []
    for r in hits:
        if r["trackName"] not in seen:
            seen.add(r["trackName"]); out.append(r)
    return out[:n]


def embed_file(path):
    m, p = clap()
    pcm = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(path), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(pcm, dtype=np.float32)
    wins = [a[i:i + 480000] for i in range(0, max(len(a) - 240000, 1), 480000)]
    with torch.no_grad():
        x = p(audio=wins, sampling_rate=48000, return_tensors="pt").to("cuda")
        e = m.audio_projection(m.audio_model(input_features=x["input_features"], is_longer=x.get("is_longer")).pooler_output)
        e = torch.nn.functional.normalize(e, dim=-1)
    return e.cpu().numpy()


def artist_embeddings(artist):
    """Per-track embeddings (n_tracks, d) for an artist; cached. Empty array if no previews."""
    store = dict(np.load(OUT)) if OUT.exists() else {}
    if artist in store:
        return store[artist]
    d = DIR / artist.replace("/", "_")
    d.mkdir(parents=True, exist_ok=True)
    embs = []
    for t in tracks(artist):
        f = d / f'{t["trackId"]}.m4a'
        if not f.exists():
            f.write_bytes(urllib.request.urlopen(t["previewUrl"], timeout=30).read())
        embs.append(embed_file(f).mean(0))
    store[artist] = np.stack(embs) if embs else np.zeros((0, 512), dtype=np.float32)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT, **store)
    return store[artist]


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(a, artist_embeddings(a).shape)
