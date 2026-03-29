import sys
import json
from pathlib import Path
import trafilatura

def scrape(artist_id):
    path = Path(f"data/artists/{artist_id}/sources.json")
    if not path.exists():
        print(f"Not found: {path}")
        sys.exit(1)

    sources = json.loads(path.read_text())

    for entry in sources:
        if "text" in entry:
            continue

        url = entry["url"]
        pub = entry.get("publication", url)

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            entry["text"] = None
            print(f"FAIL {pub} — fetch failed (network/blocked) — {url}")
            continue
        text = trafilatura.extract(downloaded)
        if not text:
            entry["text"] = None
            print(f"FAIL {pub} — no text extracted (paywall/JS) — {url}")
            continue
        entry["text"] = text
        print(f"OK  {pub}")

    path.write_text(json.dumps(sources, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/scrape.py <artist_id>")
        sys.exit(1)
    scrape(sys.argv[1])
