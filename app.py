import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from sgp4.api import Satrec

from ingest.celestrak import fetch_tles
from ingest.spaceweather import get_latest_spaceweather
from propagate.propagate import propagate_tles
from screening.screening import screen_conjunctions, closest_approach_for_pair
from maneuver.maneuver import compute_maneuver
from ml.predictor import DragErrorPredictor

st.set_page_config(page_title="OrbitGuard: Conjunction Risk Calculator", layout="wide")

st.title("OrbitGuard AI & Physics Conjunction Risk Calculator")
st.markdown("Live TLE screening with SGP4 propagation. Close-approach distances are estimates from public TLEs; collision probability requires covariance data and is not reported here.")

st.sidebar.header("Simulation Parameters")

weather_mode = st.sidebar.selectbox("Space Weather Mode", ["live", "quiet", "storm"], index=0)
@st.cache_data(ttl=300)
def load_spaceweather(mode):
    return get_latest_spaceweather(mode, refresh=True)

@st.cache_resource
def load_drag_predictor():
    return DragErrorPredictor()

def show_ai_estimate(satellite, weather):
    """Display the repository's demo drag-error model for one selected TLE."""
    line2 = satellite["line2"]
    mean_motion_rev_day = float(line2[52:63])
    mean_motion_rad_s = mean_motion_rev_day * 2.0 * np.pi / 86400.0
    altitude_km = (398600.4418 / mean_motion_rad_s**2) ** (1.0 / 3.0) - 6378.137
    satrec = Satrec.twoline2rv(satellite["line1"], line2)
    bstar = abs(float(satrec.bstar))
    tle_age_days = float(satellite.get("tle_age_days", 0.0))
    estimate_m = load_drag_predictor().predict_error(
        altitude_km, float(weather["f107"]), float(weather["kp"]), bstar, tle_age_days
    )
    st.subheader("AI Drag-Error Estimate")
    st.metric("Predicted along-track error", f"{estimate_m:.1f} m")
    st.caption(
        f"Inputs: mean altitude {altitude_km:.0f} km, F10.7 {weather['f107']:.1f}, "
        f"Kp {weather['kp']:.1f}, B* {bstar:.2e}, TLE age {tle_age_days:.2f} days."
    )
    st.warning(
        "Demo model: its training examples are synthetic. This estimate is not "
        "validated against measured orbit-prediction errors."
    )

sw_data = load_spaceweather(weather_mode)

st.sidebar.subheader("Spacecraft Specs")
spacecraft_mass = st.sidebar.number_input("Mass (kg)", value=500.0, min_value=10.0)
isp = st.sidebar.number_input("Engine Isp (s)", value=300.0, min_value=50.0)
available_fuel = st.sidebar.number_input("Available Fuel (kg)", value=50.0, min_value=0.0)

st.sidebar.subheader("Screening Settings")
force_live_refresh = st.sidebar.checkbox("Force fresh live data", value=False)
hbr = st.sidebar.number_input("Hard-Body Radius (m)", value=5.0, min_value=1.0)
threshold_km = st.sidebar.slider("Screening Threshold (km)", 1.0, 50.0, 10.0)
max_objects = st.sidebar.slider("Max LEO Objects to Load", 50, 2000, 100, step=50)
forecast_hours = st.sidebar.slider("Forecast Window (Hours)", 12, 168, 24)

st.sidebar.subheader("Custom Debris Ephemeris (Optional)")
st.sidebar.caption("Positions are km in the same TEME frame as SGP4 output; times are minutes from analysis start.")
use_custom_debris = st.sidebar.checkbox("Add Custom Debris Object", value=False)
custom_name = st.sidebar.text_input("Debris Name", value="CUSTOM-DEBRIS-X")
c1_t = st.sidebar.number_input("Pt 1 Time offset (min)", value=0.0)
c1_x = st.sidebar.number_input("Pt 1 X (km)", value=6500.0)
c1_y = st.sidebar.number_input("Pt 1 Y (km)", value=1000.0)
c1_z = st.sidebar.number_input("Pt 1 Z (km)", value=0.0)

