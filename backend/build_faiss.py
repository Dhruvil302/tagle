import sqlite3, faiss, numpy as np, os

DB = "data/tagle.sqlite"
INDEX_PATH = "data/tagle.index"

def load_embeddings():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT photo_id, embedding FROM embeddings")
    rows = cur.fetchall()
    con.close()

    ids = []
    embs = []
    for pid, blob in rows:
        emb = np.frombuffer(blob, dtype=np.float32)
        ids.append(pid)
        embs.append(emb)

    return np.vstack(embs), np.array(ids)

def build_index():
    X, ids = load_embeddings()
    dim = X.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(X)
    faiss.write_index(index, INDEX_PATH)

    # save ids separately
    np.save("data/tagle_ids.npy", ids)

    print(f"FAISS index built with {len(ids)} embeddings")

if __name__ == "__main__":
    build_index()