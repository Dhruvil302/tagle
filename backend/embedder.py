import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from PIL import Image
import torch
from tqdm import tqdm

DB="data/tagle.sqlite"
model=SentenceTransformer("clip-ViT-B-32")

def get_unembedded(limit=200):
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute(""" SELECT id, file_path
                FROM photos
                WHERE id NOT IN (SELECT photo_id FROM embeddings)
                LIMIT ?""", (limit,))
    rows=cur.fetchall()
    con.close()
    return rows

def save_embedding(photo_id, emb: np.ndarray):
    con=sqlite3.connect(DB)
    cur= con.cursor()
    cur.execute("INSERT OR REPLACE INTO embeddings(photo_id, embedding) VALUES (?,?)",(photo_id, emb.tobytes()))
    con.commit()
    con.close()

def embed_image(path):
    img= Image.open(path).convert("RGB")
    return model.encode(img, convert_to_numpy=True)

def run(batch=300):
    rows=get_unembedded(batch)
    for photo_id, path in tqdm(rows, desc="Embedding"):
        try:
            emb=embed_image(path)
            save_embedding(photo_id, emb)
        except Exception as e:
            print("Error:", path,e)

if __name__=="__main__":
    run()
    print("Embeddings generated")