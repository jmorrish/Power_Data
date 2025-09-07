import streamlit as st

st.set_page_config(page_title="About Marine Hybrid Power Simulator", layout="wide")
st.title("About Marine Hybrid Power Simulator")

st.markdown("""
Welcome to the **Marine Hybrid Power Simulator**, a professional tool designed for modeling and simulating hybrid renewable energy systems on marine platforms like boats, offshore buoys, or remote ocean installations. This app helps you evaluate the performance of solar photovoltaic (PV), wind turbines, hydrogenerators (using ocean currents), and battery storage to meet your daily energy needs. Whether you're planning for energy independence at sea or optimizing a sustainable setup, this simulator provides year-long hourly insights into energy production, battery health, and system reliability.

## What the Simulator Does
- **Site and System Configuration**: Enter your location (latitude/longitude), simulation year, and customize components like panel count, turbine specs, or battery capacity.
- **Data Sources**: Pulls real-world weather and ocean data from NASA POWER for solar/wind and CMEMS for currents (or use your own uploaded files for custom scenarios).
- **Simulation**: Runs a full-year, hourly model to calculate energy generation, battery charging/discharging, excess energy (exports), and shortfalls (unmet load).
- **Outputs**: Displays key metrics, charts (e.g., hourly power, monthly energy, battery SOC), and a downloadable CSV of results.
- **Key Features**: Enable/disable sources, simulate solar-wind interference, and use synthetic currents for quick tests.

The app assumes a constant daily load (your input kWh divided evenly over 24 hours) and focuses on off-grid marine applications where reliability is critical.

## How the Metrics Are Calculated
Below, we explain each metric shown in the "Key Metrics" section, including what it means and the mathematical formulas used. These are based on standard renewable energy models and hourly simulations.
""")

st.subheader("1. PV kWh/year")
st.markdown("**What It Means**: The total energy (in kilowatt-hours, kWh) produced by your solar panels over one year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Uses sunlight data (Global Horizontal Irradiance, Direct Normal Irradiance, and Diffuse Horizontal Irradiance, in W/m²) adjusted for panel tilt (θ) and azimuth (φ).")
st.markdown("- Cell temperature (T_cell, °C):")
st.latex(r"T_{\text{cell}} = T_{\text{air}} + \frac{\text{POA}_{\text{global}} \cdot (\text{NOCT} - 20)}{800}")
st.markdown("- Power per panel (W):")
st.latex(r"P_{\text{panel}} = W_p \cdot \frac{\text{POA}_{\text{global}}}{1000} \cdot \left(1 + \frac{\gamma}{100} \cdot (T_{\text{cell}} - 25)\right)")
st.markdown("- Fouling reduction (if enabled):")
st.latex(r"\text{Fouling_pct} = \text{fouled_min_pct} + (\text{fouled_max_pct} - \text{fouled_min_pct}) \cdot \frac{\text{cycle_position}}{\text{cleaning_cycle_days}}")
st.latex(r"P_{\text{panel}} = P_{\text{panel}} \cdot \left(1 - \frac{\text{Fouling_pct}}{100}\right)")
st.markdown("- System losses:")
st.latex(r"P_{\text{DC}} = P_{\text{panel}} \cdot N_{\text{panels}} \cdot (1 - \text{dc_loss_frac}) \cdot (1 - \text{misc_pr_frac})")
st.latex(r"P_{\text{AC}} = P_{\text{DC}} \cdot \text{mppt_eff} \cdot \text{inv_eff}")
st.markdown("- Annual total:")
st.latex(r"\text{PV kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{AC},h}}{1000}")

st.subheader("2. Wind kWh/year")
st.markdown("**What It Means**: The total energy (in kWh) produced by your wind turbine(s) over one year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Wind speed adjustment to hub height:")
st.latex(r"v_{\text{hub}} = v_{10} \cdot \frac{\log\left(\frac{h + \epsilon}{z_0 + \epsilon}\right)}{\log\left(\frac{10}{z_0 + \epsilon}\right)}")
st.markdown("- Power curve:")
st.markdown("  - If v_hub < v_cut_in or v_hub > v_cut_out: P = 0")
st.markdown("  - If v_cut_in ≤ v_hub < v_rated:")
st.latex(r"P = P_{\text{rated}} \cdot \left( \frac{v_{\text{hub}} - v_{\text{cut_in}}}{v_{\text{rated}} - v_{\text{cut_in}}} \right)^3")
st.markdown("  - If v_rated ≤ v_hub ≤ v_cut_out: P = P_rated")
st.markdown("- Apply efficiencies:")
st.latex(r"P_{\text{wind}} = P \cdot \text{air_system_eff} \cdot \text{availability_frac} \cdot N_{\text{turbines}}")
st.markdown("- (Interference: P_wind = 0 if solar > 50W.)")
st.markdown("- Annual total:")
st.latex(r"\text{Wind kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{wind},h}}{1000}")

