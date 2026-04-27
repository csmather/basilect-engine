"""NTS tracklist crawler.

Phases, each resumable:
  1. master      → data/master_sitemap.jsonl  (every show + episode URL)
  2. shows       → data/shows.jsonl           (per-show metadata: genres, moods, etc.)
  3. tracklists  → data/tracklists.jsonl      (one fetch per episode)

Side product:
  artists  → data/artist_sitemap.jsonl   (slug→id table for free-text artist canonicalization)

Why master sitemap, not /api/v2 pagination?
  /api/v2/shows pagination caps at offset=1008 (HTTP 422 beyond), and per-show
  /episodes lists are also lossy beyond the API window. The master sitemap.xml.gz
  enumerates every show landing and every episode URL, including ones the API can't
  paginate to. Verified: even the oldest episode (2012) fetches 200 via tracklist.

Run:
  python crawl.py master
  python crawl.py shows [--limit N]
  python crawl.py tracklists [--limit N]
  python crawl.py artists                # only needed once, for later canonicalization
"""
import argparse
import gzip
import json
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).parent
DATA = ROOT / "data"
MASTER_FILE = DATA / "master_sitemap.jsonl"
SHOWS_FILE = DATA / "shows.jsonl"
TRACKLISTS_FILE = DATA / "tracklists.jsonl"
SITEMAP_FILE = DATA / "artist_sitemap.jsonl"  # built by `artists` cmd; slug→id table
ERRORS_FILE = DATA / "errors.jsonl"

API = "https://www.nts.live/api/v2"
MASTER_INDEX = "https://www.nts.live/sitemap.xml.gz"
ARTISTS_INDEX = "https://www.nts.live/artists_sitemap.xml.gz"

SUB_RE = re.compile(r"<loc>(https://www\.nts\.live/[^<]+\.xml\.gz)</loc>")
LOC_RE = re.compile(r"<loc>(https://www\.nts\.live/[^<]+)</loc>")
ARTIST_URL_RE = re.compile(r"<loc>(https://www\.nts\.live/artists/(\d+)-([^<]+))</loc>")
SHOW_LANDING_RE = re.compile(r"^https://www\.nts\.live/shows/([^/]+)$")
EPISODE_URL_RE = re.compile(r"^https://www\.nts\.live/shows/([^/]+)/episodes/([^/]+)$")

