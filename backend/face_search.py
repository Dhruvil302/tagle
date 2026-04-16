"""
Face-related query helpers for the Streamlit UI.

Kept thin — the UI filters by cluster membership rather than running
nearest-neighbour face search at query time.
"""

import sqlite3

DB = "data/tagle.sqlite"


def list_people(db_path=DB):
    """
    Returns: list of (cluster_id, name, face_count, sample_photo_path, sample_bbox_json)
    The sample is the highest-confidence face detection in the cluster, with its bbox
    so callers can crop the face out of the full photo for a usable thumbnail.
    Ordered: named people first (alphabetical), then unnamed by largest first.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        SELECT
          p.cluster_id,
          p.name,
          COUNT(f.id) AS face_count,
          (SELECT ph.file_path
             FROM faces f2 JOIN photos ph ON ph.id = f2.photo_id
             WHERE f2.cluster_id = p.cluster_id
             ORDER BY f2.det_score DESC LIMIT 1) AS sample_path,
          (SELECT f3.bbox
             FROM faces f3
             WHERE f3.cluster_id = p.cluster_id
             ORDER BY f3.det_score DESC LIMIT 1) AS sample_bbox
        FROM people p
        LEFT JOIN faces f ON f.cluster_id = p.cluster_id
        GROUP BY p.cluster_id, p.name
        ORDER BY (p.name IS NULL), p.name, face_count DESC
        """
    )
    rows = cur.fetchall()
    con.close()
    return rows


def photo_ids_for_cluster(cluster_id, db_path=DB):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "SELECT DISTINCT photo_id FROM faces WHERE cluster_id = ?",
        (cluster_id,),
    )
    ids = {row[0] for row in cur.fetchall()}
    con.close()
    return ids


def rename_person(cluster_id, name, db_path=DB):
    name = (name or "").strip() or None
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO people(cluster_id, name, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(cluster_id) DO UPDATE SET
          name = excluded.name,
          updated_at = datetime('now')
        """,
        (cluster_id, name),
    )
    con.commit()
    con.close()


def names_for_photo(photo_id, db_path=DB):
    """Return named persons appearing in a photo (excludes unnamed clusters)."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        SELECT DISTINCT p.name
        FROM faces f JOIN people p ON p.cluster_id = f.cluster_id
        WHERE f.photo_id = ? AND p.name IS NOT NULL AND p.name != ''
        """,
        (photo_id,),
    )
    names = [row[0] for row in cur.fetchall()]
    con.close()
    return names
