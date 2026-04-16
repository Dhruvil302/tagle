"""
Backfill location_name for existing photos that have GPS but no location yet.
Usage: python backend/geocode_backfill.py
"""

import sqlite3
import time

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from tqdm import tqdm

DB = "data/tagle.sqlite"
geolocator = Nominatim(user_agent="tagle-photo-organizer", timeout=5)


def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse(f"{lat}, {lon}", language="en", zoom=18)
        if location and location.address:
            return location.address
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"  Timeout/unavailable for ({lat}, {lon}): {e}")
    except Exception as e:
        print(f"  Error for ({lat}, {lon}): {e}")
    return None


def run():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        """
        SELECT id, gps_lat, gps_lon FROM photos
        WHERE gps_lat IS NOT NULL AND gps_lon IS NOT NULL
          AND (location_name IS NULL OR location_name = '')
        """
    )
    rows = cur.fetchall()

    if not rows:
        print("All photos with GPS already have location names.")
        return

    print(f"Geocoding {len(rows)} photos (1 req/sec due to Nominatim rate limit)...")

    updated = 0
    for pid, lat, lon in tqdm(rows, desc="Geocoding"):
        name = reverse_geocode(lat, lon)
        if name:
            cur.execute("UPDATE photos SET location_name = ? WHERE id = ?", (name, pid))
            updated += 1
        time.sleep(1)  # respect Nominatim rate limit

    con.commit()
    con.close()
    print(f"Done. Updated {updated}/{len(rows)} photos with location names.")


if __name__ == "__main__":
    run()
