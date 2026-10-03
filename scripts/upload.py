"""Upload finished proxies to the concerts-clips R2 bucket (incremental). --watch keeps going while media.py runs."""
import json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROXIES = Path("D:/concerts-proxies")
DONE = BASE / "data" / "uploaded.json"


def put(f):
    r = subprocess.run(f'npx wrangler r2 object put "concerts-clips/{f.name}" --file "{f}" '
                       f'--content-type video/mp4 --cache-control "public, max-age=31536000" --remote',
                       shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=BASE)
    return f.name, r.returncode == 0, r.stderr[-300:]


def encoding():
    r = subprocess.run(["powershell", "-c", "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                        "? { $_.CommandLine -match 'media.py' } | measure | % Count"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() not in ("", "0")


def main():
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    while True:
        todo = [f for f in sorted(PROXIES.glob("*.mp4")) if not f.name.endswith(".part.mp4") and f.name not in done]
        with ThreadPoolExecutor(6) as pool:
            for name, ok, err in pool.map(put, todo):
                if ok:
                    done.add(name)
                else:
                    print("failed", name, err, flush=True)
        DONE.write_text(json.dumps(sorted(done)))
        if todo:
            print(f"{len(done)} uploaded", flush=True)
        if "--watch" not in sys.argv or (not encoding() and not todo):
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