UA = "basilect-research/0.1 (matherscottc@gmail.com)"
HEADERS = {"User-Agent": UA}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get_json(url: str, **params) -> dict:
    r = SESSION.get(url, params=params or None, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_xml_gz(url: str) -> str:
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    content = r.content
    if content[:2] == b"\x1f\x8b":
        return gzip.decompress(content).decode()
    return content.decode()


# ---------- phase 1: master sitemap ----------

def fetch_master(sleep_s: float) -> None:
    if MASTER_FILE.exists():
        print(f"master: {MASTER_FILE.name} exists, skipping (delete to re-fetch)", file=sys.stderr)
        return
    DATA.mkdir(parents=True, exist_ok=True)
    print("fetching master sitemap index", file=sys.stderr)
    index_xml = fetch_xml_gz(MASTER_INDEX)
    sub_urls = SUB_RE.findall(index_xml)
    print(f"  {len(sub_urls)} sub-sitemaps", file=sys.stderr)

    shows = 0
    episodes = 0
    with MASTER_FILE.open("w") as f:
        for sub in sub_urls:
            print(f"  {sub}", file=sys.stderr)
            xml = fetch_xml_gz(sub)
            for m in LOC_RE.finditer(xml):
                url = m.group(1)
                em = EPISODE_URL_RE.match(url)
                if em:
                    f.write(json.dumps({
                        "kind": "episode",
                        "show_alias": em.group(1),
                        "episode_alias": em.group(2),
                    }) + "\n")
                    episodes += 1
                    continue
                sm = SHOW_LANDING_RE.match(url)
                if sm:
                    f.write(json.dumps({
                        "kind": "show",
                        "show_alias": sm.group(1),
                    }) + "\n")
                    shows += 1
            time.sleep(sleep_s)
    print(f"master: shows={shows} episodes={episodes}", file=sys.stderr)


# ---------- phase 2: per-show metadata ----------

def trim_show(s: dict) -> dict:
    return {
        "show_alias": s.get("show_alias"),
        "name": s.get("name"),
        "type": s.get("type"),
        "description": s.get("description"),
        "external_links": s.get("external_links") or [],
        "moods": [m.get("value") for m in (s.get("moods") or [])],
        "genres": [g.get("value") for g in (s.get("genres") or [])],
        "location_short": s.get("location_short"),
        "location_long": s.get("location_long"),
        "intensity": s.get("intensity"),
        "frequency": s.get("frequency"),
    }


def load_seen_shows() -> set[str]:
    if not SHOWS_FILE.exists():
        return set()
    seen: set[str] = set()
    with SHOWS_FILE.open() as f:
        for line in f:
            try:
                row = json.loads(line)
                sa = row.get("show_alias")
                if sa:
                    seen.add(sa)
            except json.JSONDecodeError:
                continue
    return seen


def load_shows_from_master() -> list[str]:
    # Master sitemap stores aliases extracted from URLs, so non-ASCII slugs
    # (e.g. coucou-chloé) appear %-encoded. The API expects the decoded form;
    # passing %-encoded would double-encode over the wire and 404.
    aliases: list[str] = []
    seen: set[str] = set()
    with MASTER_FILE.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("kind") == "show":
                sa = r.get("show_alias")
                if sa:
                    sa = urllib.parse.unquote(sa)
                    if sa not in seen:
                        seen.add(sa)
                        aliases.append(sa)
    return aliases


def _fetch_one_show(show_alias: str, sleep_s: float) -> dict:
    url = f"{API}/shows/{show_alias}"
    try:
        data = get_json(url)
        result = {"ok": True, "row": trim_show(data)}
    except Exception as e:
        result = {
            "ok": False,
            "show_alias": show_alias,
            "error": f"{type(e).__name__}: {e}",
        }
    time.sleep(sleep_s)
    return result


def fetch_shows(sleep_s: float, limit: int | None, concurrency: int) -> None:
    if not MASTER_FILE.exists():
        print("shows: run `master` phase first", file=sys.stderr)
        return
    DATA.mkdir(parents=True, exist_ok=True)
    aliases = load_shows_from_master()
    seen = load_seen_shows()
    todo = [a for a in aliases if a not in seen]
    if limit is not None:
        todo = todo[:limit]
    rate = concurrency / sleep_s if sleep_s > 0 else float("inf")
    print(f"shows: {len(todo)} todo ({len(seen)} done, {len(aliases)} total) | concurrency={concurrency} sleep={sleep_s}s ≈{rate:.1f} req/s", file=sys.stderr)

    write_lock = threading.Lock()
    ok = errors = 0
    interrupted = False

    pool = ThreadPoolExecutor(max_workers=concurrency)
    out = SHOWS_FILE.open("a")
    err = ERRORS_FILE.open("a")
    try:
        futures = [pool.submit(_fetch_one_show, a, sleep_s) for a in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result["ok"]:
                with write_lock:
                    out.write(json.dumps(result["row"], ensure_ascii=False) + "\n")
                    out.flush()
                ok += 1
            else:
                with write_lock:
                    err.write(json.dumps({
                        "phase": "shows",
                        "show_alias": result["show_alias"],
                        "error": result["error"],
                    }) + "\n")
                    err.flush()
                errors += 1
            if i % 100 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] ok={ok} err={errors}", file=sys.stderr)
    except KeyboardInterrupt:
        interrupted = True
        print("\ninterrupted; cancelling pending fetches...", file=sys.stderr)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        out.close()
        err.close()
    status = "INTERRUPTED" if interrupted else "done"
    print(f"shows: {status}. ok={ok} errors={errors}", file=sys.stderr)


# ---------- phase 3: tracklists ----------

def trim_track(t: dict) -> dict:
    return {
        "artist": t.get("artist"),
        "title": t.get("title"),
        "uid": t.get("uid"),
    }


def load_seen_episodes() -> set[str]:
    if not TRACKLISTS_FILE.exists():
        return set()
    seen: set[str] = set()
    with TRACKLISTS_FILE.open() as f:
        for line in f:
            try:
                row = json.loads(line)
                ea = row.get("episode_alias")
                if ea:
                    seen.add(ea)
            except json.JSONDecodeError:
                continue
    return seen


def load_episodes_from_master() -> list[dict]:
    # See note in load_shows_from_master: %-encoded slugs would double-encode
    # over the wire. Decode here so callers always get API-ready aliases.
    rows = []
    with MASTER_FILE.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("kind") == "episode":
                rows.append({
                    "show_alias": urllib.parse.unquote(r["show_alias"]),
                    "episode_alias": urllib.parse.unquote(r["episode_alias"]),
                })
    return rows


def _fetch_one_tracklist(ep: dict, sleep_s: float) -> dict:
    url = f"{API}/shows/{ep['show_alias']}/episodes/{ep['episode_alias']}/tracklist"
    try:
        data = get_json(url)
        tracks = [trim_track(t) for t in (data.get("results") or [])]
        result = {
            "ok": True,
            "row": {
                "show_alias": ep["show_alias"],
                "episode_alias": ep["episode_alias"],
                "tracks": tracks,
            },
        }
    except Exception as e:
        result = {
            "ok": False,
            "ep": ep,
            "error": f"{type(e).__name__}: {e}",
        }
    # Per-worker pacing. With concurrency=N, effective rate ≈ N / sleep_s req/s.
    time.sleep(sleep_s)
    return result


def fetch_tracklists(sleep_s: float, limit: int | None, concurrency: int) -> None:
    if not MASTER_FILE.exists():
        print("tracklists: run `master` phase first", file=sys.stderr)
        return
    DATA.mkdir(parents=True, exist_ok=True)
    episodes = load_episodes_from_master()
    seen = load_seen_episodes()
    todo = [e for e in episodes if e["episode_alias"] not in seen]
    if limit is not None:
        todo = todo[:limit]
    rate = concurrency / sleep_s if sleep_s > 0 else float("inf")
    print(f"tracklists: {len(todo)} episodes ({len(seen)} done, {len(episodes)} total) | concurrency={concurrency} sleep={sleep_s}s ≈{rate:.1f} req/s", file=sys.stderr)

    write_lock = threading.Lock()
    ok = errors = empty = 0
    interrupted = False

    pool = ThreadPoolExecutor(max_workers=concurrency)
    out = TRACKLISTS_FILE.open("a")
    err = ERRORS_FILE.open("a")
    try:
        futures = [pool.submit(_fetch_one_tracklist, ep, sleep_s) for ep in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result["ok"]:
                row = result["row"]
                with write_lock:
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    out.flush()
                ok += 1
                if not row["tracks"]:
                    empty += 1
            else:
                with write_lock:
                    err.write(json.dumps({
                        "phase": "tracklists",
                        "show_alias": result["ep"]["show_alias"],
                        "episode_alias": result["ep"]["episode_alias"],
                        "error": result["error"],
                    }) + "\n")
                    err.flush()
                errors += 1
            if i % 100 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] ok={ok} empty={empty} err={errors}", file=sys.stderr)
    except KeyboardInterrupt:
        interrupted = True
        print("\ninterrupted; cancelling pending fetches...", file=sys.stderr)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        out.close()
        err.close()
    status = "INTERRUPTED" if interrupted else "done"
    print(f"tracklists: {status}. ok={ok} empty={empty} errors={errors}", file=sys.stderr)


# ---------- artists sitemap (canonicalization dictionary) ----------

def walk_artists(sleep_s: float) -> None:
    if SITEMAP_FILE.exists():
        print(f"artists: {SITEMAP_FILE.name} exists, skipping (delete to re-fetch)", file=sys.stderr)
        return
    DATA.mkdir(parents=True, exist_ok=True)
    print("fetching artists sitemap index", file=sys.stderr)
    index_xml = fetch_xml_gz(ARTISTS_INDEX)
    sub_urls = SUB_RE.findall(index_xml)
    print(f"  {len(sub_urls)} sub-sitemaps", file=sys.stderr)
    n = 0
    with SITEMAP_FILE.open("w") as f:
        for sub in sub_urls:
            print(f"  {sub}", file=sys.stderr)
            xml = fetch_xml_gz(sub)
            for m in ARTIST_URL_RE.finditer(xml):
                f.write(json.dumps({"id": int(m.group(2)), "slug": m.group(3), "url": m.group(1)}) + "\n")
                n += 1
            time.sleep(sleep_s)
    print(f"artists: wrote {n} artists", file=sys.stderr)


# ---------- cli ----------

def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("master", help="phase 1: walk master sitemap (shows + episodes)")
    sp.add_argument("--sleep", type=float, default=1.0)

    sp = sub.add_parser("shows", help="phase 2: fetch per-show metadata")
    sp.add_argument("--sleep", type=float, default=1.0, help="per-worker sleep between requests (effective rate ≈ concurrency/sleep req/s)")
    sp.add_argument("--limit", type=int, help="limit to N shows (testing)")
    sp.add_argument("--concurrency", type=int, default=1, help="parallel workers (default: 1, sync)")

    sp = sub.add_parser("tracklists", help="phase 3: fetch tracklist per episode")
    sp.add_argument("--sleep", type=float, default=1.0, help="per-worker sleep between requests (effective rate ≈ concurrency/sleep req/s)")
    sp.add_argument("--limit", type=int, help="limit to N episodes (testing)")
    sp.add_argument("--concurrency", type=int, default=1, help="parallel workers (default: 1, sync)")

    sp = sub.add_parser("artists", help="walk artists sitemap (slug→id canonicalization table)")
    sp.add_argument("--sleep", type=float, default=1.0)

    args = p.parse_args()
    if args.cmd == "master":
        fetch_master(args.sleep)
    elif args.cmd == "shows":
        fetch_shows(args.sleep, args.limit, args.concurrency)
    elif args.cmd == "tracklists":
        fetch_tracklists(args.sleep, args.limit, args.concurrency)
    elif args.cmd == "artists":
        walk_artists(args.sleep)


if __name__ == "__main__":
    main()
