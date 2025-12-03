import subprocess
import sys
import os

def run_script(script, *args):
    """
    Utility helper to run another backend script.
    Always assumes you're running from project root (where backend/ lives).
    """
    cmd = [sys.executable, os.path.join("backend", script)] + list(args)
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)


if __name__ == "__main__":

    # Default photo directory
    photos_dir = sys.argv[1] if len(sys.argv) > 1 else "photos"

    # Simple sanity check
    if not os.path.isdir(photos_dir):
        print(f"Photos directory not found: {photos_dir}")
        sys.exit(1)

    print("========================================")
    print("  T A G L E   -   Full Ingest Pipeline  ")
    print("  Phases: Scan → Caption → Tag → Embed → Index")
    print("========================================")
    print(f"Photos directory: {photos_dir}\n")

    # Phase 1
    print("[1/5] Scanning photos...")
    run_script("scan.py", photos_dir)

    print("[2/5] Generating captions...")
    run_script("caption.py")

    print("[3/5] Extracting tags...")
    run_script("tagger.py")

    # Phase 2
    print("[4/5] Creating CLIP embeddings...")
    run_script("embedder.py")

    print("[5/5] Building FAISS index...")
    run_script("build_faiss.py")

    print("\nTagle full pipeline complete.")
    print("   - Phase 1: scan + captions + tags")
    print("   - Phase 2: embeddings + FAISS index\n")
    print("You can now run semantic search, e.g.:")
    print('  python backend/semantic_search.py "dog on the beach"  ')