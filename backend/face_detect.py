"""
Face detection + embedding stage.

For each photo not yet processed, detects faces via InsightFace's buffalo_l
model and stores (photo_id, embedding, bbox, det_score) rows into the faces table.

Run:
    python backend/face_detect.py
"""

import json
import sqlite3

import numpy as np
from tqdm import tqdm

try:
    from insightface.app import FaceAnalysis
except ImportError as e:
    raise SystemExit(
        "insightface not installed. Run: pip install insightface onnxruntime"
    ) from e

import cv2

DB = "data/tagle.sqlite"


def load_model():
    # CPU-only by default; add GPU providers if available
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def get_unprocessed_photos(limit=500):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, file_path FROM photos
        WHERE id NOT IN (SELECT DISTINCT photo_id FROM faces)
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    con.close()
    return rows


def mark_no_faces(photo_id):
    """
    Insert a sentinel row so this photo is not re-scanned next run.
    We use a single row with a zero-length embedding blob and det_score=-1
    to signal 'processed, no faces found'.
    """
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO faces(photo_id, embedding, bbox, det_score) VALUES (?,?,?,?)",
        (photo_id, b"", None, -1.0),
    )
    con.commit()
    con.close()


def save_faces(photo_id, faces):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for f in faces:
        emb = f.normed_embedding.astype(np.float32)  # 512-d, L2-normalized
        bbox = json.dumps([float(x) for x in f.bbox.tolist()])
        cur.execute(
            "INSERT INTO faces(photo_id, embedding, bbox, det_score) VALUES (?,?,?,?)",
            (photo_id, emb.tobytes(), bbox, float(f.det_score)),
        )
    con.commit()
    con.close()


def detect_in_photo(app, path):
    img = cv2.imread(path)
    if img is None:
        return None  # unreadable
    return app.get(img)


def run(batch=1000):
    rows = get_unprocessed_photos(batch)
    if not rows:
        print("No new photos to process for faces.")
        return

    print(f"Loading InsightFace model...")
    app = load_model()

    for photo_id, path in tqdm(rows, desc="Detecting faces"):
        try:
            faces = detect_in_photo(app, path)
            if faces is None:
                continue  # skip unreadable; don't mark so it retries later
            if len(faces) == 0:
                mark_no_faces(photo_id)
            else:
                save_faces(photo_id, faces)
        except Exception as e:
            print(f"Error processing {path}: {e}")


if __name__ == "__main__":
    run()
    print("Face detection complete")
