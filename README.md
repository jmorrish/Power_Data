# Marine Power MVP (Improved)

Local professional MVP for hybrid solar + wind + hydro power simulation on marine platforms with battery.

## Improvements
- Stable HYCOM OPeNDAP URL for historical currents (2018-present, 3-hr interpolated to hourly).
- Correct timezone for NASA POWER (Local Time Meridian).
- Bug fixes and error handling.
- Added battery cycle estimate.
- Worst-week SOC plot.

## Quick Start
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py

For ERA5: Configure CDS API key in ~/.cdsapirc.

Notes:
- For currents pre-2018, HYCOM expt_93.0 starts late 2018. For older, use CMEMS GLOBAL_MULTIYEAR_PHY_001_030 (requires registration at marine.copernicus.eu).