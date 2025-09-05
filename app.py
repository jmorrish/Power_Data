import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import plotly.express as px
from datetime import timedelta

from energy import (
    PVParams, WindParams, HydroParams, BatteryParams,
    run_point_sim
)

st.set_page_config(page_title="Marine Hybrid Power MVP", layout="wide")
st.title("Marine Hybrid Power Simulator")
st.caption("Professional tool for solar, wind, hydro on marine platforms with battery modeling.")

col_site, col_map = st.columns([1, 2])
with col_site:
    st.header("Site Selection")
    lat = st.number_input("Latitude", -90.0, 90.0, 50.7, format="%.4f")
    lon = st.number_input("Longitude", -180.0, 180.0, -3.5, format="%.4f")
    year = st.number_input("Simulation Year", 1984, 2100, 2024)

with col_map:
    m = folium.Map(location=[lat, lon], zoom_start=6)
    folium.Marker([lat, lon]).add_to(m)
    map_data = st_folium(m, width=700, height=400)
    if map_data and map_data["last_clicked"]:
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.info(f"Updated: Lat {lat:.4f}, Lon {lon:.4f}")

# NEW: Checkboxes for enabling generation methods
st.subheader("Generation Methods")
col_methods = st.columns(4)  # UPDATED: Added one more column for the new checkbox
with col_methods[0]:
    use_pv = st.checkbox("Enable Solar PV", True)
with col_methods[1]:
    use_wind = st.checkbox("Enable Wind", True)
with col_methods[2]:
    use_hydro = st.checkbox("Enable Hydro", True)
with col_methods[3]:
    interference = st.checkbox("Enable Solar-Wind Interference (Solar >50W stops Wind)", False)  # NEW

col_pv, col_wind = st.columns(2)
with col_pv:
    st.header("Solar PV")
    Wp = st.number_input("Panel Wattage (Wp)", 10, 1000, 400)
    count = st.number_input("Number of Panels", 1, 100, 6)
    tilt = st.number_input("Tilt (degrees)", 0.0, 90.0, 30.0)
    az = st.number_input("Azimuth (degrees, 180=South)", 0.0, 360.0, 180.0)
    gamma = st.number_input("Temp Coeff (%/°C)", -1.0, 0.0, -0.35)
    noct = st.number_input("NOCT (°C)", 20.0, 60.0, 45.0)
    module_eff = st.slider("Module Efficiency (%)", 10, 25, 20) / 100
    dc_loss = st.slider("DC Losses (%)", 0, 30, 6) / 100
    mppt_eff = st.slider("MPPT Efficiency (%)", 80, 100, 97) / 100
    inv_eff = st.slider("Inverter Efficiency (%)", 80, 100, 96) / 100
    misc_pr = st.slider("Misc PR Losses (%)", 0, 20, 5) / 100
    fouled_min = st.slider("% Fouled Min", 0, 100, 5)
    fouled_max = st.slider("% Fouled Max", 0, 100, 60)
    cleaning_cycle = st.number_input("Cleaning Cycle (days)", 0, 365, 30)

with col_wind:
    st.header("Wind Turbine")
    hub_h = st.number_input("Hub Height (m)", 1.0, 50.0, 12.0)
    z0 = st.number_input("Roughness Length (m)", 0.0001, 0.001, 0.0002, format="%.6f")
    cut_in = st.number_input("Cut-in Speed (m/s)", 0.0, 10.0, 3.0)
    rated_v = st.number_input("Rated Speed (m/s)", 5.0, 20.0, 12.0)
    rated_p = st.number_input("Rated Power (W)", 100.0, 5000.0, 600.0)
    cut_out = st.number_input("Cut-out Speed (m/s)", 10.0, 50.0, 25.0)
    wind_eff = st.slider("System Efficiency (%)", 50, 100, 90) / 100
    wind_avail = st.slider("Availability (%)", 70, 100, 95) / 100
    count_wind = st.number_input("Number of Turbines", 1, 100, 1)  # NEW

col_hydro, col_batt = st.columns(2)
with col_hydro:
    st.header("Hydrogenerator")
    dia = st.number_input("Rotor Diameter (m)", 0.05, 5.0, 0.4)
    Cp = st.number_input("Power Coefficient (Cp)", 0.05, 0.59, 0.35)
    hydro_eff = st.slider("Mech/Elec Efficiency (%)", 50, 100, 85) / 100
    hydro_avail = st.slider("Availability (%)", 50, 100, 90) / 100
    count_hydro = st.number_input("Number of Generators", 1, 100, 1)  # NEW

with col_batt:
    st.header("Battery")
    cap_Wh = st.number_input("Capacity (Wh)", 1000, 100000, 10000)
    dod = st.slider("Usable DoD (%)", 10, 100, 90) / 100
    eta_rt = st.slider("Round-trip Efficiency (%)", 70, 100, 92) / 100
    max_chg = st.number_input("Max Charge (kW)", 0.1, 10.0, 1.5)
    max_dis = st.number_input("Max Discharge (kW)", 0.1, 10.0, 2.0)

col_load, col_data = st.columns(2)
with col_load:
    st.header("Load")
    load_kwh = st.number_input("Daily Load (kWh)", 0.0, 100.0, 6.0)

