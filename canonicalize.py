"""Canonicalize free-text artist strings on tracklists to NTS integer artist IDs.

Reads:
  data/tracklists.jsonl     (one row per episode, raw artist strings)
  data/artist_sitemap.jsonl (slug → id dictionary)

Writes:
  data/canonicalized.jsonl  (one row per episode: show_alias, episode_alias,
                             artist_ids [sorted unique], n_tracks, n_unresolved)
  data/unresolved.jsonl     (diagnostic: unresolved fragments + counts)

Pipeline per artist string:
  1. Skip if placeholder (Unknown Artist, Excerpt, ...).
  2. Try full-string slug match (catches "Tyler, the Creator" without splitting).
  3. If unmatched and contains a delimiter (,/&/ft/feat/x), split and slug-match each fragment.
  4. Per-fragment fallback: try with "the-" prefix added or stripped.

Run:
  python canonicalize.py
  python canonicalize.py --probe "A$AP Rocky"   # debug a single string
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TRACKLISTS_FILE = DATA / "tracklists.jsonl"
ARTIST_SITEMAP_FILE = DATA / "artist_sitemap.jsonl"
CANONICAL_FILE = DATA / "canonicalized.jsonl"
UNRESOLVED_FILE = DATA / "unresolved.jsonl"

COMMA_RE = re.compile(r"\s*,\s*")
SUB_DELIM_RE = re.compile(r"\s*(?:&| feat\.? | ft\.? | x )\s*", re.IGNORECASE)

# Tracklist-staff notes and meta-strings we want to skip outright.
PLACEHOLDERS = {
    "", "unknown artist", "unknown", "unkown", "various artists", "various",
    "v/a", "v.a.", "n/a", "untitled", "id", "?", ".", "excerpt", "intro",
    "outro", "interlude", "skit", "voice over", "voice-over",
}


def slugify(s: str) -> str:
    """NTS slug pattern: lowercase ASCII, alphanumerics joined by single hyphens."""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load_artist_sitemap() -> dict[str, int]:
    if not ARTIST_SITEMAP_FILE.exists():
        sys.exit(f"missing {ARTIST_SITEMAP_FILE} — run `crawl.py artists` first")
    slugs: dict[str, int] = {}
    with ARTIST_SITEMAP_FILE.open() as f:
        for line in f:
            r = json.loads(line)
            slugs[r["slug"]] = r["id"]
    return slugs


def _lookup(slug: str, slugs: dict[str, int]) -> int | None:
    """Slug lookup with article-prefix fallback (the-x ↔ x)."""
    if slug in slugs:
        return slugs[slug]
    if slug.startswith("the-"):
        alt = slug[4:]
        if alt in slugs:
            return slugs[alt]
    else:
        alt = "the-" + slug
        if alt in slugs:
            return slugs[alt]
    return None


def resolve(s: str, slugs: dict[str, int]) -> tuple[list[int], list[str]]:
    """Resolve a free-text artist string to NTS artist IDs.

    Two-tier split: comma is a hard collaborator boundary, but `&`/`ft`/`x`
    can appear inside band names ("Rhythm & Sound", "Earth, Wind & Fire").
    So: split on commas first, try each fragment as a full match, only fall
    back to sub-delimiters if the comma-fragment doesn't slug-match anything.

    Returns (ids, unresolved_fragments). Caller dedupes per-episode.
    """
    s = (s or "").strip()
    if not s or s.lower() in PLACEHOLDERS:
        return [], []
    full_sl = slugify(s)
    full_id = _lookup(full_sl, slugs)
    if full_id is not None:
        return [full_id], []
    comma_parts = COMMA_RE.split(s)
    ids: list[int] = []
    unresolved: list[str] = []
    for cp in comma_parts:
        cp = cp.strip()
        if not cp or cp.lower() in PLACEHOLDERS:
            continue
        cp_sl = slugify(cp)
        if not cp_sl:
            continue
        cp_id = _lookup(cp_sl, slugs)
        if cp_id is not None:
            ids.append(cp_id)
            continue
        sub_parts = SUB_DELIM_RE.split(cp)
        if len(sub_parts) <= 1:
            unresolved.append(cp)
            continue
        for p in sub_parts:
            p = p.strip()
            if not p or p.lower() in PLACEHOLDERS:
                continue
            sl = slugify(p)
            if not sl:
                continue
            pid = _lookup(sl, slugs)
            if pid is not None:
                ids.append(pid)
            else:
                unresolved.append(p)
    return ids, unresolved


def canonicalize_all() -> None:
    if not TRACKLISTS_FILE.exists():
        sys.exit(f"missing {TRACKLISTS_FILE} — run `crawl.py tracklists` first")
    slugs = load_artist_sitemap()
    print(f"loaded {len(slugs)} artist slugs", file=sys.stderr)

    n_episodes = 0
    n_empty_eps = 0
    n_strings = 0
    n_full_match = 0
    n_split_clean = 0
    n_split_partial = 0
    n_unresolved_total = 0
    unresolved_counter: Counter[str] = Counter()

    with TRACKLISTS_FILE.open() as fin, CANONICAL_FILE.open("w") as fout:
        for line in fin:
            r = json.loads(line)
            tracks = r.get("tracks") or []
            n_episodes += 1
            if not tracks:
                n_empty_eps += 1
            ids: set[int] = set()
            n_unresolved_ep = 0
            for t in tracks:
                a = (t.get("artist") or "").strip()
                if not a or a.lower() in PLACEHOLDERS:
                    continue
                n_strings += 1
                resolved_ids, unresolved_frags = resolve(a, slugs)
                if resolved_ids:
                    ids.update(resolved_ids)
                full_sl = slugify(a)
                if _lookup(full_sl, slugs) is not None:
                    n_full_match += 1
                elif resolved_ids and not unresolved_frags:
                    n_split_clean += 1
                elif resolved_ids:
                    n_split_partial += 1
                else:
                    n_unresolved_total += 1
                if unresolved_frags:
                    n_unresolved_ep += len(unresolved_frags)
                    for u in unresolved_frags:
                        unresolved_counter[u] += 1
            fout.write(json.dumps({
                "show_alias": r["show_alias"],
                "episode_alias": r["episode_alias"],
                "artist_ids": sorted(ids),
                "n_tracks": len(tracks),
                "n_unresolved": n_unresolved_ep,
            }, ensure_ascii=False) + "\n")

    with UNRESOLVED_FILE.open("w") as f:
        for s, c in unresolved_counter.most_common():
            f.write(json.dumps({"fragment": s, "count": c}, ensure_ascii=False) + "\n")

    print(f"\nepisodes: {n_episodes} ({n_empty_eps} empty)", file=sys.stderr)
    print(f"artist strings processed: {n_strings}", file=sys.stderr)
    if n_strings:
        def pct(n): return f"{100*n/n_strings:.1f}%"
        n_unresolved_strings = n_unresolved_total
        print(f"  full-string match:       {n_full_match:>7}  ({pct(n_full_match)})", file=sys.stderr)
        print(f"  split, all parts hit:    {n_split_clean:>7}  ({pct(n_split_clean)})", file=sys.stderr)
        print(f"  split, some parts hit:   {n_split_partial:>7}  ({pct(n_split_partial)})", file=sys.stderr)
        print(f"  fully unresolved:        {n_unresolved_strings:>7}  ({pct(n_unresolved_strings)})", file=sys.stderr)
    print(f"distinct unresolved fragments: {len(unresolved_counter)}", file=sys.stderr)


def probe(s: str) -> None:
    slugs = load_artist_sitemap()
    ids, unresolved = resolve(s, slugs)
    print(f"input:      {s!r}")
    print(f"slug:       {slugify(s)!r}")
    print(f"comma split: {[p.strip() for p in COMMA_RE.split(s)]}")
    print(f"resolved:   {ids}")
    print(f"unresolved: {unresolved}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--probe", help="debug-resolve a single string and exit")
    args = p.parse_args()
    if args.probe:
        probe(args.probe)
    else:
        canonicalize_all()


if __name__ == "__main__":
    main()
