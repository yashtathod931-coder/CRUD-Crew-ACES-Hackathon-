import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.spatial import cKDTree
from scipy.optimize import minimize_scalar
from scipy.interpolate import CubicHermiteSpline


def screen_conjunctions(positions, velocities, times, sats, threshold_km=10.0):
    """Find close approaches and refine TCA with position/velocity Hermite arcs.

    ``pc`` is intentionally not produced: TLEs do not include the covariance
    needed for a defensible collision probability.
    """
    num_steps, num_sats, _ = positions.shape
    if num_steps < 2 or num_sats < 2 or len(times) != num_steps:
        return []

    step_seconds = (times[1] - times[0]).total_seconds()
    if step_seconds <= 0:
        raise ValueError("Propagation times must be strictly increasing")

    # For each pair, retain only intervals adjacent to a sampled close approach.
    # The margin covers the maximum time to the nearest sample (half a step).
    search_radius = threshold_km + 8.0 * step_seconds
    candidate_intervals = {}

    for t_idx in range(num_steps):
        p = positions[t_idx]
        valid = np.flatnonzero(np.isfinite(p).all(axis=1) &
                               np.isfinite(velocities[t_idx]).all(axis=1))
        if len(valid) < 2:
            continue
        for a, b in cKDTree(p[valid]).query_pairs(search_radius):
            pair = (int(valid[a]), int(valid[b]))
            intervals = candidate_intervals.setdefault(pair, set())
            if t_idx > 0:
                intervals.add(t_idx - 1)
            if t_idx < num_steps - 1:
                intervals.add(t_idx)

    results = []
    for (sat_i, sat_j), intervals in candidate_intervals.items():
        relative_pos = positions[:, sat_i] - positions[:, sat_j]
        relative_vel = velocities[:, sat_i] - velocities[:, sat_j]
        valid = np.isfinite(relative_pos).all(axis=1) & np.isfinite(relative_vel).all(axis=1)
        best = None
        best_speed = None
        for idx in intervals:
            if not (valid[idx] and valid[idx + 1]):
                continue
            t0 = times[idx].timestamp()
            t1 = times[idx + 1].timestamp()
            duration = t1 - t0
            if duration <= 0:
                continue
            # Linear relative motion gives a fast TCA seed. Refine only intervals
            # whose seed can plausibly meet the requested screening threshold.
            r0 = relative_pos[idx].astype(np.float64)
            dr = relative_pos[idx + 1].astype(np.float64) - r0
            fraction = float(np.clip(-np.dot(r0, dr) / max(np.dot(dr, dr), 1e-20), 0.0, 1.0))
            linear_miss = float(np.linalg.norm(r0 + fraction * dr))
            if linear_miss > threshold_km + 50.0:
                continue
            arc = CubicHermiteSpline(
                [0.0, duration], relative_pos[idx:idx + 2],
                relative_vel[idx:idx + 2], axis=0
            )
            opt = minimize_scalar(lambda t: float(np.dot(arc(t), arc(t))),
                                  bounds=(0.0, duration), method="bounded",
                                  options={"xatol": 1e-3})
            options = [(0.0, float(np.linalg.norm(arc(0.0)))),
                       (duration, float(np.linalg.norm(arc(duration)))),
                       (opt.x, float(np.sqrt(max(0.0, opt.fun))))]
            dt, distance = min(options, key=lambda value: value[1])
            if best is None or distance < best[1]:
                best = (t0 + dt, float(distance))
                best_speed = float(np.linalg.norm(arc(dt, 1)))
        if best is None or best[1] > threshold_km:
            continue
        tca_epoch, miss_distance = best
        results.append({
            "sat_i": sats[sat_i]["name"], "sat_j": sats[sat_j]["name"],
            "sat_i_idx": sat_i, "sat_j_idx": sat_j,
            "tca_time": datetime.fromtimestamp(tca_epoch, tz=timezone.utc),
            "miss_distance_km": miss_distance,
            "relative_speed_km_s": best_speed,
        })
    return sorted(results, key=lambda item: item["tca_time"])


def closest_approach_for_pair(positions, velocities, times, sat_i, sat_j):
    """Return sampled range and a Hermite-refined TCA for one object pair."""
    relative_pos = (positions[:, sat_i] - positions[:, sat_j]).astype(np.float64)
    relative_vel = (velocities[:, sat_i] - velocities[:, sat_j]).astype(np.float64)
    valid = (np.isfinite(relative_pos).all(axis=1) &
             np.isfinite(relative_vel).all(axis=1))
    intervals = np.flatnonzero(valid[:-1] & valid[1:])
    if len(intervals) == 0:
        raise ValueError("The selected objects have no overlapping valid ephemeris points.")

    step = (times[1] - times[0]).total_seconds()
    if step <= 0:
        raise ValueError("Propagation times must be strictly increasing.")
    r0 = relative_pos[intervals]
    dr = relative_pos[intervals + 1] - r0
    fractions = np.clip(-np.einsum("ij,ij->i", r0, dr) /
                        np.maximum(np.einsum("ij,ij->i", dr, dr), 1e-20), 0.0, 1.0)
    linear_misses = np.linalg.norm(r0 + fractions[:, None] * dr, axis=1)
    best_local = int(np.argmin(linear_misses))
    idx = int(intervals[best_local])

    duration = (times[idx + 1] - times[idx]).total_seconds()
    arc = CubicHermiteSpline(
        [0.0, duration], relative_pos[idx:idx + 2],
        relative_vel[idx:idx + 2], axis=0
    )
    opt = minimize_scalar(lambda dt: float(np.dot(arc(dt), arc(dt))),
                          bounds=(0.0, duration), method="bounded",
                          options={"xatol": 1e-3})
    options = [(0.0, float(np.linalg.norm(arc(0.0)))),
               (duration, float(np.linalg.norm(arc(duration)))),
               (opt.x, float(np.sqrt(max(0.0, opt.fun))))]
    dt, miss_distance = min(options, key=lambda item: item[1])
    return {
        "tca_time": times[idx] + timedelta(seconds=dt),
        "miss_distance_km": miss_distance,
        "relative_speed_km_s": float(np.linalg.norm(arc(dt, 1))),
        "sampled_distances_km": np.linalg.norm(relative_pos[valid], axis=1),
        "valid_indices": np.flatnonzero(valid),
    }
