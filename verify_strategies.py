from backend.search_strategies.coordinator import StrategyCoordinator
from backend.config import PROJECT_SLUG
import json

def test_search_strategies():
    coordinator = StrategyCoordinator()
    
    print("--- 1. Testing Leahy Consultation Mode ---")
    # Force leahy project
    # Use a query that should match seeded after images
    leahy_results = coordinator.search("yard transformation", project_slug="leahy")
    
    print(f"Results count: {len(leahy_results)}")
    # Find our seeded project in the results
    seeded_project = next((p for p in leahy_results if p['id'] == 'b52cf69f-5b17-45ed-a015-ed8ab8746ce9'), None)
    
    if seeded_project:
        print(f"Seeded Project Found: SUCCESS")
        print(f"Assets breakdown: {len(seeded_project['assets']['after'])} After, {len(seeded_project['assets']['context'])} Context")
        print(f"Hero Image ID: {seeded_project['hero_image']['id']}")
    else:
        print("Seeded Project NOT found in search results (check threshold or indexing)")
    
    print("\n--- 2. Testing Leahy Fallback (Knowledge Engine) ---")
    # Query that is definitely garbage for CLIP
    fallback_results = coordinator.search("asdfasdfasdfqwertytrewq", project_slug="leahy")
    if fallback_results:
        first = fallback_results[0]
        res_type = first.get('type')
        print(f"Result type: {res_type}")
        if res_type == 'fact_card':
            text = first.get('text', '')
            print(f"Text snippet: {text[:50]}...")
            print("Fact Card Fallback: SUCCESS")
        else:
            print(f"Fallback failed, got type: {res_type}")
    
    print("\n--- 3. Testing Lynch Standard Search (Strategy Switching) ---")
    # Use coordinator directly. With my fix, this should switch to StandardSearch
    lynch_results = coordinator.search("patio", project_slug="lynch")
    if lynch_results:
        first = lynch_results[0]
        # Standard search returns list of dicts with image fields, no 'assets'
        is_project = 'assets' in first
        print(f"First result type: {'ProjectContainer' if is_project else 'Atomic'}")
        if not is_project:
            print("Lynch Standard Search: SUCCESS (Strategy Switched)")
            print(f"Result ID: {first.get('id')}")
        else:
            print("Lynch failure: still using Consultation strategy")

if __name__ == "__main__":
    test_search_strategies()
