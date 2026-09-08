
"""
tests/test_scan_endpoint.py
 
Hits the live /api/scan route with a real sample label image and
prints the response. Run this AFTER starting the FastAPI server
(uvicorn main:app --reload) and AFTER the real function names in
scan.py's imports/calls are wired up.
 
Usage:
    python tests/test_scan_endpoint.py path/to/sample_labels/some_label.jpg
    python tests/test_scan_endpoint.py path/to/sample_labels/some_label.jpg --debug
"""
 
import sys
import json
import argparse
import requests
 
DEFAULT_URL = "http://127.0.0.1:8000/api/scan"
 
 
def run_test(image_path: str, url: str, debug: bool):
    with open(image_path, "rb") as f:
        files = {"file": (image_path, f, "image/jpeg")}
        params = {"debug": "true"} if debug else {}
        resp = requests.post(url, files=files, params=params)
 
    print(f"Status: {resp.status_code}")
 
    try:
        data = resp.json()
    except ValueError:
        print("Response was not JSON:")
        print(resp.text)
        return
 
    print(json.dumps(data, indent=2))
 
    if resp.status_code != 200:
        print("\n--- FAILED ---")
        sys.exit(1)
 
    if "report" not in data:
        print("\n--- WARNING: no 'report' key in response ---")
 
    print("\n--- OK ---")
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the /api/scan endpoint")
    parser.add_argument("image_path", help="Path to a sample label image or PDF")
    parser.add_argument("--url", default=DEFAULT_URL, help="Endpoint URL")
    parser.add_argument("--debug", action="store_true", help="Request debug output too")
    args = parser.parse_args()
 
    run_test(args.image_path, args.url, args.debug)