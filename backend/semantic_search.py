import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import sys
import os

DB = "data/tagle.sqlite"
INDEX_PATH = "data/tagle.index"
IDS_PATH = "data/tagle_ids.npy"

# Load CLIP text encoder
model = SentenceTransformer("clip-ViT-B-32")

def search(query, top_k=10):
    # embed query
    q_emb = model.encode([query], convert_to_numpy=True).astype("float32")

    # ensure index + ids exist
    if not os.path.exists(INDEX_PATH) or not os.path.exists(IDS_PATH):
        raise FileNotFoundError("FAISS index or tagle_ids.npy is missing. Run build_faiss.py first.")

    # load index
    index = faiss.read_index(INDEX_PATH)
    ids = np.load(IDS_PATH)

    # search
    D, I = index.search(q_emb, top_k)

    # fetch corresponding photos
    con = sqlite3.connect(DB)
    cur = con.cursor()
    results = []

    for idx in I[0]:
        if idx == -1:
            continue
        pid = int(ids[idx])
        cur.execute("SELECT file_path, caption, tags FROM photos WHERE id=?", (pid,))
        row = cur.fetchone()
        if row:
            results.append(row)

    con.close()
    return results


if __name__ == "__main__":

    if len(sys.argv) > 1:
        query = " ".join(arg for arg in sys.argv[1:] if not arg.isdigit())
        top_k = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 10

        results = search(query, top_k=top_k)

        for p, c, t in results:
            print("📸", p)
            print("   caption:", c)
            print("   tags:", t)
            print()
    else:
        print("Usage: python backend/semantic_search.py \"query\" [top_k]")