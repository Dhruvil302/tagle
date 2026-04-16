```text
████████╗ █████╗  ██████╗ ██╗     ███████╗
╚══██╔══╝██╔══██╗██╔════╝ ██║     ██╔════╝
   ██║   ███████║██║  ███╗██║     █████╗  
   ██║   ██╔══██║██║   ██║██║     ██╔══╝  
   ██║   ██║  ██║╚██████╔╝███████╗███████╗
   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝

                     T A G L E
        Your photos. Organized locally.
```
<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/offline-AI-orange" />
  <img src="https://img.shields.io/badge/captions-BLIP-black" />
  <img src="https://img.shields.io/badge/semantic-CLIP%20%2B%20FAISS-purple" />
  <img src="https://img.shields.io/badge/faces-InsightFace-red" />
  <img src="https://img.shields.io/badge/UI-Streamlit-ff4b4b" />
</p>


# 🏷️ Tagle
> **Your photos, intelligently organized — all local.**

Tagle is a local-first photo intelligence tool.
It scans your photos, extracts EXIF metadata, generates AI captions, reverse-geocodes GPS coordinates to human-readable locations, detects and clusters faces, and lets you search everything with keyword, semantic (CLIP), or hybrid rank-fusion search — all offline.

---

## 🚀 Features

- 🖼️ **Local photo processing** — never uploads your photos
- 🧠 **AI-generated captions** using BLIP (runs offline)
- 🏷️ **Automatic keyword tagging** (lightweight NLP)
- 📅 **EXIF extraction** — date, camera, GPS
- 🗺️ **Reverse geocoding** — resolves GPS to addresses & landmarks (e.g. `Brooklyn Bridge, New York, US`) via Nominatim
- 👤 **Face recognition** — detects faces with InsightFace, clusters them into persons with DBSCAN, name them once in the UI
- 🔍 **Keyword search** across captions, tags, and location names
- ✨ **Semantic search** via CLIP + FAISS (natural-language queries)
- 🔀 **Combined rank-fusion search** using Reciprocal Rank Fusion (RRF) to merge semantic and keyword results
- 🎛️ **Streamlit web UI** with filters for date, GPS bounding box, and person
- 💾 **SQLite database** — simple, portable, single file
- 🔁 **Incremental pipeline** — only processes new files at each stage

---

## 📦 Project Structure
```markdown
tagle/
├── data/                       # SQLite DB + FAISS index (ignored in git)
├── photos/                     # Your images go here
├── converted/                  # HEIC → JPG conversions
├── cache/                      # Model cache (ignored in git)
│
├── backend/                    # Core source code
│   ├── init_db.py              # Initialize the database schema
│   ├── scan.py                 # Scan folders, extract EXIF, reverse-geocode
│   ├── caption.py              # Generate captions using BLIP
│   ├── tagger.py               # Extract keyword tags
│   ├── embedder.py             # Create CLIP vector embeddings
│   ├── build_faiss.py          # Build the FAISS index
│   ├── face_detect.py          # Detect faces + ArcFace embeddings
│   ├── cluster_faces.py        # DBSCAN clustering → person groups
│   ├── face_search.py          # Face query helpers (used by UI)
│   ├── geocode_backfill.py     # Backfill location_name for existing photos
│   ├── ingest.py               # Full pipeline runner (7 stages)
│   ├── semantic_search.py      # CLI semantic search
│   ├── search_cli.py           # CLI keyword search
│   └── add_embeddings_table.py # One-off migration helper
│
├── app.py                      # Streamlit web UI
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

This installs everything: PyTorch, BLIP/CLIP via `transformers`/`sentence-transformers`, `faiss-cpu`, `geopy` (for reverse geocoding), `insightface` + `onnxruntime` + `opencv-python` (for face recognition), `scikit-learn` (for DBSCAN), and `streamlit` (for the UI).

If you’re on CPU-only, PyTorch will auto-install the CPU build. For CUDA:
```bash
pip install "torch>=2.2" torchvision --extra-index-url https://download.pytorch.org/whl/cu121
```

### 3. Initialize the database
```bash
python backend/init_db.py
```
Creates `data/tagle.sqlite` with the `photos`, `embeddings`, `faces`, and `people` tables. Safe to run on an existing DB — migrations are additive.

---

## 📸 Add Your Photos

Place any number of images into:
```
tagle/photos/
```
Supported formats: **JPG / JPEG, PNG, WEBP, TIFF, BMP, HEIC/HEIF** (HEIC is auto-converted to JPG in `converted/`).

---

## 🧠 Run the Full Pipeline

```bash
python backend/ingest.py photos
```

This runs all 7 stages sequentially — each is incremental, so re-running only processes new/unprocessed data:

| Stage | Script | What it does |
|------:|--------|--------------|
| 1/7 | `scan.py` | Walks folders, hashes files, extracts EXIF, reverse-geocodes GPS → `location_name` |
| 2/7 | `caption.py` | Generates natural-language captions with BLIP |
| 3/7 | `tagger.py` | Extracts keyword tags from captions (NLTK) |
| 4/7 | `embedder.py` | Creates 512-d CLIP embeddings per photo |
| 5/7 | `build_faiss.py` | Builds a FAISS L2 index from embeddings |
| 6/7 | `face_detect.py` | Detects faces + ArcFace embeddings via InsightFace |
| 7/7 | `cluster_faces.py` | Clusters face embeddings with DBSCAN into person groups |

> **Note:** Reverse geocoding uses Nominatim and respects its 1 req/sec rate limit, so the scan stage takes ~1 s per GPS-tagged photo the first time.

---

## 🗺️ Backfill Location Names (for existing DBs)

If you already have photos in the DB that predate reverse geocoding:
```bash
python backend/geocode_backfill.py
```
Geocodes every photo with GPS that doesn't yet have a `location_name`. One-time operation.

---

## 🔍 CLI Search

### Keyword search (matches captions, tags, and location)
```bash
python backend/search_cli.py beach
python backend/search_cli.py family sunset
python backend/search_cli.py "brooklyn bridge"
```

### Semantic search (CLIP + FAISS)
```bash
python backend/semantic_search.py "dog on the beach"
python backend/semantic_search.py "sunset mountains" 20
```

Example output:
```text
📸 photos/IMG_1123.jpg
    caption: A dog running along the beach at sunset.
    tags: dog,running,beach,sunset
