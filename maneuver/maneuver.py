import numpy as np

def compute_maneuver(m0, isp, available_fuel, miss_distance_km,
                     lead_time_seconds, hard_body_radius_m):
    """Return an idealized impulse estimate to clear a screening distance.

    This is a first-order geometry estimate, not an executable maneuver plan.
    It assumes the impulse is aligned with the miss direction and applied now.
    """
    g0 = 9.80665
    target_miss_km = (hard_body_radius_m + 100.0) / 1000.0
    needed_shift_m = max(0.0, (target_miss_km - miss_distance_km) * 1000.0)
    if needed_shift_m == 0.0:
        dv_mps = 0.0
    elif lead_time_seconds <= 0:
        dv_mps = float("inf")
    else:
        dv_mps = needed_shift_m / lead_time_seconds

    exhaust_velocity = isp * g0
    fuel_used_kg = (float(m0 * (1.0 - np.exp(-dv_mps / exhaust_velocity)))
                    if np.isfinite(dv_mps) and exhaust_velocity > 0 else float("inf"))
    within_fuel = fuel_used_kg <= available_fuel
    return {
        "dv_mps": dv_mps,
        "fuel_used_kg": fuel_used_kg,
        "target_miss_km": target_miss_km,
        "within_fuel": within_fuel,
    }
