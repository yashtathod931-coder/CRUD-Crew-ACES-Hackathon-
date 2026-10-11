import numpy as np
from datetime import datetime, timedelta
from sgp4.api import Satrec, jday
import time

def propagate_tles(sats, start_time: datetime, duration_hours=72, step_seconds=30):
    num_steps = int((duration_hours * 3600) / step_seconds) + 1
    num_sats = len(sats)
    
    positions = np.full((num_steps, num_sats, 3), np.nan, dtype=np.float32)
    velocities = np.full((num_steps, num_sats, 3), np.nan, dtype=np.float32)
    
    satrecs = []
    for sat in sats:
        try:
            satrecs.append(Satrec.twoline2rv(sat["line1"], sat["line2"]))
        except Exception:
            satrecs.append(None)
            
    t0 = time.time()
    times = [start_time + timedelta(seconds=i * step_seconds) for i in range(num_steps)]
    
    jd_frs = []
    for t in times:
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
        jd_frs.append((jd, fr))
        
    for s_idx, satrec in enumerate(satrecs):
        if satrec is None:
            continue
        for t_idx, (jd, fr) in enumerate(jd_frs):
            e, r, v = satrec.sgp4(jd, fr)
            if e == 0:
                positions[t_idx, s_idx, 0] = r[0]
                positions[t_idx, s_idx, 1] = r[1]
                positions[t_idx, s_idx, 2] = r[2]
                velocities[t_idx, s_idx, 0] = v[0]
                velocities[t_idx, s_idx, 1] = v[1]
                velocities[t_idx, s_idx, 2] = v[2]
                
    elapsed = time.time() - t0
    print(f"[Propagate] Propagated {num_sats} objects across {num_steps} steps in {elapsed:.2f} seconds.")
    return positions, velocities, times
