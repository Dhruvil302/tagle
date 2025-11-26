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

Tagle automatically scans your photo library, extracts EXIF metadata, generates AI captions, and tags each image — creating a fully searchable, privacy-preserving photo database that runs **entirely offline** on your own machine.

---

## 🚀 Features

- 🖼️ **Local photo processing** — never uploads your photos  
- 🧠 **AI-generated captions** using BLIP (runs offline)  
- 🏷️ **Automatic keyword tagging** (lightweight NLP)  
- 📅 **EXIF extraction** — date, camera, GPS (when available)  
- 🔍 **Fast keyword search** via CLI  
- 💾 **SQLite database** (simple, portable, scalable)  
- 🔁 **Incremental updates** — only processes new files  

---

## 📦 Project Structure

tagle/
├── data/                 # SQLite DB + model cache
├── photos/               # Your images go here
├── cache/                # HuggingFace cache (optional)
│
├── backend/                # Core source code
│   ├── init_db.py        # Initialize the database
│   ├── scan.py           # Scan folders & extract EXIF
│   ├── caption.py        # Generate captions using BLIP
│   ├── tagger.py         # Extract keyword tags
│   ├── ingest.py         # Full pipeline runner
│   └── search_cli.py     # Simple keyword search
│
├── converted
├── requirements.txt
└── README.md
---

## ⚙️ Installation

### 1. Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

2. Install dependencies

pip install "torch>=2.2" torchvision --extra-index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.44.2 pillow piexif tqdm pandas nltk sqlite-utils

If you’re on CPU-only, just run:

pip install torch torchvision

and PyTorch will install the CPU version automatically.

⸻

🧱 Initialize the Database

python backend/init_db.py

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

python backend/ingest.py photos

This performs:
	1.	Folder scan
	2.	EXIF extraction
	3.	Caption generation (local BLIP model)
	4.	Keyword tagging
	5.	DB updates

You can run it anytime — it only processes new/unprocessed photos.

⸻

🔍 Search Your Photos

python backend/search_cli.py beach
python backend/search_cli.py family sunset
python backend/search_cli.py dog 2018

Example output:

01. photos/beach_trip_2020.jpg
    date: 2020-06-18
    caption: A family walking on the beach during sunset.
    tags: family,walking,beach,sunset,trip


⸻

🧭 Design Philosophy

Principle	Implementation
Privacy-first	100% local, never uploads images
Simple & modular	Each step is a separate script
Scalable	SQLite + batch processing
Incremental	Hash-based duplicate detection
Extensible	Easy to add embeddings, UI, faces, etc.


⸻

🧾 License

MIT License © 2025 — Dhruvil Vasoya

⸻

💬 Credits
	•	Salesforce BLIP model
	•	Hugging Face Transformers
	•	Pillow / SQLite / Piexif
	•	Community multimodal AI inspiration

⸻

✨ Why “Tagle”?

Tagle = “Tag” + “Google” (in spirit) —
A local AI memory assistant that helps you rediscover your photos anytime, without ever leaving your device.

⸻

🔗 Get Started

python backend/ingest.py photos
python backend/search_cli.py "your search terms"

Tagle — your memories, retrieved with intelligence — and privacy.
