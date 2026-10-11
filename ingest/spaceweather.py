import os
import json
import requests

CACHE_DIR = os.path.join("data", "cache")
KP_CACHE_FILE = os.path.join(CACHE_DIR, "kp_index.json")
F107_CACHE_FILE = os.path.join(CACHE_DIR, "f107_index.json")

QUIET = {"kp": 1.0, "f107": 70.0, "density_uncertainty": 0.10}
STORM = {"kp": 7.0, "f107": 180.0, "density_uncertainty": 0.50}

def get_latest_spaceweather(mode="live", refresh=True):
    if mode == "quiet":
        return {**QUIET, "source": "quiet scenario"}
    if mode == "storm":
        return {**STORM, "source": "storm scenario"}
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    kp, kp_source, kp_time = fetch_kp(refresh=refresh, with_metadata=True)
    f107, f107_source, f107_time = fetch_f107(refresh=refresh, with_metadata=True)
    uncertainty = 0.10 + (max(0.0, min(kp, 9.0) - 1.0) / 8.0) * 0.40
    return {
        "kp": kp,
        "f107": f107,
        "density_uncertainty": uncertainty,
        "source": f"Kp {kp_source}; F10.7 {f107_source}",
        "observed_at": {"kp": kp_time, "f107": f107_time},
    }

def fetch_kp(refresh=False, with_metadata=False):
    url = "https://services.swpc.noaa.gov/json/geospace/geospace_k_index.json"
    try:
      if refresh:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            with open(KP_CACHE_FILE, "w") as f:
                json.dump(data, f)
            parsed = (_parse_kp(data), "live NOAA", _parse_time(data[-1]))
            return parsed if with_metadata else parsed[0]
    except Exception:
        pass
    if os.path.exists(KP_CACHE_FILE):
        try:
            with open(KP_CACHE_FILE, "r") as f:
                data = json.load(f)
            parsed = (_parse_kp(data), "cached NOAA", _parse_time(data[-1]))
            return parsed if with_metadata else parsed[0]
        except Exception:
            pass
    parsed = (QUIET["kp"], "quiet fallback", None)
    return parsed if with_metadata else parsed[0]

def _parse_kp(data):
    if not data:
        return QUIET["kp"]
    latest = data[-1]
    if isinstance(latest, dict):
        for key in ["kp", "k_index", "value"]:
            if key in latest:
                return float(latest[key])
    elif isinstance(latest, (list, tuple)) and len(latest) >= 2:
        return float(latest[1])
    return QUIET["kp"]

def fetch_f107(refresh=False, with_metadata=False):
    url = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"
    try:
      if refresh:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            with open(F107_CACHE_FILE, "w") as f:
                json.dump(data, f)
            parsed = (_parse_f107(data), "live NOAA", _parse_time(data[-1]))
            return parsed if with_metadata else parsed[0]
    except Exception:
        pass
    if os.path.exists(F107_CACHE_FILE):
        try:
            with open(F107_CACHE_FILE, "r") as f:
                data = json.load(f)
            parsed = (_parse_f107(data), "cached NOAA", _parse_time(data[-1]))
            return parsed if with_metadata else parsed[0]
        except Exception:
            pass
    parsed = (QUIET["f107"], "quiet fallback", None)
    return parsed if with_metadata else parsed[0]

def _parse_time(record):
    if isinstance(record, dict):
        return next((str(record[key]) for key in ("time_tag", "time", "date") if record.get(key)), None)
    return None

def _parse_f107(data):
    if not data:
        return QUIET["f107"]
    latest = data[-1]
    if isinstance(latest, dict):
        for key in ["f10.7", "flux", "smoothed_flux"]:
            if key in latest and latest[key] is not None:
                return float(latest[key])
    return QUIET["f107"]
