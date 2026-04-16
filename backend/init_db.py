import sqlite3, os
#os.makedirs("data", exist_ok=True)

con = sqlite3.connect("data/tagle.sqlite")
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS photos (
  id INTEGER PRIMARY KEY,
  file_path TEXT UNIQUE,
  file_hash TEXT,
  width INTEGER,
  height INTEGER,
  date_taken TEXT,
  gps_lat REAL,
  gps_lon REAL,
  camera_make TEXT,
  camera_model TEXT,
  caption TEXT,
  tags TEXT,
  location_name TEXT,
  processed_at TEXT DEFAULT (datetime('now'))
);
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_hash ON photos(file_hash);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_date ON photos(date_taken);")

# Migration: add location_name column if missing (for existing databases)
try:
    cur.execute("ALTER TABLE photos ADD COLUMN location_name TEXT")
except sqlite3.OperationalError:
    pass  # column already exists

# Face recognition tables
cur.execute("""
CREATE TABLE IF NOT EXISTS faces (
  id INTEGER PRIMARY KEY,
  photo_id INTEGER NOT NULL,
  embedding BLOB NOT NULL,
  bbox TEXT,
  det_score REAL,
  cluster_id INTEGER,
  FOREIGN KEY(photo_id) REFERENCES photos(id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS people (
  cluster_id INTEGER PRIMARY KEY,
  name TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_faces_photo ON faces(photo_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_faces_cluster ON faces(cluster_id);")

con.commit()
con.close()
print("Database initialized: data/tagle.sqlite")