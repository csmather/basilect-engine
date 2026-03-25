"""Update all artist JSON files with MBIDs and fresh genres from MusicBrainz."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from musicbrainz import fetch_genres_by_mbid

DATA_DIR = Path(__file__).parent.parent / "data" / "artists"

ARTISTS = [
    ("alex_g", "7df4c4de-3181-4a69-bd36-9d663970cebb"),
    ("animal_collective", "0c751690-c784-4a4f-b1e4-c1de27d47581"),
    ("aphex_twin", "f22942a1-6f70-4f48-866e-238cb2308fbd"),
    ("badbadnotgood", "754294d5-d7d2-4ea2-8184-1dcaaf55a56f"),
    ("bill_evans", "8247a3f2-3a8e-4256-b322-6c57b03a4e36"),
    ("bladee", "cd689e77-dfdd-4f81-b50c-5e5a3f5e38a4"),
    ("brian_eno", "ff95eb47-41c4-4f7f-a104-cdc30f02e872"),
    ("danny_brown", "960afc67-9c21-46dd-9c7f-ff2b509e3150"),
    ("earl_sweatshirt", "8b22acd6-20e6-4463-a75c-c14b5cfdb666"),
    ("faye_webster", "ce4a1c08-6912-423f-bf6c-97ce69f5e89f"),
    ("fishmans", "d0f25f16-7782-42e8-8047-c16a1cb2b450"),
    ("haruomi_hosono", "078be324-de92-4c72-9371-65bdcf324154"),
    ("mgmt", "c485632c-b784-4ee9-8ea1-c5fb365681fc"),
    ("neil_young", "75167b8b-44e4-407b-9d35-effe87b223cf"),
    ("nujabes", "1595addf-f76b-450a-a097-af852ff35f27"),
    ("skrillex", "ae002c5d-aac6-490b-a39a-30aa9e2edf2b"),
    ("the_garden", "77bc5aae-3cdf-4942-860a-4ebc67b3c280"),
    ("ween", "c0eee88b-47f2-4cd2-ac48-a045e902a432"),
    ("yung_lean", "757ed661-fbad-4e45-b1cd-a6b09f06f54a"),
]

# Yasuaki Shimizu has no MBID — manual tags provided by user
MANUAL = {
    "yasuaki_shimizu": ["ambient", "experimental", "jazz", "experimental jazz", "j-pop", "jazz fusion", "new wave"],
}


def update_artist(slug: str, mbid: str) -> None:
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        print(f"  SKIP — file not found: {path}")
        return

    with open(path) as f:
        node = json.load(f)

    print(f"  Fetching genres for {node['name']} ({mbid})...")
    genres = fetch_genres_by_mbid(mbid)

    if not genres:
        print(f"  WARNING: No genres returned from MusicBrainz for {node['name']}")
    else:
        print(f"  {len(genres)} genres: {genres}")

    node["mbid"] = mbid
    node["genres"] = genres

    with open(path, "w") as f:
        json.dump(node, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path.name}")


def update_manual(slug: str, genres: list[str]) -> None:
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        print(f"  SKIP — file not found: {path}")
        return

    with open(path) as f:
        node = json.load(f)

    node.pop("mbid", None)  # No MBID for this artist
    node["genres"] = genres

    with open(path, "w") as f:
        json.dump(node, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path.name} (manual tags)")


if __name__ == "__main__":
    print("=== Updating artist nodes with MusicBrainz genres ===\n")

    for slug, mbid in ARTISTS:
        print(f"[{slug}]")
        try:
            update_artist(slug, mbid)
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

    print("[yasuaki_shimizu]")
    update_manual("yasuaki_shimizu", MANUAL["yasuaki_shimizu"])
    print()

    print("=== Done ===")
