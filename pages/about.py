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

### 1. PV kWh/year
**What It Means**: The total energy (in kilowatt-hours, kWh) produced by your solar panels over one year.

**How It's Calculated**:
- Uses sunlight data (Global Horizontal Irradiance, Direct Normal Irradiance, and Diffuse Horizontal Irradiance, in W/m²) adjusted for panel tilt (\( \theta \)) and azimuth (\( \phi \)).
- Cell temperature (\( T_{\text{cell}} \), °C):
  \[
  T_{\text{cell}} = T_{\text{air}} + \frac{\text{POA}_{\text{global}} \cdot (\text{NOCT} - 20)}{800}
  \]
- Power per panel (W):
  \[
  P_{\text{panel}} = W_p \cdot \frac{\text{POA}_{\text{global}}}{1000} \cdot \left(1 + \frac{\gamma}{100} \cdot (T_{\text{cell}} - 25)\right)
  \]
- Fouling reduction (if enabled):
  \[
  \text{Fouling_pct} = \text{fouled_min_pct} + (\text{fouled_max_pct} - \text{fouled_min_pct}) \cdot \frac{\text{cycle_position}}{\text{cleaning_cycle_days}}
  \]
  \[
  P_{\text{panel}} = P_{\text{panel}} \cdot \left(1 - \frac{\text{Fouling_pct}}{100}\right)
  \]
- System losses:
  \[
  P_{\text{DC}} = P_{\text{panel}} \cdot N_{\text{panels}} \cdot (1 - \text{dc_loss_frac}) \cdot (1 - \text{misc_pr_frac})
  \]
  \[
  P_{\text{AC}} = P_{\text{DC}} \cdot \text{mppt_eff} \cdot \text{inv_eff}
  \]
- Annual total:
  \[
  \text{PV kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{AC},h}}{1000}
  \]

### 2. Wind kWh/year
**What It Means**: The total energy (in kWh) produced by your wind turbine(s) over one year.

**How It's Calculated**:
- Wind speed adjustment to hub height:
  \[
  v_{\text{hub}} = v_{10} \cdot \frac{\log\left(\frac{h + \epsilon}{z_0 + \epsilon}\right)}{\log\left(\frac{10}{z_0 + \epsilon}\right)}
  \]
- Power curve:
  - If \( v_{\text{hub}} < v_{\text{cut_in}} \) or \( v_{\text{hub}} > v_{\text{cut_out}} \): \( P = 0 \)
  - If \( v_{\text{cut_in}} \leq v_{\text{hub}} < v_{\text{rated}} \):
    \[
    P = P_{\text{rated}} \cdot \left( \frac{v_{\text{hub}} - v_{\text{cut_in}}}{v_{\text{rated}} - v_{\text{cut_in}}} \right)^3
  \]
  - If \( v_{\text{rated}} \leq v_{\text{hub}} \leq v_{\text{cut_out}} \): \( P = P_{\text{rated}} \)
- Apply efficiencies:
  \[
  P_{\text{wind}} = P \cdot \text{air_system_eff} \cdot \text{availability_frac} \cdot N_{\text{turbines}}
  \]
- (Interference: \( P_{\text{wind}} = 0 \) if solar > 50W.)
- Annual total:
  \[
  \text{Wind kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{wind},h}}{1000}
  \]

### 3. Hydro kWh/year
**What It Means**: The total energy (in kWh) produced by your hydrogenerator(s) using ocean currents over one year.

**How It's Calculated**:
- Synthetic currents (if used):
  \[
  v_{\text{current}} = \text{mean_v} + (\text{peak_v} - \text{mean_v}) \cdot \sin\left( \frac{2\pi \cdot t}{12.42 \cdot 3600} \right)
  \]
- Power:
  \[
  P_{\text{hydro}} = 0.5 \cdot 1025 \cdot \pi \cdot \left(\frac{\text{rotor_diam_m}}{2}\right)^2 \cdot \text{Cp} \cdot v_{\text{current}}^3 \cdot \text{mech_elec_eff} \cdot \text{availability_frac} \cdot N_{\text{generators}}
  \]
- Annual total:
  \[
  \text{Hydro kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{hydro},h}}{1000}
  \]

