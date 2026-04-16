# app.py - Streamlit UI for Tagle

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from PIL import Image

from backend.semantic_search import search as semantic_search
from backend.face_search import (
    list_people,
    photo_ids_for_cluster,
    rename_person,
    names_for_photo,
)

# Paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "tagle.sqlite"


# ---------- Data helpers ----------

def get_db_connection():
    return sqlite3.connect(DB_PATH)


@st.cache_data
def get_metadata_bounds():
    """
    Compute bounds for date (years) and GPS (lat/lon) based on what's in the DB.
    Returns:
        (min_year, max_year, lat_min, lat_max, lon_min, lon_max)
        Any of them may be None if not available.
    """
    con = get_db_connection()
    cur = con.cursor()

    # Date bounds (year from EXIF string like 'YYYY:MM:DD HH:MM:SS')
    cur.execute("SELECT date_taken FROM photos WHERE date_taken IS NOT NULL AND date_taken != ''")
    dates = [row[0] for row in cur.fetchall()]
    years = []
    for d in dates:
        # Typically 'YYYY:MM:DD ...'
        if len(d) >= 4 and d[:4].isdigit():
            years.append(int(d[:4]))
    min_year = min(years) if years else None
    max_year = max(years) if years else None

    # GPS bounds
    cur.execute(
        """
        SELECT MIN(gps_lat), MAX(gps_lat), MIN(gps_lon), MAX(gps_lon)
        FROM photos
        WHERE gps_lat IS NOT NULL AND gps_lon IS NOT NULL
        """
    )
    lat_min, lat_max, lon_min, lon_max = cur.fetchone()
    con.close()

    return min_year, max_year, lat_min, lat_max, lon_min, lon_max


def keyword_search(
    query: str,
    limit: int = 50,
    year_range: Optional[Tuple[int, int]] = None,
    lat_range: Optional[Tuple[float, float]] = None,
    lon_range: Optional[Tuple[float, float]] = None,
    photo_id_filter: Optional[set] = None,
):
    """Simple LIKE-based keyword search on caption + tags with optional filters."""
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return []

    # Short-circuit: person filter with empty set → no results possible
    if photo_id_filter is not None and len(photo_id_filter) == 0:
        return []

    where_clauses = []
    params: List = []

    # text search
    text_clause = " AND ".join(["(LOWER(caption) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(location_name) LIKE ?)"] * len(terms))
    where_clauses.append(text_clause)
    for t in terms:
        like = f"%{t}%"
        params.extend([like, like, like])

    # year filter
    if year_range is not None:
        y_min, y_max = year_range
        # substr(date_taken,1,4) = 'YYYY'
        where_clauses.append(
            "date_taken IS NOT NULL AND date_taken != '' AND CAST(SUBSTR(date_taken,1,4) AS INTEGER) BETWEEN ? AND ?"
        )
        params.extend([y_min, y_max])

    # location filter
    if lat_range is not None and lon_range is not None:
        lat_min, lat_max = lat_range
        lon_min, lon_max = lon_range
        where_clauses.append(
            "gps_lat IS NOT NULL AND gps_lon IS NOT NULL AND gps_lat BETWEEN ? AND ? AND gps_lon BETWEEN ? AND ?"
        )
        params.extend([lat_min, lat_max, lon_min, lon_max])

    # person filter (photo_ids from a face cluster)
    if photo_id_filter is not None:
        placeholders = ",".join("?" * len(photo_id_filter))
        where_clauses.append(f"id IN ({placeholders})")
        params.extend(photo_id_filter)

    where_sql = " AND ".join(where_clauses)

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT id, file_path, caption, tags, date_taken, gps_lat, gps_lon
        FROM photos
        WHERE {where_sql}
        ORDER BY date_taken DESC, id DESC
        LIMIT ?
        """,
        (*params, limit),
    )
    rows = cur.fetchall()
    con.close()
    return rows


def get_recent_photos(
    limit: int = 50,
    year_range: Optional[Tuple[int, int]] = None,
    lat_range: Optional[Tuple[float, float]] = None,
    lon_range: Optional[Tuple[float, float]] = None,
    photo_id_filter: Optional[set] = None,
):
    """Fetch most recent photos, optionally filtered by date/location/person."""
    if photo_id_filter is not None and len(photo_id_filter) == 0:
        return []

    where_clauses = []
    params: List = []

    if year_range is not None:
        y_min, y_max = year_range
        where_clauses.append(
            "date_taken IS NOT NULL AND date_taken != '' AND CAST(SUBSTR(date_taken,1,4) AS INTEGER) BETWEEN ? AND ?"
        )
        params.extend([y_min, y_max])

    if lat_range is not None and lon_range is not None:
        lat_min, lat_max = lat_range
        lon_min, lon_max = lon_range
        where_clauses.append(
            "gps_lat IS NOT NULL AND gps_lon IS NOT NULL AND gps_lat BETWEEN ? AND ? AND gps_lon BETWEEN ? AND ?"
        )
        params.extend([lat_min, lat_max, lon_min, lon_max])

    if photo_id_filter is not None:
        placeholders = ",".join("?" * len(photo_id_filter))
        where_clauses.append(f"id IN ({placeholders})")
        params.extend(photo_id_filter)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT id, file_path, caption, tags, date_taken, gps_lat, gps_lon
        FROM photos
        {where_sql}
        ORDER BY date_taken DESC, id DESC
        LIMIT ?
        """,
        (*params, limit),
    )
    rows = cur.fetchall()
    con.close()
    return rows


