# app.py - Streamlit UI for Tagle

import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

import streamlit as st
from PIL import Image

from backend.semantic_search import search as semantic_search

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
):
    """Simple LIKE-based keyword search on caption + tags with optional filters."""
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return []

    where_clauses = []
    params: List = []

    # text search
    text_clause = " AND ".join(["(LOWER(caption) LIKE ? OR LOWER(tags) LIKE ?)"] * len(terms))
    where_clauses.append(text_clause)
    for t in terms:
        like = f"%{t}%"
        params.extend([like, like])

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

    where_sql = " AND ".join(where_clauses)

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT file_path, caption, tags, date_taken, gps_lat, gps_lon
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
):
    """Fetch most recent photos, optionally filtered by date/location."""
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

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    con = get_db_connection()
    cur = con.cursor()
    cur.execute(
        f"""
        SELECT file_path, caption, tags, date_taken, gps_lat, gps_lon
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


def passes_filters(
    date_taken: Optional[str],
    gps_lat: Optional[float],
    gps_lon: Optional[float],
    year_range: Optional[Tuple[int, int]],
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
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

    return True


def enrich_semantic_results(
    semantic_rows,
    year_range: Optional[Tuple[int, int]],
    lat_range: Optional[Tuple[float, float]],
    lon_range: Optional[Tuple[float, float]],
    max_results: int,
):
    """
    Take semantic_search rows (file_path, caption, tags),
    attach date_taken and gps from DB, and apply filters.
    """
    con = get_db_connection()
    cur = con.cursor()

    enriched = []
    for (path, cap, tags) in semantic_rows:
        cur.execute(
            """
            SELECT file_path, caption, tags, date_taken, gps_lat, gps_lon
            FROM photos WHERE file_path = ?
            """,
            (path,),
        )
        row = cur.fetchone()
        if row is None:
            continue
        p, c, t, d, lat, lon = row
        if passes_filters(d, lat, lon, year_range, lat_range, lon_range):
            # prefer DB caption/tags if present
            caption = c or cap
            tag_val = t or tags
            enriched.append((p, caption, tag_val, d, lat, lon))
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
    )
else:
    st.subheader(f"Results for: {query!r}")

    if mode.startswith("Semantic"):
        # Pure semantic search with post-filtering by metadata
        try:
            sem_results = semantic_search(query, top_k=max_results * 2)
            enriched = enrich_semantic_results(
                sem_results, year_range, lat_range, lon_range, max_results
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
        )

        # Build RRF scores: score(d) = sum( 1 / (k + rank_i) ) across lists
        rrf_scores: dict[str, float] = {}

        # Semantic ranks (already ordered by FAISS distance)
        for rank, (p, _c, _t) in enumerate(sem_raw, start=1):
            rrf_scores[p] = rrf_scores.get(p, 0.0) + 1.0 / (RRF_K + rank)

        # Keyword ranks (ordered by date DESC from SQL)
        for rank, (p, _c, _t, _d, _lat, _lon) in enumerate(kw_raw, start=1):
            rrf_scores[p] = rrf_scores.get(p, 0.0) + 1.0 / (RRF_K + rank)

        # Sort by fused score descending
        ranked_paths = sorted(rrf_scores, key=rrf_scores.get, reverse=True)

        # Build a metadata lookup from keyword results (already filtered)
        kw_map = {p: (c, t, d, lat, lon) for (p, c, t, d, lat, lon) in kw_raw}
        sem_map = {p: (c, t) for (p, c, t) in sem_raw}

        # Enrich and apply filters for results that came only from semantic side
        con = get_db_connection()
        cur = con.cursor()
        combined = []
        for p in ranked_paths:
            if p in kw_map:
                c, t, d, lat, lon = kw_map[p]
            else:
                # Semantic-only result: fetch metadata and apply filters
                cur.execute(
                    "SELECT caption, tags, date_taken, gps_lat, gps_lon FROM photos WHERE file_path = ?",
                    (p,),
                )
                row = cur.fetchone()
                if row is None:
                    continue
                c, t, d, lat, lon = row
                if not passes_filters(d, lat, lon, year_range, lat_range, lon_range):
                    continue
                # Prefer DB values, fall back to semantic result
                sem_c, sem_t = sem_map.get(p, (None, None))
                c = c or sem_c
                t = t or sem_t
            combined.append((p, c, t, d, lat, lon))
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
        path, caption, tags, date_taken, gps_lat, gps_lon = row
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
            meta_bits = []
            if date_taken:
                meta_bits.append(f"📅 {date_taken}")
            if gps_lat is not None and gps_lon is not None:
                meta_bits.append(f"📍 ({gps_lat:.3f}, {gps_lon:.3f})")
            if meta_bits:
                st.write(" • ".join(meta_bits))