import argparse
from datetime import datetime, timezone
from ingest.celestrak import fetch_tles
from ingest.spaceweather import get_latest_spaceweather
from propagate.propagate import propagate_tles
from screening.screening import screen_conjunctions

def main():
    parser = argparse.ArgumentParser(description="Run Phase 1 Conjunction Analysis")
    parser.add_argument("--max-objects", type=int, default=200, help="Max objects to load")
    parser.add_argument("--cached", action="store_true", help="Use cached data without refreshing")
    args = parser.parse_args()
    
    print("=== ACES Hackathon: Conjunction Phase 1 ===")
    sw = get_latest_spaceweather("live", refresh=not args.cached)
    print(f"Space Weather: Kp={sw['kp']}, F10.7={sw['f107']} ({sw['source']})")
    
    sats = fetch_tles(max_objects=args.max_objects, refresh=not args.cached)
    if not sats:
        print("No satellites loaded!")
        return
        
    start_time = datetime.now(timezone.utc)
    positions, velocities, times = propagate_tles(sats, start_time, duration_hours=24, step_seconds=60)
    
    conjunctions = screen_conjunctions(positions, velocities, times, sats, threshold_km=50.0)
    print(f"Found {len(conjunctions)} potential conjunctions within 50 km threshold.")
    for c in conjunctions[:5]:
        print(f"  - {c['sat_i']} vs {c['sat_j']} at {c['tca_time']} | Miss: {c['miss_distance_km']:.3f} km | Relative speed: {c['relative_speed_km_s']:.3f} km/s")

if __name__ == "__main__":
    main()
