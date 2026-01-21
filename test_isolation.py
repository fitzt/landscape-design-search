import os
import requests
import sys

# Test configuration
LYNCH_ID = 1444
LEAHY_ID = 1294
API_URL = "http://localhost:8000/api"

def test_isolation(slug, allowed_id, blocked_id):
    print(f"\n--- Testing Isolation for PROJECT_SLUG='{slug}' ---")
    
    # 1. Test Search
    print(f"Testing Search...")
    # This test assumes the server is running with the current PROJECT_SLUG
    res = requests.post(f"{API_URL}/search", json={"query": "", "top_k": 100})
    if res.status_code == 200:
        results = res.json().get("results", [])
        slugs = set(r.get("project_slug") for r in results)
        print(f"Search results slugs: {slugs}")
        if any(s != slug for s in slugs if s):
            print(f"FAILURE: Found other projects in search results!")
        else:
            print(f"SUCCESS: Search results are isolated.")
    else:
        print(f"FAILURE: Search request failed with status {res.status_code}")

    # 2. Test Image Details (Blocked ID)
    print(f"Testing Image Details (Blocked ID: {blocked_id})...")
    res = requests.post(f"{API_URL}/images/details", json={"ids": [blocked_id]})
    if res.status_code == 200:
        images = res.json().get("images", [])
        if len(images) > 0:
            print(f"FAILURE: Accessed image details for blocked project!")
        else:
            print(f"SUCCESS: Image details blocked for other project.")
    else:
        print(f"FAILURE: Image details request failed with status {res.status_code}")

    # 3. Test Raw Image (Blocked ID)
    print(f"Testing Raw Image (Blocked ID: {blocked_id})...")
    res = requests.get(f"{API_URL}/image/{blocked_id}/raw")
    if res.status_code == 404 or res.status_code == 403:
        print(f"SUCCESS: Raw image blocked (Status: {res.status_code}).")
    elif res.status_code == 200:
        print(f"FAILURE: Accessed raw image for blocked project!")
    else:
        print(f"WARNING: Raw image returned status {res.status_code}")

if __name__ == "__main__":
    # Note: This script requires the server to be running.
    # It checks against the LATEST server state.
    # To run fully automated, we'd need to start/stop the server with different env vars.
    # For now, we'll use it to verify the CURRENTLY RUNNING server.
    
    # Get current project slug from environment if possible, or expect it to be passed
    current_slug = os.getenv("PROJECT_SLUG")
    if not current_slug:
        print("Error: PROJECT_SLUG environment variable not set. Run with 'PROJECT_SLUG=leahy python3 test_isolation.py'")
        sys.exit(1)
        
    if current_slug == "leahy":
        test_isolation("leahy", LEAHY_ID, LYNCH_ID)
    elif current_slug == "lynch":
        test_isolation("lynch", LYNCH_ID, LEAHY_ID)
    else:
        print(f"Unknown PROJECT_SLUG: {current_slug}")
