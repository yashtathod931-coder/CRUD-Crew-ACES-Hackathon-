from datetime import datetime, timezone
from propagate.propagate import propagate_tles
from ingest.spaceweather import get_latest_spaceweather
from screening.screening import screen_conjunctions

def test_offline():
    print("Running offline sanity check...")
    sw = get_latest_spaceweather("quiet")
    assert sw["kp"] == 1.0
    
    sats = [
        {
            "name": "ISS (ZARYA)",
            "line1": "1 25544U 98067A   26284.50000000  .00016717  00000-0  30275-3 0  9993",
            "line2": "2 25544  51.6416 247.4627 0006703 130.5360 329.6998 15.50000000456184",
            "norad_id": "25544"
        },
        {
            "name": "IRIDIUM 33 DEB",
            "line1": "1 33775U 09010C   26284.50000000  .00001000  00000-0  10000-3 0  9991",
            "line2": "2 33775  86.4000 120.0000 0010000  50.0000 310.0000 14.39000000123456",
            "norad_id": "33775"
        }
    ]
    
    start_time = datetime.now(timezone.utc)
    positions, velocities, times = propagate_tles(sats, start_time, duration_hours=1, step_seconds=60)
    assert positions.shape[0] > 0
    assert positions.shape[1] == 2
    
    conjunctions = screen_conjunctions(positions, velocities, times, sats, threshold_km=1000.0)
    print(f"OK: tests_offline passed successfully! Found {len(conjunctions)} conjunctions.")

if __name__ == "__main__":
    test_offline()
