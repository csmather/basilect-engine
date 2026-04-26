"""Embed artist quotes using sentence-transformers.

Each artist's quotes are embedded individually, then aggregated
into a single artist-level vector via component-wise median.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
MODEL_PATH = str(Path(__file__).resolve().parent.parent / "models" / "Qwen3-Embedding-4B")
BATCH_SIZE = 8  # 4B model on 12GB VRAM; bump if headroom allows


def load_quotes():
    ids = []
    quotes_per_artist = []
    for path in sorted(ARTISTS_DIR.glob("*/quotes.json")):
        artist_id = path.parent.name
        node = json.loads(path.read_text(encoding="utf-8"))
        texts = [q["text"] for q in node["quotes"]]
        ids.append(artist_id)
        quotes_per_artist.append(texts)
    return ids, quotes_per_artist


def load_model():
    """Load Qwen3-Embedding-4B in bf16. Try flash-attn 2; fall back to sdpa."""
    base_kwargs = {"torch_dtype": "bfloat16"}
    try:
        model = SentenceTransformer(
            MODEL_PATH,
            model_kwargs={**base_kwargs, "attn_implementation": "flash_attention_2"},
            tokenizer_kwargs={"padding_side": "left"},
        )
        print("  attn: flash_attention_2")
    except (ImportError, ValueError, RuntimeError) as e:
        print(f"  flash-attn unavailable ({type(e).__name__}); using default attention")
        model = SentenceTransformer(
            MODEL_PATH,
            model_kwargs=base_kwargs,
            tokenizer_kwargs={"padding_side": "left"},
        )
    return model


def main():
    ids, quotes_per_artist = load_quotes()
    total = sum(len(q) for q in quotes_per_artist)
    print(f"Loaded {len(ids)} artists, {total} total quotes")

    print(f"Loading model: {MODEL_PATH}")
    model = load_model()

    all_quotes = []
    boundaries = []
    offset = 0
    for quotes in quotes_per_artist:
        all_quotes.extend(quotes)
        boundaries.append((offset, offset + len(quotes)))
        offset += len(quotes)

    print(f"Encoding quotes (batch_size={BATCH_SIZE})...")
    # Symmetric document embedding: no prompt prefix on either side.
    all_embeddings = model.encode(
        all_quotes,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    artist_embeddings = []
    quote_index = []
    for i, (start, end) in enumerate(boundaries):
        vecs = all_embeddings[start:end]
        median_vec = np.median(vecs, axis=0)
        artist_embeddings.append(median_vec)
        for q_idx in range(end - start):
            quote_index.append({"artist_id": ids[i], "quote_idx": q_idx})
        print(f"  {ids[i]}: {end - start} quotes -> median vector")

    embeddings = np.array(artist_embeddings)

    np.save(DATA_DIR / "embeddings.npy", embeddings)
    np.save(DATA_DIR / "quote_embeddings.npy", all_embeddings)
    (DATA_DIR / "embedding_ids.json").write_text(
        json.dumps(ids, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "quote_index.json").write_text(
        json.dumps(quote_index, indent=2), encoding="utf-8"
    )

    print(f"\nSaved embeddings: {embeddings.shape} to data/embeddings.npy")
    print(f"Saved artist order: {len(ids)} IDs to data/embedding_ids.json")
    print(f"Saved quote embeddings: {all_embeddings.shape} to data/quote_embeddings.npy")
    print(f"Saved quote index: {len(quote_index)} rows to data/quote_index.json")


if __name__ == "__main__":
    main()
