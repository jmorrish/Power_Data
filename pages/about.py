import streamlit as st

st.set_page_config(page_title="About Marine Hybrid Power Simulator", layout="wide")
st.title("About Marine Hybrid Power Simulator")

st.markdown("""
Welcome to the **Marine Hybrid Power Simulator**, a tool for modeling hybrid renewable energy systems on marine platforms. The app evaluates solar PV, wind, hydrogenerators, and batteries against a constant daily load and provides year-long hourly results.
""")

st.markdown("""
## What the Simulator Does
- **Site and System Configuration**: Location, year, and component sizing.
- **Data Sources**: NASA POWER for solar/wind and CMEMS for currents, or your own files.
- **Simulation**: Hourly generation, charging/discharging, exports, and shortfalls.
- **Outputs**: Key metrics, charts, and CSV download.
- **Options**: Enable/disable sources, solar–wind interference, synthetic currents.
""")

st.markdown("""
## How the Metrics Are Calculated
Below are the definitions and formulas used in the hourly simulation.
""")

# 1. PV
st.subheader("1. PV kWh/year")
st.markdown("**Meaning**: Total yearly energy from solar PV.")
st.markdown("Cell temperature (°C):")
st.latex(r"T_{\text{cell}} = T_{\text{air}} + \frac{\text{POA}_{\text{global}} \cdot (\text{NOCT} - 20)}{800}")
st.markdown("Power per panel (W):")
st.latex(r"P_{\text{panel}} = W_p \cdot \frac{\text{POA}_{\text{global}}}{1000} \cdot \left(1 + \frac{\gamma}{100} \cdot (T_{\text{cell}} - 25)\right)")
st.markdown("Fouling reduction (if enabled):")
st.latex(r"\text{Fouling}_{\%} = \texttt{fouled\_min\_\%} + \left(\texttt{fouled\_max\_\%} - \texttt{fouled\_min\_\%}\right) \cdot \frac{\texttt{cycle\_position}}{\texttt{cleaning\_cycle\_days}}")
st.latex(r"P_{\text{panel}} \leftarrow P_{\text{panel}} \cdot \left(1 - \frac{\text{Fouling}_{\%}}{100}\right)")
st.markdown("System losses and conversion:")
st.latex(r"P_{\text{DC}} = P_{\text{panel}} \cdot N_{\text{panels}} \cdot (1 - \text{dc\_loss\_frac}) \cdot (1 - \text{misc\_pr\_frac})")
st.latex(r"P_{\text{AC}} = P_{\text{DC}} \cdot \text{mppt\_eff} \cdot \text{inv\_eff}")
st.markdown("Annual total:")
st.latex(r"\text{PV kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{AC},h}}{1000}")

# 2. Wind
st.subheader("2. Wind kWh/year")
st.markdown("**Meaning**: Total yearly energy from wind turbines.")
st.markdown("Speed adjustment to hub height:")
st.latex(r"v_{\text{hub}} = v_{10} \cdot \frac{\ln\!\left(\frac{h + \epsilon}{z_0 + \epsilon}\right)}{\ln\!\left(\frac{10}{z_0 + \epsilon}\right)}")
st.markdown("Power curve:")
st.markdown("- If $v_{hub} < v_{cut\_in}$ or $v_{hub} > v_{cut\_out}$: $P=0$")
st.markdown("- If $v_{cut\_in} \le v_{hub} < v_{rated}$:")
st.latex(r"P = P_{\text{rated}} \cdot \left(\frac{v_{\text{hub}} - v_{\text{cut\_in}}}{v_{\text{rated}} - v_{\text{cut\_in}}}\right)^3")
st.markdown("- If $v_{rated} \le v_{hub} \le v_{cut\_out}$: $P=P_{rated}$")
st.markdown("Apply efficiencies and count:")
st.latex(r"P_{\text{wind}} = P \cdot \text{air\_system\_eff} \cdot \text{availability\_frac} \cdot N_{\text{turbines}}")
st.caption("Optional interference: set $P_{wind}=0$ if solar $>50$ W.")
st.markdown("Annual total:")
st.latex(r"\text{Wind kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{wind},h}}{1000}")

# 3. Hydro
st.subheader("3. Hydro kWh/year")
st.markdown("**Meaning**: Total yearly energy from hydrogenerators (currents).")
st.markdown("Synthetic currents (if used):")
st.latex(r"v_{\text{current}} = \text{mean\_v} + (\text{peak\_v} - \text{mean\_v}) \cdot \sin\!\left( \frac{2\pi \cdot t}{12.42 \cdot 3600} \right)")
st.markdown("Power:")
st.latex(r"P_{\text{hydro}} = \tfrac{1}{2}\cdot 1025 \cdot \pi \cdot \left(\tfrac{\text{rotor\_diam\_m}}{2}\right)^2 \cdot \text{Cp} \cdot v_{\text{current}}^3 \cdot \text{mech\_elec\_eff} \cdot \text{availability\_frac} \cdot N_{\text{generators}}")
st.markdown("Annual total:")
st.latex(r"\text{Hydro kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{hydro},h}}{1000}")