c2_t = st.sidebar.number_input("Pt 2 Time offset (min)", value=30.0)
c2_x = st.sidebar.number_input("Pt 2 X (km)", value=6450.0)
c2_y = st.sidebar.number_input("Pt 2 Y (km)", value=1100.0)
c2_z = st.sidebar.number_input("Pt 2 Z (km)", value=50.0)

c3_t = st.sidebar.number_input("Pt 3 Time offset (min)", value=60.0)
c3_x = st.sidebar.number_input("Pt 3 X (km)", value=6400.0)
c3_y = st.sidebar.number_input("Pt 3 Y (km)", value=1200.0)
c3_z = st.sidebar.number_input("Pt 3 Z (km)", value=100.0)
forecast_min_low = min(c1_t, c3_t)
forecast_min_high = max(c1_t, c3_t)
debris_forecast_minutes = st.sidebar.number_input(
    "Debris position estimate time (min)",
    min_value=float(forecast_min_low),
    max_value=float(forecast_min_high),
    value=float((forecast_min_low + forecast_min_high) / 2.0),
)

run_label = "Calculate Selected Satellite vs Debris" if use_custom_debris else "Run Conjunction Analysis"
if st.sidebar.button(run_label, type="primary"):
    st.session_state.pop("session_data", None)
    try:
      with st.spinner("Fetching current TLEs and propagating orbits..."):
        if force_live_refresh:
            load_spaceweather.clear()
        sw_data = load_spaceweather(weather_mode)
        f107, kp = sw_data["f107"], sw_data["kp"]
        sats = fetch_tles(max_objects=max_objects, refresh=force_live_refresh)
        if not sats:
            raise RuntimeError("No valid satellite TLEs were available. Check the network or data cache.")
        start_time = datetime.now(timezone.utc)
        positions, velocities, times = propagate_tles(sats, start_time, duration_hours=forecast_hours, step_seconds=60)
        
        if use_custom_debris:
            if not (c1_t < c2_t < c3_t):
                raise ValueError("Custom debris time offsets must be strictly increasing.")
            t0 = times[0].timestamp()
            t_pts = np.array([c1_t * 60, c2_t * 60, c3_t * 60]) + t0
            pos_pts = np.array([
                [c1_x, c1_y, c1_z],
                [c2_x, c2_y, c2_z],
                [c3_x, c3_y, c3_z]
            ])
            
            num_steps = len(times)
            custom_pos = np.full((num_steps, 3), np.nan, dtype=np.float32)
            custom_vel = np.full((num_steps, 3), np.nan, dtype=np.float32)
            
            t_seconds = np.array([t.timestamp() for t in times])
            for point_idx in range(len(t_pts) - 1):
                segment_start, segment_end = t_pts[point_idx:point_idx + 2]
                mask = (t_seconds >= segment_start) & (t_seconds <= segment_end)
                segment_seconds = segment_end - segment_start
                segment_velocity = (pos_pts[point_idx + 1] - pos_pts[point_idx]) / segment_seconds
                fraction = ((t_seconds[mask] - segment_start) / segment_seconds)[:, None]
                custom_pos[mask] = pos_pts[point_idx] + fraction * (pos_pts[point_idx + 1] - pos_pts[point_idx])
                custom_vel[mask] = segment_velocity
                
            custom_debris_idx = len(sats)
            forecast_epoch = start_time.timestamp() + debris_forecast_minutes * 60.0
            custom_prediction = np.array([
                np.interp(forecast_epoch, t_pts, pos_pts[:, dim])
                for dim in range(3)
            ])
            sats.append({"name": custom_name, "norad_id": "99999", "line1": "", "line2": ""})
            positions = np.concatenate([positions, custom_pos[:, np.newaxis, :]], axis=1)
            velocities = np.concatenate([velocities, custom_vel[:, np.newaxis, :]], axis=1)
            
        # In custom-debris mode, only the user-selected satellite/debris pair is
        # relevant. Skip the unrelated all-satellite conjunction scan.
        conjunctions = [] if use_custom_debris else screen_conjunctions(
            positions, velocities, times, sats, threshold_km=threshold_km
        )
        
        st.session_state["session_data"] = {
            "sats": sats,
            "positions": positions,
            "velocities": velocities,
            "times": times,
            "conjunctions": conjunctions,
            "start_time": start_time,
            "tle_age_days": max(sat.get("tle_age_days", 0.0) for sat in sats),
            "weather": sw_data,
            "custom_debris_idx": custom_debris_idx if use_custom_debris else None,
            "debris_forecast_minutes": debris_forecast_minutes if use_custom_debris else None,
            "debris_predicted_position_km": custom_prediction if use_custom_debris else None,
        }
        if use_custom_debris:
            st.success(f"Loaded {len(sats) - 1} satellites. Choose one below to calculate its distance from your debris coordinates.")
        else:
            st.success(f"Analysis complete! Loaded {len(sats)} objects, found {len(conjunctions)} close approaches.")
    except Exception as exc:
        st.error(f"Analysis could not be completed: {exc}")