### 4. Total Gen kWh/year
**What It Means**: The total energy (in kWh) produced by all sources combined over one year.

**How It's Calculated**:
- Hourly total:
  \[
  P_{\text{total},h} = P_{\text{AC},h} + P_{\text{wind},h} + P_{\text{hydro},h}
  \]
- Annual total:
  \[
  \text{Total Gen kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{total},h}}{1000}
  \]

### 5. Excess kWh/year
**What It Means**: The total excess energy (in kWh) that can't be used or stored.

**How It's Calculated**:
- Hourly surplus:
  \[
  \text{surplus}_h = P_{\text{total},h} - \text{load}_h
  \]
  where \( \text{load}_h = \frac{\text{load_kwh_per_day} \cdot 1000}{24} \).
- If surplus > 0:
  \[
  \text{chg_pwr}_h = \min(\text{surplus}_h, \text{max_charge_kW} \cdot 1000)
  \]
  \[
  \text{chg_Wh}_h = \text{chg_pwr}_h \cdot 1
  \]
  \[
  \text{chg_Wh_eff}_h = \min(\text{chg_Wh}_h \cdot \sqrt{\text{eta_roundtrip}}, E_{\text{max}} - \text{SOC}_h)
  \]
  \[
  \text{excess}_h = \text{surplus}_h - \text{chg_pwr}_h
  \]
- Annual total:
  \[
  \text{Excess kWh/year} = \frac{\sum_{h=1}^{8760} \text{excess}_h}{1000}
  \]

### 6. Unmet kWh/year
**What It Means**: The total energy shortfall (in kWh) not met by generation or battery.

**How It's Calculated**:
- If surplus < 0:
  \[
  \text{need_pwr}_h = \min(-\text{surplus}_h, \text{max_discharge_kW} \cdot 1000)
  \]
  \[
  \text{need_Wh}_h = \text{need_pwr}_h \cdot 1
  \]
  \[
  \text{used_Wh}_h = \min(\text{need_Wh}_h, \text{SOC}_h \cdot \sqrt{\text{eta_roundtrip}})
  \]
  \[
  \text{dis}_h = \text{used_Wh}_h
  \]
  \[
  \text{unmet}_h = \max(0, -\text{surplus}_h - \text{dis}_h)
  \]
- Annual total:
  \[
  \text{Unmet kWh/year} = \frac{\sum_{h=1}^{8760} \text{unmet}_h}{1000}
  \]

### 7. SOC Min (%)
**What It Means**: The lowest battery charge level (percentage) during the year.

**How It's Calculated**:
- \( E_{\text{max}} = \text{capacity_Wh} \cdot \text{usable_DoD_frac} \)
- Update SOC hourly (clipped to [0, \( E_{\text{max}} \)]).
- \[
  \text{SOC_frac}_h = \frac{\text{SOC}_h}{E_{\text{max}}}
  \]
- \[
  \text{SOC Min (%)} = \min_{h=1}^{8760} (\text{SOC_frac}_h \cdot 100)
  \]

### 8. SOC Max (%)
**What It Means**: The highest battery charge level (percentage) during the year.

**How It's Calculated**:
- Same as SOC Min:
  \[
  \text{SOC Max (%)} = \max_{h=1}^{8760} (\text{SOC_frac}_h \cdot 100)
  \]

### 9. Approx Cycles/year
**What It Means**: Estimated number of full battery cycles in a year.

**How It's Calculated**:
- Hourly change:
  \[
  \Delta \text{SOC}_h = |\text{SOC}_h - \text{SOC}_{h-1}|
  \]
- \[
  \text{Approx Cycles/year} = \sum_{h=1}^{8760} \frac{\Delta \text{SOC}_h}{2 \cdot E_{\text{max}}}
  \]

## Data Sources and Assumptions
- **Data**: Sunlight/wind from NASA POWER; currents from CMEMS or synthetic models.
- **Assumptions**: Hourly steps, constant load, seawater density of 1025 kg/m³.
- **Customization**: Disable sources or add interference for realistic scenarios.

This simulator is built for accuracy and ease—contact us for customizations or questions!
""")