with col_data:
    st.header("Data Sources")
    use_cmems = st.checkbox("Use CMEMS for Currents (global, requires copernicusmarine login)", False)
    cmems_dataset_id = "cmems_mod_nws_phy-uv_my_7km-2D_PT1H-i"
    if use_cmems:
        if st.button("Load Available CMEMS Datasets"):
            try:
                import copernicusmarine
                datasets = copernicusmarine.describe()['datasets']
                available_datasets = [ds['dataset_id'] for ds in datasets if 'phy' in ds['dataset_id'].lower() and ('uo' in ds['variables'] or 'vo' in ds['variables'])]
                st.session_state['available_datasets'] = available_datasets
            except Exception as e:
                st.error(f"Failed to load datasets: {str(e)}")
        available_datasets = st.session_state.get('available_datasets', [])
        if available_datasets:
            cmems_dataset_id = st.selectbox("Select CMEMS Dataset", available_datasets)
        else:
            cmems_dataset_id = st.text_input("Enter Custom CMEMS Dataset ID", cmems_dataset_id)
    uploaded_file = st.file_uploader("Upload Hourly Currents CSV (optional, overrides others)", type="csv")
    uploaded_currents = None
    if uploaded_file is not None:
        uploaded_currents = pd.read_csv(uploaded_file, index_col="time", parse_dates=True)
        uploaded_currents = resample_hourly(uploaded_currents)
    # NEW: Uploads for solar and wind
    upload_solar_file = st.file_uploader("Upload Hourly Solar Met CSV (overrides fetched, columns: GHI, DNI, DHI, T2M_C, WS10M optional)", type="csv")
    uploaded_solar = None
    if upload_solar_file is not None:
        uploaded_solar = pd.read_csv(upload_solar_file, index_col="time", parse_dates=True)
        uploaded_solar = resample_hourly(uploaded_solar)
    upload_wind_file = st.file_uploader("Upload Hourly Wind Met CSV (overrides WS10M)", type="csv")
    uploaded_wind = None
    if upload_wind_file is not None:
        uploaded_wind = pd.read_csv(upload_wind_file, index_col="time", parse_dates=True)
        uploaded_wind = resample_hourly(uploaded_wind)
    use_manual_currents = st.checkbox("Use Manual Synthetic Currents (overrides fetches)")
    mean_v = 0.5
    peak_v = 1.5
    if use_manual_currents:
        mean_v = st.number_input("Mean Current Speed (m/s)", 0.0, 5.0, 0.5)
        peak_v = st.number_input("Peak Current Speed (m/s)", 0.0, 5.0, 1.5)

if st.button("Run Simulation", type="primary"):
    with st.spinner("Fetching data and simulating..."):
        pv_params = PVParams(
            Wp, count, tilt, az, gamma, noct, dc_loss, mppt_eff, inv_eff, misc_pr, module_efficiency=module_eff,
            fouled_min_pct=fouled_min, fouled_max_pct=fouled_max, cleaning_cycle_days=cleaning_cycle
        )
        wind_params = WindParams(hub_h, z0, wind_eff, cut_in, rated_v, rated_p, cut_out, wind_avail, count=count_wind)  # UPDATED: Pass count
        hydro_params = HydroParams(dia, Cp, hydro_eff, hydro_avail, count=count_hydro)  # UPDATED: Pass count
        batt_params = BatteryParams(cap_Wh, dod, eta_rt, max_chg, max_dis)
        df, summary = run_point_sim(
            lat, lon, year, pv_params, wind_params, hydro_params, batt_params, load_kwh,
            use_cmems, uploaded_currents, use_manual_currents, mean_v, peak_v, cmems_dataset_id=cmems_dataset_id,
            uploaded_solar=uploaded_solar, uploaded_wind=uploaded_wind,  # NEW
            use_pv=use_pv, use_wind=use_wind, use_hydro=use_hydro,  # NEW
            interference=interference  # NEW
        )
    st.success("Simulation complete!")

    st.header("Key Metrics")
    cols = st.columns(4)
    cols[0].metric("PV kWh/year", f"{summary['energy_kwh']['pv']:.1f}")
    cols[1].metric("Wind kWh/year", f"{summary['energy_kwh']['wind']:.1f}")
    cols[2].metric("Hydro kWh/year", f"{summary['energy_kwh']['hydro']:.1f}")
    cols[3].metric("Total Gen kWh/year", f"{summary['energy_kwh']['total_gen']:.1f}")
    cols = st.columns(4)
    cols[0].metric("Exports kWh/year", f"{summary['energy_kwh']['exports']:.1f}")
    cols[1].metric("Unmet kWh/year", f"{summary['energy_kwh']['unmet']:.1f}")
    cols[2].metric("SOC Min (%)", f"{summary['battery']['soc_min_pct']:.1f}")
    cols[3].metric("SOC Max (%)", f"{summary['battery']['soc_max_pct']:.1f}")
    st.metric("Approx Cycles/year", f"{summary['battery']['cycles_approx']:.1f}")

    st.header("Plots")
    fig_power = px.line(df[["pv", "wind", "hydro"]], title="Hourly Power (W)")
    st.plotly_chart(fig_power, use_container_width=True)

    fig_soc = px.line(df["soc_frac"] * 100, title="Battery SOC (%)")
    st.plotly_chart(fig_soc, use_container_width=True)

    monthly = df[["pv", "wind", "hydro"]].resample("ME").sum() / 1000
    fig_monthly = px.bar(monthly, barmode="stack", title="Monthly Energy (kWh)")
    st.plotly_chart(fig_monthly, use_container_width=True)

    if summary["worst_week_start"]:
        worst_start = pd.to_datetime(summary["worst_week_start"])
        worst_df = df.loc[worst_start : worst_start + timedelta(days=7)]
        fig_worst = px.line(worst_df["soc_frac"] * 100, title="Worst Week SOC (%)")
        st.plotly_chart(fig_worst, use_container_width=True)

    st.download_button("Download Hourly Data (CSV)", df.to_csv(), f"simulation_{lat}_{lon}_{year}.csv")