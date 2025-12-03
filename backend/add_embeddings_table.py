import sqlite3

con = sqlite3.connect("data/tagle.sqlite")
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS embeddings (
    photo_id INTEGER PRIMARY KEY,
    embedding BLOB,
    FOREIGN KEY(photo_id) REFERENCES photos(id)
);
""")

con.commit()
con.close()
print("Embeddings table created")