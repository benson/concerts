"""Whisper-transcribe every camera clip -> data/transcripts.json (incremental). Arg: optional path filter."""
import json, os, subprocess, sys
import numpy as np
from pathlib import Path

# ctranslate2 needs the pip-installed CUDA dlls on PATH (Windows)
import importlib.util
for pkg in ("nvidia.cublas", "nvidia.cudnn"):
    spec = importlib.util.find_spec(pkg)
    if spec:
        os.add_dll_directory(str(Path(spec.submodule_search_locations[0]) / "bin"))
        os.environ["PATH"] = str(Path(spec.submodule_search_locations[0]) / "bin") + os.pathsep + os.environ["PATH"]

from faster_whisper import WhisperModel

ROOT = Path("D:/icloud-videos")
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "transcripts.json"


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    videos = [v for v in json.loads((DATA / "videos.json").read_text())
              if v["model"] and flt in v["path"] and v["path"] not in done]
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    for i, v in enumerate(videos):
        try:
            pcm = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(ROOT / v["path"]), "-vn", "-ac", "1",
                                  "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
            audio = np.frombuffer(pcm, dtype=np.float32)
            segs, info = model.transcribe(audio, vad_filter=True, beam_size=5,
                                          condition_on_previous_text=False)
            segs = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip(),
                     "p": round(s.avg_logprob, 2)} for s in segs]
            done[v["path"]] = {"lang": info.language, "segments": segs}
        except Exception as e:
            print("error", v["path"], e, flush=True)
            continue
        text = " / ".join(s["text"] for s in segs)
        print(v["path"], "|", text[:160], flush=True)
        if i % 20 == 19:
            OUT.write_text(json.dumps(done, indent=1))
    OUT.write_text(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
