"""
Cluster face embeddings into person groups using DBSCAN.

Reads all real face rows (det_score > 0) from the faces table, runs DBSCAN on
their embeddings, writes cluster_id back, and ensures every cluster has a row
in the people table (name left NULL until user assigns one).

Run:
    python backend/cluster_faces.py
    python backend/cluster_faces.py --eps 0.45 --min-samples 2
"""

import argparse
import sqlite3

import numpy as np
from sklearn.cluster import DBSCAN

DB = "data/tagle.sqlite"


def load_face_embeddings():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "SELECT id, embedding FROM faces WHERE det_score > 0 AND LENGTH(embedding) > 0"
    )
    rows = cur.fetchall()
    con.close()

    if not rows:
        return np.array([]), np.array([])

    ids = np.array([r[0] for r in rows], dtype=np.int64)
    embs = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    return ids, embs


def write_cluster_ids(face_ids, labels):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executemany(
        "UPDATE faces SET cluster_id = ? WHERE id = ?",
        [(int(lbl), int(fid)) for fid, lbl in zip(face_ids, labels)],
    )
    # Preserve existing names; just make sure every cluster is represented
    unique_clusters = {int(l) for l in labels if int(l) != -1}
    for cid in unique_clusters:
        cur.execute(
            "INSERT OR IGNORE INTO people(cluster_id, name) VALUES (?, NULL)",
            (cid,),
        )
    con.commit()
    con.close()


def run(eps=0.4, min_samples=3):
    face_ids, embs = load_face_embeddings()
    if len(face_ids) == 0:
        print("No face embeddings found. Run face_detect.py first.")
        return

    print(f"Clustering {len(face_ids)} face embeddings (eps={eps}, min_samples={min_samples})...")
    # Embeddings from InsightFace are already L2-normalized, so cosine ≈ Euclidean on sphere
    clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = clusterer.fit_predict(embs)

    n_clusters = len({l for l in labels if l != -1})
    n_noise = int((labels == -1).sum())
    print(f"Found {n_clusters} clusters, {n_noise} noise faces.")

    write_cluster_ids(face_ids, labels)
    print("Cluster assignments saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eps", type=float, default=0.4)
    parser.add_argument("--min-samples", type=int, default=3)
    args = parser.parse_args()
    run(eps=args.eps, min_samples=args.min_samples)