def open_image(path_str: str):
    """Open an image using PIL, handling relative paths."""
    img_path = BASE_DIR / Path(path_str)
    if not img_path.is_file():
        # Try without BASE_DIR (if paths are already absolute)
        img_path = Path(path_str)
    try:
        return Image.open(img_path).convert("RGB")
    except Exception:
        return None


def crop_face(path_str: str, bbox_json: Optional[str], pad: float = 0.25):
    """
    Return a face crop (PIL image) from `path_str` using the JSON bbox [x1,y1,x2,y2].
    Adds `pad` fraction of the face size as padding so hair/chin are visible.
    Falls back to the full image if bbox is missing or invalid.
    """
    img = open_image(path_str)
    if img is None:
        return None
    if not bbox_json:
        return img
    try:
        x1, y1, x2, y2 = json.loads(bbox_json)
    except (ValueError, TypeError, json.JSONDecodeError):
        return img

    w, h = img.size
    fw = max(1.0, x2 - x1)
    fh = max(1.0, y2 - y1)
    px = fw * pad
    py = fh * pad
    left = max(0, int(x1 - px))
    top = max(0, int(y1 - py))
    right = min(w, int(x2 + px))
    bottom = min(h, int(y2 + py))
    if right <= left or bottom <= top:
        return img
    return img.crop((left, top, right, bottom))


def passes_filters(
    date_taken: Optional[str],
    gps_lat: Optional[float],
    gps_lon: Optional[float],
    year_range: Optional[Tuple[int, int]],
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
    photo_id: Optional[int] = None,
    photo_id_filter: Optional[set] = None,
) -> bool:
    """Filter helper for semantic results (which we post-filter using DB metadata)."""
    # Date filter
    if year_range is not None:
        y_min, y_max = year_range
        year = None
        if date_taken and len(date_taken) >= 4 and date_taken[:4].isdigit():
            year = int(date_taken[:4])
        if year is None or not (y_min <= year <= y_max):
            return False

    # Location filter
    if lat_range is not None and lon_range is not None:
        lat_min, lat_max = lat_range
        lon_min, lon_max = lon_range
        if gps_lat is None or gps_lon is None:
            return False
        if not (lat_min <= gps_lat <= lat_max and lon_min <= gps_lon <= lon_max):
            return False

    # Person filter
    if photo_id_filter is not None:
        if photo_id is None or photo_id not in photo_id_filter:
            return False

    return True


def enrich_semantic_results(
    semantic_rows,
    year_range: Optional[Tuple[int, int]],
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
    max_results: int,
    photo_id_filter: Optional[set] = None,
):
    """
    Take semantic_search rows (file_path, caption, tags),
    attach id/date_taken/gps from DB, and apply filters.
    """
    con = get_db_connection()
    cur = con.cursor()

    enriched = []
    for (path, cap, tags) in semantic_rows:
        cur.execute(
            """
            SELECT id, file_path, caption, tags, date_taken, gps_lat, gps_lon
            FROM photos WHERE file_path = ?
            """,
            (path,),
        )
        row = cur.fetchone()
        if row is None:
            continue
        pid, p, c, t, d, lat, lon = row
        if passes_filters(d, lat, lon, year_range, lat_range, lon_range,
                          photo_id=pid, photo_id_filter=photo_id_filter):
            # prefer DB caption/tags if present
            caption = c or cap
            tag_val = t or tags
            enriched.append((pid, p, caption, tag_val, d, lat, lon))
        if len(enriched) >= max_results:
            break

    con.close()
    return enriched


