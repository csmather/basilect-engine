"""NTS artist-page crawler.

Walks the artists sitemap, fetches each artist page, extracts the trimmed
state.artist subtree from window._REACT_STATE_, appends to data/artists.jsonl.
Resumable: skips IDs already present in the output file.
"""
import argparse
import gzip
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
DATA = ROOT / "data"
ARTISTS_FILE = DATA / "artists.jsonl"
SITEMAP_FILE = DATA / "sitemap.jsonl"
ERRORS_FILE = DATA / "errors.jsonl"

SITEMAP_INDEX = "https://www.nts.live/artists_sitemap.xml.gz"
SUB_SITEMAP_RE = re.compile(r"<loc>(https://www\.nts\.live/artists_sitemap\d+\.xml\.gz)</loc>")
ARTIST_URL_RE = re.compile(r"<loc>(https://www\.nts\.live/artists/(\d+)-([^<]+))</loc>")
REACT_STATE_RE = re.compile(r"window\._REACT_STATE_\s*=\s*(\{.*?\});\s*</script>", re.S)

USER_AGENT = "basilect-research/0.1 (matherscottc@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}


def fetch_bytes(url: str) -> bytes:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.content


def fetch_text(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def walk_sitemap() -> list[dict]:
    """Returns [{id, slug, url}, ...] for every artist page. Cached on disk."""
    if SITEMAP_FILE.exists():
        with SITEMAP_FILE.open() as f:
            return [json.loads(line) for line in f]

    print("fetching sitemap index", file=sys.stderr)
    index_xml = gzip.decompress(fetch_bytes(SITEMAP_INDEX)).decode()
    sub_urls = SUB_SITEMAP_RE.findall(index_xml)
    print(f"  {len(sub_urls)} sub-sitemaps", file=sys.stderr)

    artists = []
    for sub_url in sub_urls:
        print(f"fetching {sub_url}", file=sys.stderr)
        sub_xml = gzip.decompress(fetch_bytes(sub_url)).decode()
        for m in ARTIST_URL_RE.finditer(sub_xml):
            artists.append({"id": int(m.group(2)), "slug": m.group(3), "url": m.group(1)})

    DATA.mkdir(parents=True, exist_ok=True)
    with SITEMAP_FILE.open("w") as f:
        for a in artists:
            f.write(json.dumps(a) + "\n")
    print(f"wrote {len(artists)} artists to {SITEMAP_FILE}", file=sys.stderr)
    return artists


def parse_artist_page(html: str) -> dict | None:
    """Extract and trim state.artist from window._REACT_STATE_."""
    m = REACT_STATE_RE.search(html)
    if not m:
        return None
    state = json.loads(m.group(1))
    a = state.get("artist") or {}
    if not a.get("id"):
        return None
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "slug": a.get("slug"),
        "biography": a.get("biography"),
        "totalTracks": a.get("totalTracks"),
        "tracks": [
            {
                "title": t.get("title"),
                "artistNames": t.get("artistNames"),
                "releaseLabels": t.get("releaseLabels"),
                "releaseYear": t.get("releaseYear"),
                "discogsUrl": t.get("discogsUrl"),
            }
            for t in (a.get("tracks") or [])
        ],
        "episodesPlayedOn": [
            {
                "episode_alias": e.get("episode_alias"),
                "show_alias": e.get("show_alias"),
                "broadcast": e.get("broadcast"),
            }
            for e in (a.get("episodesPlayedOn") or [])
        ],
        "residentShowLinks": [
            {"show_alias": s.get("show_alias"), "name": s.get("name")}
            for s in (a.get("residentShowLinks") or [])
        ],
        "specialShowLinks": [
            {"show_alias": s.get("show_alias"), "name": s.get("name")}
            for s in (a.get("specialShowLinks") or [])
        ],
    }


def load_seen_ids() -> set[int]:
    if not ARTISTS_FILE.exists():
        return set()
    seen: set[int] = set()
    with ARTISTS_FILE.open() as f:
        for line in f:
            try:
                row = json.loads(line)
                if row.get("id"):
                    seen.add(row["id"])
            except json.JSONDecodeError:
                continue
    return seen


def crawl(limit: int | None, sleep_s: float) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    artists = walk_sitemap()
    seen = load_seen_ids()
    print(f"sitemap: {len(artists)} artists | already crawled: {len(seen)}", file=sys.stderr)

    todo = [a for a in artists if a["id"] not in seen]
    if limit is not None:
        todo = todo[:limit]
    print(f"to crawl: {len(todo)} (sleep={sleep_s}s)", file=sys.stderr)

    ok = errors = 0
    with ARTISTS_FILE.open("a") as out, ERRORS_FILE.open("a") as err:
        for i, a in enumerate(todo, 1):
            try:
                html = fetch_text(a["url"])
                payload = parse_artist_page(html)
                if payload is None:
                    err.write(json.dumps({"id": a["id"], "url": a["url"], "error": "no_react_state"}) + "\n")
                    err.flush()
                    errors += 1
                else:
                    out.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    out.flush()
                    ok += 1
            except Exception as e:
                err.write(json.dumps({"id": a["id"], "url": a["url"], "error": f"{type(e).__name__}: {e}"}) + "\n")
                err.flush()
                errors += 1

            if i % 25 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] ok={ok} err={errors} last={a['slug']}", file=sys.stderr)
            time.sleep(sleep_s)

    print(f"done. ok={ok} errors={errors}", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, help="crawl at most N new artists")
    p.add_argument("--full", action="store_true", help="crawl every artist in the sitemap")
    p.add_argument("--sleep", type=float, default=1.0, help="seconds between requests")
    args = p.parse_args()
    if args.sample is None and not args.full:
        p.error("specify --sample N or --full")
    crawl(limit=args.sample, sleep_s=args.sleep)


if __name__ == "__main__":
    main()
