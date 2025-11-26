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
  processed_at TEXT DEFAULT (datetime('now'))
);
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_hash ON photos(file_hash);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_photos_date ON photos(date_taken);")
con.commit()
con.close()
print("Database initialized: data/tagle.sqlite")