st.subheader("3. Hydro kWh/year")
st.markdown("**What It Means**: The total energy (in kWh) produced by your hydrogenerator(s) using ocean currents over one year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Synthetic currents (if used):")
st.latex(r"v_{\text{current}} = \text{mean_v} + (\text{peak_v} - \text{mean_v}) \cdot \sin\left( \frac{2\pi \cdot t}{12.42 \cdot 3600} \right)")
st.markdown("- Power:")
st.latex(r"P_{\text{hydro}} = 0.5 \cdot 1025 \cdot \pi \cdot \left(\frac{\text{rotor_diam_m}}{2}\right)^2 \cdot \text{Cp} \cdot v_{\text{current}}^3 \cdot \text{mech_elec_eff} \cdot \text{availability_frac} \cdot N_{\text{generators}}")
st.markdown("- Annual total:")
st.latex(r"\text{Hydro kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{hydro},h}}{1000}")

st.subheader("4. Total Gen kWh/year")
st.markdown("**What It Means**: The total energy (in kWh) produced by all sources combined over one year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Hourly total:")
st.latex(r"P_{\text{total},h} = P_{\text{AC},h} + P_{\text{wind},h} + P_{\text{hydro},h}")
st.markdown("- Annual total:")
st.latex(r"\text{Total Gen kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{total},h}}{1000}")

st.subheader("5. Excess kWh/year")
st.markdown("**What It Means**: The total excess energy (in kWh) that can't be used or stored.")
st.markdown("**How It's Calculated**:")
st.markdown("- Hourly surplus:")
st.latex(r"\text{surplus}_h = P_{\text{total},h} - \text{load}_h")
st.markdown("  where load_h = (load_kwh_per_day · 1000) / 24.")
st.markdown("- If surplus > 0:")
st.latex(r"\text{chg_pwr}_h = \min(\text{surplus}_h, \text{max_charge_kW} \cdot 1000)")
st.latex(r"\text{chg_Wh}_h = \text{chg_pwr}_h \cdot 1")
st.latex(r"\text{chg_Wh_eff}_h = \min(\text{chg_Wh}_h \cdot \sqrt{\text{eta_roundtrip}}, E_{\text{max}} - \text{SOC}_h)")
st.latex(r"\text{excess}_h = \text{surplus}_h - \text{chg_pwr}_h")
st.markdown("- Annual total:")
st.latex(r"\text{Excess kWh/year} = \frac{\sum_{h=1}^{8760} \text{excess}_h}{1000}")

st.subheader("6. Unmet kWh/year")
st.markdown("**What It Means**: The total energy shortfall (in kWh) not met by generation or battery.")
st.markdown("**How It's Calculated**:")
st.markdown("- If surplus < 0:")
st.latex(r"\text{need_pwr}_h = \min(-\text{surplus}_h, \text{max_discharge_kW} \cdot 1000)")
st.latex(r"\text{need_Wh}_h = \text{need_pwr}_h \cdot 1")
st.latex(r"\text{used_Wh}_h = \min(\text{need_Wh}_h, \text{SOC}_h \cdot \sqrt{\text{eta_roundtrip}})")
st.latex(r"\text{dis}_h = \text{used_Wh}_h")
st.latex(r"\text{unmet}_h = \max(0, -\text{surplus}_h - \text{dis}_h)")
st.markdown("- Annual total:")
st.latex(r"\text{Unmet kWh/year} = \frac{\sum_{h=1}^{8760} \text{unmet}_h}{1000}")

st.subheader("7. SOC Min (%)")
st.markdown("**What It Means**: The lowest battery charge level (percentage) during the year.")
st.markdown("**How It's Calculated**:")
st.latex(r"E_{\text{max}} = \text{capacity_Wh} \cdot \text{usable_DoD_frac}")
st.markdown("- Update SOC hourly (clipped to [0, E_max]).")
st.latex(r"\text{SOC_frac}_h = \frac{\text{SOC}_h}{E_{\text{max}}}")
st.latex(r"\text{SOC Min (%)} = \min_{h=1}^{8760} (\text{SOC_frac}_h \cdot 100)")

st.subheader("8. SOC Max (%)")
st.markdown("**What It Means**: The highest battery charge level (percentage) during the year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Same as SOC Min:")
st.latex(r"\text{SOC Max (%)} = \max_{h=1}^{8760} (\text{SOC_frac}_h \cdot 100)")

st.subheader("9. Approx Cycles/year")
st.markdown("**What It Means**: Estimated number of full battery cycles in a year.")
st.markdown("**How It's Calculated**:")
st.markdown("- Hourly change:")
st.latex(r"\Delta \text{SOC}_h = |\text{SOC}_h - \text{SOC}_{h-1}|")
st.latex(r"\text{Approx Cycles/year} = \sum_{h=1}^{8760} \frac{\Delta \text{SOC}_h}{2 \cdot E_{\text{max}}}")

st.markdown("""
## Data Sources and Assumptions
- **Data**: Sunlight/wind from NASA POWER; currents from CMEMS or synthetic models.
- **Assumptions**: Hourly steps, constant load, seawater density of 1025 kg/m³.
- **Customization**: Disable sources or add interference for realistic scenarios.

This simulator is built for accuracy and ease—contact us for customizations or questions!
""")