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
  <img src="https://img.shields.io/badge/status-Phase%201-lightgrey" />
</p>


# 🏷️ Tagle
> **Your photos, intelligently organized — all local.**

Tagle is a local-first photo intelligence tool.  
It scans your photos, extracts EXIF metadata, generates AI captions, builds searchable tags, and now (Phase 2) performs **semantic search** using CLIP embeddings + FAISS — all offline.
---

## 🚀 Features

- 🖼️ **Local photo processing** — never uploads your photos  
- 🧠 **AI-generated captions** using BLIP (runs offline)  
- 🏷️ **Automatic keyword tagging** (lightweight NLP)  
- 📅 **EXIF extraction** — date, camera, GPS (when available)  
- 🔍 **Fast keyword search** via CLI
- ✨ **CLIP semantic search (Phase 2)** via CLI
- ⚡ **FAISS vector index** for fast retrieval
- 💾 **SQLite database** (simple, portable, scalable)  
- 🔁 **Incremental updates** — only processes new files  

---

## 📦 Project Structure
```markdown
tagle/
├── data/                 # SQLite DB + FAISS index (ignored in git)
├── photos/               # Your images go here
├── cache/                # Model cache (ignored in git)
│
├── backend/                # Core source code
│   ├── init_db.py        # Initialize the database
│   ├── scan.py           # Scan folders & extract EXIF
│   ├── caption.py        # Generate captions using BLIP
│   ├── tagger.py         # Extract keyword tags
│   ├── ingest.py         # Full pipeline runner
│   ├── embedder.py       # Create Vector Embeddings 
│   ├── build_faiss.py.   # Create Faiss Index
│   ├── semantic_search.py# Search semantically
│   └── search_cli.py     # Simple keyword search
│
├── converted
├── requirements.txt
└── README.md
---
```
## ⚙️ Installation

### 1. Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```
2. Install dependencies
```bash
pip install "torch>=2.2" torchvision --extra-index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.44.2 pillow piexif tqdm pandas nltk sqlite-utils
```
If you’re on CPU-only, just run:
```bash
pip install torch torchvision
```
and PyTorch will install the CPU version automatically.

⸻

Initialize the Database
```bash
python backend/init_db.py
```
This creates:

data/tagle.sqlite


⸻

📸 Add Your Photos

Place any number of images into:

tagle/photos/

Supported formats:
	•	JPG / JPEG
	•	PNG
	•	WEBP
	•	TIFF
	•	BMP
  •	HEIC

⸻

🧠 Run Tagle (Full Pipeline)
```bash
python backend/ingest.py photos
```
This performs:
	1.	Folder scan
	2.	EXIF extraction
	3.	Caption generation (local BLIP model)
	4.	Keyword tagging
	5.	DB updates

You can run it anytime — it only processes new/unprocessed photos.

⸻

🔍 Search Your Photos
```bash
python backend/search_cli.py beach
python backend/search_cli.py family sunset
python backend/search_cli.py dog 2018
```
Example output:

01. photos/beach_trip_2020.jpg
    date: 2020-06-18
    caption: A family walking on the beach during sunset.
    tags: family,walking,beach,sunset,trip


✨ Phase 2 — Semantic Search (CLIP + FAISS)

2.1 Generate CLIP embeddings
```bash
python backend/embedder.py
```

2.2 Build FAISS index
```bash
python backend/build_faiss.py
```

You should now have:
```text
data/tagle.index
data/tagle_ids.npy
```

2.3 Run semantic search
```bash
python backend/semantic_search.py "dog on the beach"
```
or specify top K:
```bash
python backend/semantic_search.py "sunset mountains" 20
```

Example output:
```text
📸 photos/IMG_1123.jpg
    caption: A dog running along the beach at sunset.
    tags: dog,running,beach,sunset
```

⸻

🧭 Design Philosophy

Principle
Local-first - No cloud APIs or uploads
Privacy - Photos never leave your machine
Offline AI - BLIP + CLIP models run locally
Modular - Each phase is independent
Scalable - Supports thousands+ photos
Extensible -Ready for UI, faces, filtering

⸻

🧾 License

MIT License © 2025 — Dhruvil Vasoya

⸻

💬 Credits
	•	Salesforce BLIP
	•	OpenCLIP / SentenceTransformers
	•	FAISS (Meta AI)
	•	SQLite
	•	Pillow
	•	Community inspiration

⸻

✨ Why “Tagle”?

Tagle = “Tag” + “Google” (in spirit) —
A local AI memory assistant that helps you rediscover your photos anytime, without ever leaving your device.

⸻

🔗 Get Started
```bash
# First time only (if not done yet)
python backend/init_db.py

# Then, any time you add / change photos:
python backend/ingest.py photos

python backend/semantic_search.py "dog on the beach"
```
Tagle — your memories, retrieved with intelligence — and privacy.