if "session_data" in st.session_state:
    session_data = st.session_state["session_data"]
    conj_list = session_data["conjunctions"]
    st.caption(f"TLE age at analysis: up to {session_data['tle_age_days']:.1f} days. "
               f"Space weather: Kp {session_data['weather']['kp']:.1f}, "
               f"F10.7 {session_data['weather']['f107']:.1f}; "
               f"source: {session_data['weather'].get('source', 'selected mode')}. "
               "Forecast accuracy degrades with TLE age; results are screening estimates.")
    if session_data["weather"].get("observed_at"):
        st.caption(f"Weather observation times (UTC): {session_data['weather']['observed_at']}")
    st.caption("Space weather is displayed as context; propagation uses each TLE with SGP4 and does not apply a separate atmospheric drag forecast.")

    if session_data.get("custom_debris_idx") is not None:
        st.header("Selected Satellite vs Your Debris Coordinates")
        predicted_position = session_data["debris_predicted_position_km"]
        geocentric_distance = float(np.linalg.norm(predicted_position))
        estimated_altitude = geocentric_distance - 6378.137
        st.subheader("Debris Position Estimate")
        st.caption(f"Piecewise-linear estimate at +{session_data['debris_forecast_minutes']:.1f} minutes from analysis start. This is not an orbit propagation.")
        debris_cols = st.columns(5)
        debris_cols[0].metric("X", f"{predicted_position[0]:.2f} km")
        debris_cols[1].metric("Y", f"{predicted_position[1]:.2f} km")
        debris_cols[2].metric("Z", f"{predicted_position[2]:.2f} km")
        debris_cols[3].metric("Earth-Center Distance", f"{geocentric_distance:.2f} km")
        debris_cols[4].metric("Estimated Altitude", f"{estimated_altitude:.2f} km")
        debris_idx = session_data["custom_debris_idx"]
        satellite_indices = [idx for idx in range(len(session_data["sats"])) if idx != debris_idx]
        selected_sat_idx = st.selectbox(
            "Choose a satellite",
            satellite_indices,
            format_func=lambda idx: session_data["sats"][idx]["name"],
            key="tracked_satellite_idx",
        )
        try:
            pair_result = closest_approach_for_pair(
                session_data["positions"], session_data["velocities"],
                session_data["times"], selected_sat_idx, debris_idx
            )
            col1, col2, col3 = st.columns(3)
            col1.metric("Closest Distance", f"{pair_result['miss_distance_km']:.4f} km")
            col2.metric("Time of Closest Approach (UTC)", pair_result["tca_time"].strftime("%Y-%m-%d %H:%M:%S"))
            col3.metric("Relative Speed", f"{pair_result['relative_speed_km_s']:.3f} km/s")
            valid_indices = pair_result["valid_indices"]
            profile_times = [session_data["times"][idx] for idx in valid_indices]
            profile_distances = pair_result["sampled_distances_km"]
            profile = px.line(
                x=[(instant - pair_result["tca_time"]).total_seconds() / 60.0 for instant in profile_times],
                y=profile_distances,
                labels={"x": "Minutes from closest approach", "y": "Distance (km)"},
                title=f"{session_data['sats'][selected_sat_idx]['name']} to {session_data['sats'][debris_idx]['name']}",
            )
            st.plotly_chart(profile, use_container_width=True)
            show_ai_estimate(session_data["sats"][selected_sat_idx], session_data["weather"])
        except ValueError as exc:
            st.warning(str(exc))
    
    if session_data.get("custom_debris_idx") is None:
      st.header("Conjunction Screening Results")
    if session_data.get("custom_debris_idx") is not None:
        pass  # Custom-debris mode shows only the selected satellite/debris result above.
    elif not conj_list:
        st.info("No conjunctions found within the screening threshold. Try increasing the forecast window or threshold.")
    else:
        df_conj = pd.DataFrame([{
            "Satellite A": c["sat_i"],
            "Satellite B": c["sat_j"],
            "TCA (UTC)": c["tca_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "Miss Distance (km)": round(c["miss_distance_km"], 4),
            "Relative Speed (km/s)": round(c["relative_speed_km_s"], 3),
            "Proximity": ("Inside hard-body radius" if c["miss_distance_km"] * 1000 <= hbr
                          else "Very close" if c["miss_distance_km"] < 1.0 else "Screened")
        } for c in conj_list])
        
        def color_risk(val):
            color = 'red' if val == 'Inside hard-body radius' else ('orange' if val == 'Very close' else 'green')
            return f'background-color: {color}; color: white; font-weight: bold;'
            
        st.dataframe(
            df_conj.style.map(color_risk, subset=["Proximity"]),
            use_container_width=True
        )
        
        st.header("Detailed Conjunction & Maneuver Analysis")
        selected_idx = st.selectbox("Select Conjunction Pair", range(len(conj_list)), format_func=lambda i: f"{conj_list[i]['sat_i']} vs {conj_list[i]['sat_j']} ({conj_list[i]['miss_distance_km']:.3f} km)")
        
        selected_c = conj_list[selected_idx]
        lead_time = max(0.0, (selected_c["tca_time"] - session_data["start_time"]).total_seconds())
        maneuver_res = compute_maneuver(
            spacecraft_mass, isp, available_fuel,
            selected_c["miss_distance_km"], lead_time, hbr
        )
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Miss Distance", f"{selected_c['miss_distance_km']:.3f} km")
        col2.metric("Idealized Delta-v", f"{maneuver_res['dv_mps']:.3f} m/s" if np.isfinite(maneuver_res["dv_mps"]) else "No lead time")
        col3.metric("Estimated Fuel", f"{maneuver_res['fuel_used_kg']:.3f} kg" if np.isfinite(maneuver_res["fuel_used_kg"]) else "Unavailable")
        col4.metric("Fuel Budget", "Within budget" if maneuver_res["within_fuel"] else "Exceeds budget")
        
        st.markdown(f"**Screening status:** {'Inside hard-body radius' if selected_c['miss_distance_km'] * 1000 <= hbr else 'Close approach'}")
        st.caption("Maneuver values are first-order geometry estimates, not guidance. Operational decisions need validated orbit covariance and maneuver constraints.")
        show_ai_estimate(session_data["sats"][selected_c["sat_i_idx"]], session_data["weather"])
        
        st.subheader("Relative Distance Around Closest Approach")
        times = session_data["times"]
        i = selected_c["sat_i_idx"]
        j = selected_c["sat_j_idx"]
        offsets, distances = [], []
        for idx, instant in enumerate(times):
            if abs((instant - selected_c["tca_time"]).total_seconds()) <= 3600:
                delta = session_data["positions"][idx, i] - session_data["positions"][idx, j]
                if np.isfinite(delta).all():
                    offsets.append((instant - selected_c["tca_time"]).total_seconds() / 60.0)
                    distances.append(float(np.linalg.norm(delta)))
        fig = px.line(x=offsets, y=distances, labels={"x": "Time from TCA (minutes)", "y": "Distance (km)"}, title="Propagated Encounter Distance")
        fig.add_hline(y=threshold_km, line_dash="dash", line_color="orange", annotation_text="Screening Threshold")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Configure parameters in the sidebar (including optional Custom Debris coordinates) and click Run Conjunction Analysis to start.")
