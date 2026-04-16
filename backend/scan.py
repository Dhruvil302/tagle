import os, hashlib, sqlite3, time
from PIL import Image, ExifTags
from tqdm import tqdm

# --- Reverse geocoding setup ---
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
    _geolocator = Nominatim(user_agent="tagle-photo-organizer", timeout=5)
    GEOCODE_ENABLED = True
except ImportError:
    print("Geocoding not available. Run: pip install geopy")
    GEOCODE_ENABLED = False

# --- Try to add HEIC/HEIF support ---
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_ENABLED = True
except ImportError:
    print("HEIC support not found. Run: pip install pillow-heif")
    HEIC_ENABLED = False

DB = "data/tagle.sqlite"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp", ".heic", ".heif"}
CONVERT_DIR = "converted"  # change to None to save next to original


# --- Helpers ---
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_exif(path):
    exif = {}
    try:
        img = Image.open(path)
        exif_raw = img._getexif()
        if exif_raw:
            for k, v in exif_raw.items():
                tag = ExifTags.TAGS.get(k, k)
                exif[tag] = v
        exif["width"], exif["height"] = img.size
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return exif


def reverse_geocode(lat, lon):
    """Convert GPS coordinates to a human-readable location string via Nominatim."""
    if not GEOCODE_ENABLED or lat is None or lon is None:
        return None
    try:
        location = _geolocator.reverse(f"{lat}, {lon}", language="en", zoom=18)
        if location and location.address:
            return location.address
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding failed for ({lat}, {lon}): {e}")
    except Exception as e:
        print(f"Geocoding error for ({lat}, {lon}): {e}")
    return None


def save_record(path, h, exif):
    con = sqlite3.connect(DB)
    cur = con.cursor()

    gps_lat = (
        float(exif.get('GPSInfo').get(2)[0]) + (exif.get('GPSInfo').get(2)[1] / 60) + (exif.get('GPSInfo').get(2)[2] / 3600)
        if exif.get('GPSInfo') else None
    )
    gps_lon = (
        float(exif.get('GPSInfo').get(4)[0]) + (exif.get('GPSInfo').get(4)[1] / 60) + (exif.get('GPSInfo').get(4)[2] / 3600)
        if exif.get('GPSInfo') else None
    )

    location_name = reverse_geocode(gps_lat, gps_lon)
    if location_name:
        time.sleep(1)  # Nominatim rate limit: 1 request/second

    cur.execute("""
    INSERT OR IGNORE INTO photos(file_path,file_hash,width,height,date_taken,camera_make,camera_model,gps_lat,gps_lon,location_name)
    VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (
        path,
        h,
        exif.get("width"),
        exif.get("height"),
        str(exif.get("DateTimeOriginal") or ""),
        str(exif.get("Make") or ""),
        str(exif.get("Model") or ""),
        gps_lat,
        gps_lon,
        location_name,
    ))
    con.commit()
    con.close()


def convert_heic_to_jpg(path):
    """
    Converts a HEIC file to JPG and returns the new path.
    """
    if not HEIC_ENABLED:
        return None

    base = os.path.splitext(os.path.basename(path))[0]
    out_dir = CONVERT_DIR if CONVERT_DIR else os.path.dirname(path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{base}.jpg")

    if os.path.exists(out_path):
        return out_path  # skip if already converted

    try:
        img1 = Image.open(path)
        img = img1.convert("RGB")
        img.save(out_path, "JPEG", quality=95, exif=img1.info["exif"])
        return out_path
    except Exception as e:
        print(f"Failed to convert {path}: {e}")
        return None


def scan(root="photos"):
    files = []
    for dp, _, fn in os.walk(root):
        for f in fn:
            ext = os.path.splitext(f)[1].lower()
            if ext in IMG_EXT:
                files.append(os.path.join(dp, f))

    for p in tqdm(files, desc="Scanning"):
        ext = os.path.splitext(p)[1].lower()

        # Convert HEIC/HEIF
        if ext in {".heic", ".heif"}:
            if not HEIC_ENABLED:
                print(f"Skipping HEIC (support not installed): {p}")
                continue
            converted = convert_heic_to_jpg(p)
            if not converted:
                continue
            p = converted  # use the converted JPG for DB record

        save_record(p, md5(p), read_exif(p))


if __name__ == "__main__":
    import sys
    scan(sys.argv[1] if len(sys.argv) > 1 else "photos")
    print("Scan complete")