# 4. Total Gen
st.subheader("4. Total Gen kWh/year")
st.markdown("**Meaning**: Yearly energy from all sources.")
st.markdown("Hourly total:")
st.latex(r"P_{\text{total},h} = P_{\text{AC},h} + P_{\text{wind},h} + P_{\text{hydro},h}")
st.markdown("Annual total:")
st.latex(r"\text{Total Gen kWh/year} = \frac{\sum_{h=1}^{8760} P_{\text{total},h}}{1000}")

# 5. Excess
st.subheader("5. Excess kWh/year")
st.markdown("**Meaning**: Yearly energy that cannot be used or stored.")
st.markdown("Hourly surplus:")
st.latex(r"\text{surplus}_h = P_{\text{total},h} - \text{load}_h")
st.markdown("Where:")
st.latex(r"\text{load}_h = \frac{\text{load\_kwh\_per\_day} \cdot 1000}{24}")
st.markdown("Charging when surplus > 0:")
st.latex(r"\text{chg\_pwr}_h = \min(\text{surplus}_h, \text{max\_charge\_kW} \cdot 1000)")
st.latex(r"\text{chg\_Wh}_h = \text{chg\_pwr}_h \cdot 1")
st.latex(r"\text{chg\_Wh\_eff}_h = \min(\text{chg\_Wh}_h \cdot \sqrt{\text{eta\_roundtrip}}, E_{\text{max}} - \text{SOC}_h)")
st.latex(r"\text{excess}_h = \text{surplus}_h - \text{chg\_pwr}_h")
st.markdown("Annual total:")
st.latex(r"\text{Excess kWh/year} = \frac{\sum_{h=1}^{8760} \text{excess}_h}{1000}")

# 6. Unmet
st.subheader("6. Unmet kWh/year")
st.markdown("**Meaning**: Yearly shortfall not met by generation or battery.")
st.markdown("Discharge when surplus < 0:")
st.latex(r"\text{need\_pwr}_h = \min(-\text{surplus}_h, \text{max\_discharge\_kW} \cdot 1000)")
st.latex(r"\text{need\_Wh}_h = \text{need\_pwr}_h \cdot 1")
st.latex(r"\text{used\_Wh}_h = \min(\text{need\_Wh}_h, \text{SOC}_h \cdot \sqrt{\text{eta\_roundtrip}})")
st.latex(r"\text{dis}_h = \text{used\_Wh}_h")
st.latex(r"\text{unmet}_h = \max(0, -\text{surplus}_h - \text{dis}_h)")
st.markdown("Annual total:")
st.latex(r"\text{Unmet kWh/year} = \frac{\sum_{h=1}^{8760} \text{unmet}_h}{1000}")

# 7. SOC Min
st.subheader("7. SOC Min (%)")
st.markdown("**Meaning**: Minimum battery state of charge over the year.")
st.latex(r"E_{\text{max}} = \text{capacity\_Wh} \cdot \text{usable\_DoD\_frac}")
st.markdown("SOC fraction and minimum:")
st.latex(r"\text{SOC\_frac}_h = \frac{\text{SOC}_h}{E_{\text{max}}}")
st.latex(r"\text{SOC Min (\%)} = \min_{h=1}^{8760} \left(\text{SOC\_frac}_h \cdot 100\right)")

# 8. SOC Max
st.subheader("8. SOC Max (%)")
st.markdown("**Meaning**: Maximum battery state of charge over the year.")
st.latex(r"\text{SOC Max (\%)} = \max_{h=1}^{8760} \left(\text{SOC\_frac}_h \cdot 100\right)")

# 9. Approx Cycles
st.subheader("9. Approx Cycles/year")
st.markdown("**Meaning**: Estimated count of full battery cycles per year.")
st.latex(r"\Delta \text{SOC}_h = \left|\text{SOC}_h - \text{SOC}_{h-1}\right|")
st.latex(r"\text{Approx Cycles/year} = \sum_{h=1}^{8760} \frac{\Delta \text{SOC}_h}{2 \cdot E_{\text{max}}}")

st.markdown("""
## Data Sources and Assumptions
- **Data**: NASA POWER (solar/wind); CMEMS or synthetic for currents.
- **Assumptions**: Hourly time step, constant load, seawater density 1025 kg/m³.
- **Customization**: Toggle sources and interference as needed.
""")