```

---

## 🖥️ Streamlit Web UI

Launch the app:
```bash
streamlit run app.py
```

The UI provides:

- **Three search modes** in the sidebar:
  - **Semantic (CLIP)** — nearest-neighbour vector search
  - **Keyword (caption + tags + location)** — SQL `LIKE` search
  - **Combined (Rank Fusion)** — merges both result lists using Reciprocal Rank Fusion so photos ranked highly by either signal rise to the top
- **Filters** — year range, latitude/longitude bounding box, and **person** (see below)
- **Manage people** expander — assign names to each face cluster; thumbnails are cropped to the detected face region for easy identification
- **Result cards** — show caption, tags, date, GPS, and a `👤 Alice, Bob` badge when named persons are detected

---

## 👤 Person Search

1. Run `python backend/face_detect.py` (or the full ingest) to detect faces in all photos.
2. Run `python backend/cluster_faces.py` to group similar faces into clusters.
3. Open the UI, expand **Manage people**, and name each cluster once (e.g. "Alice", "Dad").
4. Enable **Filter by person** in the sidebar and choose a name. The filter composes with keyword, semantic, and combined-rank search — e.g. *"Alice at the beach"* returns photos containing Alice **and** semantically matching a beach scene.

Tuning knobs for clustering (edit in `backend/cluster_faces.py` or pass as CLI flags):
```bash
python backend/cluster_faces.py --eps 0.4 --min-samples 3
```
- Lower `--eps` → stricter similarity (fewer false merges, more splits)
- Lower `--min-samples` → fewer faces dropped as "noise"

---

## 🔀 Combined Rank Fusion

The Combined search mode doesn't just intersect results — it uses **Reciprocal Rank Fusion**:

```
score(photo) = Σ 1 / (k + rank_i)      where k = 60
```

across the semantic and keyword rankings. Photos that appear high in either list rank well; photos ranked high in **both** dominate the top results. No score normalization needed — RRF works directly on ranks.

---

## 🧭 Design Philosophy

| Principle | |
|-----------|--|
| **Local-first** | No cloud APIs at search time. Only Nominatim (geocoding) touches the network, and only during ingest. |
| **Privacy** | Photos, faces, and embeddings never leave your machine. |
| **Offline AI** | BLIP (captions), CLIP (embeddings), InsightFace (faces) all run locally. |
| **Modular** | Each pipeline stage is a standalone script; run any stage independently. |
| **Scalable** | SQLite + FAISS handle tens of thousands of photos on commodity hardware. |
| **Incremental** | Every stage skips already-processed data. |

---

## 🧾 License

MIT License © 2025 — Dhruvil Vasoya

---

## 💬 Credits

- Salesforce **BLIP** — image captioning
- **OpenCLIP / SentenceTransformers** — image/text embeddings
- **FAISS** (Meta AI) — vector search
- **InsightFace** — face detection + ArcFace embeddings
- **scikit-learn** — DBSCAN clustering
- **Nominatim / OpenStreetMap** — reverse geocoding
- **Streamlit** — web UI
- **SQLite**, **Pillow**, **ONNX Runtime**, **OpenCV**

---

## ✨ Why "Tagle"?

Tagle = "Tag" + "Google" (in spirit) —
A local AI memory assistant that helps you rediscover your photos anytime, without ever leaving your device.

---

## 🔗 Get Started

```bash
# First time only
pip install -r requirements.txt
python backend/init_db.py

# Any time you add photos:
python backend/ingest.py photos

# Search from the CLI:
python backend/semantic_search.py "dog on the beach"

# Or launch the UI:
streamlit run app.py
```

Tagle — your memories, retrieved with intelligence and privacy.
