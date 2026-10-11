import os
import time
import requests
from sgp4.api import Satrec

CACHE_DIR = os.path.join("data", "cache")
GROUPS = {
    "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
    "cosmos-2251-debris": "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=tle",
    "iridium-33-debris": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle",
    "fengyun-1c-debris": "https://celestrak.org/NORAD/elements/gp.php?GROUP=fengyun-1c-debris&FORMAT=tle",
    "cosmos-1408-debris": "https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-1408-debris&FORMAT=tle"
}

EARTH_RADIUS_KM = 6378.137

def fetch_tles(max_objects=None, refresh=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    all_sats = []
    seen_norad = set()
    parse_count = 0
    rejected_count = 0
    data_sources = []

    for group_name, url in GROUPS.items():
        cache_file = os.path.join(CACHE_DIR, f"{group_name}.tle")
        tles = []

        if not refresh and os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 7200:
                with open(cache_file, "r", encoding="utf-8", errors="ignore") as f:
                    tles = f.readlines()
        
        if not tles:
            try:
                print(f"[CelesTrak] Downloading group '{group_name}'...")
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    text = resp.text
                    if "1 " in text and "2 " in text and _parse_tle_lines(text.splitlines()):
                        with open(cache_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        tles = text.splitlines()
                    else:
                        print(f"[CelesTrak] Empty or unrecognized TLE response for '{group_name}'.")
                else:
                    print(f"[CelesTrak] HTTP {resp.status_code} for '{group_name}'.")
            except Exception as e:
                print(f"[CelesTrak] Failed to download '{group_name}': {e}")

            if not tles and os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8", errors="ignore") as f:
                    tles = f.readlines()
                data_sources.append(f"{group_name}:cache")
            elif tles:
                data_sources.append(f"{group_name}:live/cache")

        parsed = _parse_tle_lines(tles)
        parse_count += len(parsed)
        for sat in parsed:
            norad = sat["norad_id"]
            if norad in seen_norad:
                continue
            if is_leo(sat):
                seen_norad.add(norad)
                sat["tle_age_days"] = tle_age_days(sat)
                all_sats.append(sat)
                if max_objects and len(all_sats) >= max_objects:
                    break
            else:
                rejected_count += 1
        if max_objects and len(all_sats) >= max_objects:
            break

    print(f"[CelesTrak] Loaded {len(all_sats)} unique LEO objects.")
    if not all_sats:
        raise RuntimeError(
            "No usable LEO TLEs. "
            f"Parsed {parse_count} records and rejected {rejected_count}; "
            f"data sources: {', '.join(data_sources) if data_sources else 'none (download failed and no cache was readable)'}."
        )
    return all_sats

def _parse_tle_lines(lines):
    clean_lines = [l.strip() for l in lines if l.strip()]
    sats = []
    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        if line.startswith("1 ") and i + 1 < len(clean_lines) and clean_lines[i+1].startswith("2 "):
            name = f"SAT-{clean_lines[i][2:7].strip()}"
            l1 = clean_lines[i]
            l2 = clean_lines[i+1]
            sats.append({"name": name, "line1": l1, "line2": l2, "norad_id": l1[2:7].strip()})
            i += 2
        elif i + 2 < len(clean_lines) and clean_lines[i+1].startswith("1 ") and clean_lines[i+2].startswith("2 "):
            name = line
            l1 = clean_lines[i+1]
            l2 = clean_lines[i+2]
            sats.append({"name": name, "line1": l1, "line2": l2, "norad_id": l1[2:7].strip()})
            i += 3
        else:
            i += 1
    return sats

def is_leo(sat):
    try:
        satellite = Satrec.twoline2rv(sat["line1"], sat["line2"])
        if satellite.error:
            return False
        # TLE mean motion is in revolutions/day; convert to radians/second.
        mean_motion_rev_day = float(sat["line2"][52:63])
        eccentricity = float("0." + sat["line2"][26:33].strip())
        if mean_motion_rev_day <= 0:
            return False
        mean_motion_rad_s = mean_motion_rev_day * 2.0 * 3.141592653589793 / 86400.0
        semi_major_axis_km = (398600.4418 / mean_motion_rad_s**2) ** (1.0 / 3.0)
        perigee_km = semi_major_axis_km * (1.0 - eccentricity) - EARTH_RADIUS_KM
        return -100.0 <= perigee_km <= 2000.0
    except Exception:
        return False

def tle_age_days(sat, now=None):
    """Age of the TLE epoch in days, using its two-digit year convention."""
    from datetime import datetime, timezone
    line1 = sat["line1"]
    year_short = int(line1[18:20])
    year = 1900 + year_short if year_short >= 57 else 2000 + year_short
    day_of_year = float(line1[20:32])
    from datetime import timedelta
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - epoch).total_seconds() / 86400.0)