# ---------- UI ----------

st.set_page_config(
    page_title="Tagle",
    layout="wide",
)

st.title("📸 Tagle")
st.caption("Your photos. Organized locally.")

min_year, max_year, lat_min, lat_max, lon_min, lon_max = get_metadata_bounds()

with st.sidebar:
    st.header("Search options")
    mode = st.radio(
        "Search mode",
        [
            "Semantic (CLIP)",
            "Keyword (caption + tags)",
            "Combined (Rank Fusion)",
        ],
        index=0,
    )
    max_results = st.slider("Max results", min_value=10, max_value=100, value=30, step=10)

    st.markdown("---")
    st.subheader("Filters")

    # Date filter
    year_range = None
    if min_year is not None and max_year is not None and min_year <= max_year:
        enable_date = st.checkbox("Filter by date (year)", value=False)
        if enable_date:
            year_range = st.slider(
                "Year range",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year),
            )

    # Location filter
    lat_range = lon_range = None
    if (
        lat_min is not None
        and lat_max is not None
        and lon_min is not None
        and lon_max is not None
    ):
        enable_loc = st.checkbox("Filter by location (lat/lon)", value=False)
        if enable_loc:
            lat_range = st.slider(
                "Latitude range",
                min_value=float(lat_min),
                max_value=float(lat_max),
                value=(float(lat_min), float(lat_max)),
            )
            lon_range = st.slider(
                "Longitude range",
                min_value=float(lon_min),
                max_value=float(lon_max),
                value=(float(lon_min), float(lon_max)),
            )

    # Person filter
    photo_id_filter = None
    people_rows = list_people()
    if people_rows:
        enable_person = st.checkbox("Filter by person", value=False)
        if enable_person:
            person_labels = {
                cid: (name if name else f"Unnamed #{cid} ({count} faces)")
                for (cid, name, count, _sp, _bb) in people_rows
            }
            selected_cluster = st.selectbox(
                "Person",
                options=list(person_labels.keys()),
                format_func=lambda cid: person_labels[cid],
            )
            photo_id_filter = photo_ids_for_cluster(selected_cluster)

    # Manage people
    if people_rows:
        with st.expander("Manage people"):
            st.caption("Assign a name to each face cluster. Names persist across searches.")
            for (cid, name, count, sample_path, sample_bbox) in people_rows:
                cols = st.columns([1, 3])
                with cols[0]:
                    if sample_path:
                        face_img = crop_face(sample_path, sample_bbox)
                        if face_img is not None:
                            st.image(face_img, width=120)
                with cols[1]:
                    new_name = st.text_input(
                        f"Cluster #{cid} ({count} faces)",
                        value=name or "",
                        key=f"person_name_{cid}",
                    )
                    if new_name != (name or ""):
                        if st.button("Save", key=f"save_{cid}"):
                            rename_person(cid, new_name)
                            st.rerun()

    st.markdown("---")
    st.markdown("**Tip:** Make sure you ran the ingest pipeline first:")
    st.code("python backend/ingest.py photos", language="bash")

query = st.text_input("Search your photos", placeholder="e.g. dog on the beach at sunset")

if not query.strip():
    st.subheader("Recent photos")
    results = get_recent_photos(
        limit=max_results,
        year_range=year_range,
        lat_range=lat_range,
        lon_range=lon_range,
        photo_id_filter=photo_id_filter,
    )
