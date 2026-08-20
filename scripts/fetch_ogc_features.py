"""Fetch all features within a bbox from an EA/NE OGC API - Features collection,
paginating until numberReturned is exhausted, and save as a single GeoJSON file."""
import sys
import json
import time
import urllib.request

BBOX = "-3.0558,53.6647,-2.0358,54.2589"  # Ribble Management Catchment envelope
LIMIT = 1000


def fetch(base_url, collection, out_path):
    all_features = []
    start_index = 0
    while True:
        url = (
            f"{base_url}/collections/{collection}/items"
            f"?bbox={BBOX}&f=json&limit={LIMIT}&startIndex={start_index}"
        )
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.load(resp)
        features = data.get("features", [])
        all_features.extend(features)
        returned = data.get("numberReturned", len(features))
        matched = data.get("numberMatched")
        print(f"  startIndex={start_index} returned={returned} matched={matched} total_so_far={len(all_features)}")
        if returned < LIMIT:
            break
        start_index += LIMIT
        time.sleep(0.3)

    fc = {"type": "FeatureCollection", "features": all_features}
    with open(out_path, "w") as f:
        json.dump(fc, f)
    print(f"Saved {len(all_features)} features to {out_path}")


if __name__ == "__main__":
    base_url, collection, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    fetch(base_url, collection, out_path)