else:
    st.subheader(f"Results for: {query!r}")

    if mode.startswith("Semantic"):
        # Pure semantic search with post-filtering by metadata
        try:
            sem_results = semantic_search(query, top_k=max_results * 2)
            enriched = enrich_semantic_results(
                sem_results, year_range, lat_range, lon_range, max_results,
                photo_id_filter=photo_id_filter,
            )
            results = enriched
        except Exception as e:
            st.error(f"Semantic search failed: {e}")
            results = []

    elif mode.startswith("Keyword"):
        # Pure keyword search with filters in SQL
        results = keyword_search(
            query,
            limit=max_results,
            year_range=year_range,
            lat_range=lat_range,
            lon_range=lon_range,
            photo_id_filter=photo_id_filter,
        )

    else:
        # Combined (Rank Fusion): merge semantic + keyword via Reciprocal Rank Fusion
        RRF_K = 60  # standard RRF constant to dampen high-rank dominance

        try:
            sem_raw = semantic_search(query, top_k=max_results * 3)
        except Exception as e:
            st.error(f"Semantic search failed: {e}")
            sem_raw = []

        kw_raw = keyword_search(
            query,
            limit=max_results * 3,
            year_range=year_range,
            lat_range=lat_range,
            lon_range=lon_range,
            photo_id_filter=photo_id_filter,
        )

        # Build RRF scores: score(d) = sum( 1 / (k + rank_i) ) across lists
        rrf_scores: dict[str, float] = {}

        # Semantic ranks (already ordered by FAISS distance)
        for rank, (p, _c, _t) in enumerate(sem_raw, start=1):
            rrf_scores[p] = rrf_scores.get(p, 0.0) + 1.0 / (RRF_K + rank)

        # Keyword ranks (ordered by date DESC from SQL)
        for rank, (_pid, p, _c, _t, _d, _lat, _lon) in enumerate(kw_raw, start=1):
            rrf_scores[p] = rrf_scores.get(p, 0.0) + 1.0 / (RRF_K + rank)

        # Sort by fused score descending
        ranked_paths = sorted(rrf_scores, key=rrf_scores.get, reverse=True)

        # Build a metadata lookup from keyword results (already filtered)
        kw_map = {p: (pid, c, t, d, lat, lon) for (pid, p, c, t, d, lat, lon) in kw_raw}
        sem_map = {p: (c, t) for (p, c, t) in sem_raw}

        # Enrich and apply filters for results that came only from semantic side
        con = get_db_connection()
        cur = con.cursor()
        combined = []
        for p in ranked_paths:
            if p in kw_map:
                pid, c, t, d, lat, lon = kw_map[p]
            else:
                # Semantic-only result: fetch metadata and apply filters
                cur.execute(
                    "SELECT id, caption, tags, date_taken, gps_lat, gps_lon FROM photos WHERE file_path = ?",
                    (p,),
                )
                row = cur.fetchone()
                if row is None:
                    continue
                pid, c, t, d, lat, lon = row
                if not passes_filters(d, lat, lon, year_range, lat_range, lon_range,
                                      photo_id=pid, photo_id_filter=photo_id_filter):
                    continue
                # Prefer DB values, fall back to semantic result
                sem_c, sem_t = sem_map.get(p, (None, None))
                c = c or sem_c
                t = t or sem_t
            combined.append((pid, p, c, t, d, lat, lon))
            if len(combined) >= max_results:
                break
        con.close()

        results = combined

        st.caption(
            "Combined mode: results ranked using Reciprocal Rank Fusion (RRF) — "
            "photos appearing high in both semantic and keyword results are boosted."
        )

if not results:
    if query.strip():
        st.info("No results for this combination. Try a broader query, different filters, or another mode.")
    else:
        st.info("No photos found yet. Add images to the 'photos/' folder and run the ingest pipeline.")
else:
    # Display as a grid
    cols_per_row = 4
    cols = st.columns(cols_per_row)

    for i, row in enumerate(results):
        # row can be: (file_path, caption, tags, date_taken, gps_lat, gps_lon)
        # from keyword / recent / combined / enriched semantic
        photo_id, path, caption, tags, date_taken, gps_lat, gps_lon = row
        col = cols[i % cols_per_row]
        with col:
            img = open_image(path)
            if img is not None:
                st.image(img, width='stretch')
            else:
                st.write("🚫 Image not found")

            st.markdown(f"**`{Path(path).name}`**", help=str(path))
            if caption:
                st.caption(caption)
            if tags:
                st.write("`" + str(tags) + "`")
            people_in_photo = names_for_photo(photo_id)
            if people_in_photo:
                st.write("👤 " + ", ".join(people_in_photo))
            meta_bits = []
            if date_taken:
                meta_bits.append(f"📅 {date_taken}")
            if gps_lat is not None and gps_lon is not None:
                meta_bits.append(f"📍 ({gps_lat:.3f}, {gps_lon:.3f})")
            if meta_bits:
                st.write(" • ".join(meta_bits))