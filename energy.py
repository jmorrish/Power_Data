# Updated energy.py with correct CMEMS fetch

import os
import math
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

import numpy as np
import pandas as pd
import requests
import xarray as xr
import pytz
import pvlib
from pvlib.irradiance import get_total_irradiance
from pvlib.temperature import noct_sam
from timezonefinder import TimezoneFinder

# Utilities

def get_ltm_tz(lon: float) -> str:
    offset = round(lon / 15)
    if offset >= 0:
        return f'Etc/GMT-{offset}'
    else:
        return f'Etc/GMT+{-offset}'

def to_local_index(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    return df.tz_convert(tz)

def resample_hourly(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("1h").interpolate(limit=1).ffill().bfill()

# Data fetchers

def fetch_nasa_power_hourly(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    base = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    variables = [
        "ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF",
        "T2M", "PS", "WS10M", "WD10M", "RH2M"
    ]
    url = f"{base}?parameters={','.join(variables)}&community=RE&longitude={lon}&latitude={lat}&start={start.replace('-','')}&end={end.replace('-','')}&format=JSON&user=demo"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        payload = data.get("properties", {}).get("parameter", {})
        if not payload:
            raise RuntimeError("No data from NASA POWER")
        series = {var: pd.Series(vals) for var, vals in payload.items()}
        df = pd.DataFrame(series)
        df.index = pd.to_datetime(df.index, format="%Y%m%d%H")
        df["PS_Pa"] = df.get("PS", 0) * 1000.0
        df = df.rename(columns={
            "ALLSKY_SFC_SW_DWN": "GHI", "ALLSKY_SFC_SW_DNI": "DNI",
            "ALLSKY_SFC_SW_DIFF": "DHI", "T2M": "T2M_C"
        })
        tz = get_ltm_tz(lon)
        return df.tz_localize(tz)
    except Exception as e:
        raise RuntimeError(f"NASA POWER fetch failed: {str(e)}")

def fetch_era5_point(lat: float, lon: float, year: int, cache_dir: str) -> Optional[pd.DataFrame]:
    try:
        import cdsapi
    except ImportError:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    target = os.path.join(cache_dir, f"era5_{year}_{lat:.3f}_{lon:.3f}.nc")
    if not os.path.exists(target):
        c = cdsapi.Client()
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
                "year": str(year),
                "month": list(map(lambda m: f"{m:02d}", range(1, 13))),
                "day": list(map(lambda d: f"{d:02d}", range(1, 32))),
                "time": list(map(lambda h: f"{h:02d}:00", range(24))),
                "format": "netcdf",
                "area": [lat + 0.05, lon - 0.05, lat - 0.05, lon + 0.05],
            },
            target,
        )
    ds = xr.open_dataset(target)
    ds_pt = ds.sel(latitude=lat, longitude=lon % 360, method="nearest")
    u = ds_pt["u10"].to_series()
    v = ds_pt["v10"].to_series()
    ws = np.sqrt(u**2 + v**2)
    df = pd.DataFrame({"WS10M": ws})
    df.index = pd.to_datetime(df.index).tz_localize("UTC")
    return df

def fetch_hycom_surface_current(lat: float, lon: float, start: str, end: str) -> Optional[pd.DataFrame]:
    url = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"
    try:
        ds = xr.open_dataset(url, decode_times=False)
        # Manual time decoding
        if 'time' in ds.variables:
            time_units = ds.time.attrs.get('units', 'hours since 2000-01-01 00:00:00')
            ref_time = pd.to_datetime(time_units.split('since ')[1])
            ds = ds.assign_coords(time=ref_time + pd.to_timedelta(ds.time.values, unit='h'))
        lon360 = (lon + 360) % 360
        t0 = np.datetime64(pd.to_datetime(start))
        t1 = np.datetime64(pd.to_datetime(end))
        ds = ds.sel(time=slice(t0, t1))
        ds_pt = ds.sel(lat=lat, lon=lon360, depth=0, method="nearest")
        u = ds_pt["water_u"].to_series()
        v = ds_pt["water_v"].to_series()
        spd = np.sqrt(u**2 + v**2)
        out = pd.DataFrame({"CURR_U": u, "CURR_V": v, "CURR_SPD": spd})
        out.index = pd.to_datetime(out.index).tz_localize("UTC")
        return resample_hourly(out)  # Interpolate 3-hr to hourly
    except Exception as e:
        print(f"HYCOM fetch failed: {str(e)}")
        return None

def fetch_cmems_surface_current(lat: float, lon: float, start: str, end: str, cache_dir: str, dataset_id: str) -> Optional[pd.DataFrame]:
    try:
        import copernicusmarine
    except ImportError:
        print("copernicusmarine not installed. Install with pip install copernicusmarine and login via CLI.")
        return None
    os.makedirs(cache_dir, exist_ok=True)
    target = os.path.join(cache_dir, f"cmems_currents_{dataset_id}_{lat:.3f}_{lon:.3f}_{start}_{end}.nc")
    if not os.path.exists(target):
        copernicusmarine.subset(
            dataset_id=dataset_id,
            variables=["uo", "vo"],
            minimum_longitude=lon - 0.1,
            maximum_longitude=lon + 0.1,
            minimum_latitude=lat - 0.1,
            maximum_latitude=lat + 0.1,
            start_datetime=start,
            end_datetime=end,
            output_filename=target
        )
    ds = xr.open_dataset(target)
    ds_pt = ds.sel(latitude=lat, longitude=lon, method="nearest")
    u = ds_pt["uo"].to_series()
    v = ds_pt["vo"].to_series()
    spd = np.sqrt(u**2 + v**2)
    out = pd.DataFrame({"CURR_U": u, "CURR_V": v, "CURR_SPD": spd})
    out.index = pd.to_datetime(out.index).tz_localize("UTC")
    return resample_hourly(out)

def generate_synthetic_currents(index: pd.DatetimeIndex, mean_v: float, peak_v: float) -> pd.Series:
    t_seconds = (index - index[0]).total_seconds()
    period = 12.42 * 3600  # M2 tidal period in seconds
    amp = (peak_v - mean_v)
    cur_spd = mean_v + amp * np.sin(2 * np.pi * t_seconds / period)
    return pd.Series(cur_spd, index=index).clip(lower=0.0)

# Power models

@dataclass
class PVParams:
    Wp: float
    count: int
    tilt_deg: float
    az_deg: float
    gamma_pct_per_C: float
    NOCT_C: float
    dc_loss_frac: float
    mppt_eff: float
    inv_eff: float
    misc_pr_frac: float
    module_efficiency: float  # STC module efficiency (e.g., 0.20 for 20%)
    fouled_min_pct: float = 0.0
    fouled_max_pct: float = 0.0
    cleaning_cycle_days: float = 0.0

def pv_power_hourly(lat, lon, tz, met_df: pd.DataFrame, params: PVParams) -> pd.Series:
    times = met_df.index
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    dni = met_df.get("DNI", 0).clip(lower=0).fillna(0)
    ghi = met_df.get("GHI", 0).clip(lower=0).fillna(0)
    dhi = met_df.get("DHI", 0).clip(lower=0).fillna(0)
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    poa = get_total_irradiance(
        params.tilt_deg, params.az_deg, dni, ghi, dhi,
        sp["apparent_zenith"], sp["azimuth"], model="perez",
        dni_extra=dni_extra
    )
    poa_irr = poa["poa_global"].clip(lower=0).fillna(0)
    t_air = met_df.get("T2M_C", 15)
    ws = met_df.get("WS10M", 1)
    t_cell = noct_sam(
        poa_global=poa_irr, 
        temp_air=t_air, 
        wind_speed=ws, 
        noct=params.NOCT_C, 
        module_efficiency=params.module_efficiency
    )
    gamma = params.gamma_pct_per_C / 100
    p_panel = params.Wp * (poa_irr / 1000) * (1 + gamma * (t_cell - 25))
    p_panel = p_panel.clip(lower=0)
    
    if params.cleaning_cycle_days > 0:
        start_time = times[0]
        fractional_days = (times - start_time).total_seconds() / 86400.0
        cycle_position = fractional_days % params.cleaning_cycle_days
        fouling_pct = params.fouled_min_pct + (params.fouled_max_pct - params.fouled_min_pct) * (cycle_position / params.cleaning_cycle_days)
    else:
        fouling_pct = pd.Series(0.0, index=times)
    p_panel *= (1 - fouling_pct / 100)
    
    p_dc = p_panel * params.count * (1 - params.dc_loss_frac) * (1 - params.misc_pr_frac)
    p_chg = p_dc * params.mppt_eff
    p_ac = p_chg * params.inv_eff
    return p_ac

@dataclass
class WindParams:
    hub_height_m: float
    roughness_z0: float
    air_system_eff: float
    cut_in: float
    rated_speed: float
    rated_power_w: float
    cut_out: float
    availability_frac: float
    count: int = 1  # NEW: Number of wind turbines

def shear_to_height(ws10: pd.Series, h: float, z0: float) -> pd.Series:
    eps = 1e-6
    factor = np.log((h + eps) / (z0 + eps)) / np.log(10 / (z0 + eps))
    return ws10.clip(lower=0.01) * factor

def wind_power_curve(speed: pd.Series, p: WindParams) -> pd.Series:
    spd = speed.clip(lower=0)
    pc = pd.Series(0.0, index=spd.index)
    mask_ramp = (spd >= p.cut_in) & (spd < p.rated_speed)
    mask_rated = (spd >= p.rated_speed) & (spd <= p.cut_out)
    pc[mask_ramp] = p.rated_power_w * ((spd[mask_ramp] - p.cut_in) / (p.rated_speed - p.cut_in))**3
    pc[mask_rated] = p.rated_power_w
    pc *= p.air_system_eff * p.availability_frac * p.count  # UPDATED: Multiply by count
    return pc

@dataclass
class HydroParams:
    rotor_diam_m: float
    Cp: float
    mech_elec_eff: float
    availability_frac: float
    count: int = 1  # NEW: Number of hydro generators

def hydro_power(speed: pd.Series, p: HydroParams) -> pd.Series:
    rho = 1025.0
    A = math.pi * (p.rotor_diam_m / 2)**2
    power = 0.5 * rho * A * p.Cp * (speed.clip(lower=0)**3) * p.mech_elec_eff * p.availability_frac * p.count  # UPDATED: Multiply by count
    return power

@dataclass
class BatteryParams:
    capacity_Wh: float
    usable_DoD_frac: float
    eta_roundtrip: float
    max_charge_kW: float
    max_discharge_kW: float

def battery_dispatch(hourly_gen_w: pd.DataFrame, hourly_load_w: pd.Series, bp: BatteryParams) -> Tuple[pd.DataFrame, float]:
    index = hourly_gen_w.index
    df = pd.DataFrame(index=index)
    df["gen_pv"] = hourly_gen_w.get("pv", pd.Series(0.0, index=index)).fillna(0)
    df["gen_wind"] = hourly_gen_w.get("wind", pd.Series(0.0, index=index)).fillna(0)
    df["gen_hydro"] = hourly_gen_w.get("hydro", pd.Series(0.0, index=index)).fillna(0)
    df["gen_total"] = df[["gen_pv", "gen_wind", "gen_hydro"]].sum(1)
    df["load"] = hourly_load_w.clip(lower=0).fillna(0)
    E_max = bp.capacity_Wh * bp.usable_DoD_frac
    eta_ch = math.sqrt(bp.eta_roundtrip)
    eta_dis = math.sqrt(bp.eta_roundtrip)
    soc = 0.5 * E_max
    soc_list = []
    chg_list = []
    dis_list = []
    unmet_list = []
    export_list = []
    cycles = 0.0
    prev_soc = soc
    for _, row in df.iterrows():
        gen = row["gen_total"]
        load = row["load"]
        surplus = gen - load
        chg = dis = unmet = export = 0.0
        if surplus >= 0:
            chg_pwr = min(surplus, bp.max_charge_kW * 1000)
            chg_Wh = chg_pwr * 1
            headroom = E_max - soc
            chg_Wh_eff = min(chg_Wh * eta_ch, headroom)
            soc += chg_Wh_eff
            export = surplus - chg_pwr
            chg = chg_pwr
        else:
            need_pwr = min(-surplus, bp.max_discharge_kW * 1000)
            need_Wh = need_pwr * 1
            avail_Wh = soc * eta_dis
            used_Wh = min(need_Wh, avail_Wh)
            soc -= used_Wh / eta_dis
            dis = used_Wh
            unmet = max(-surplus - need_pwr, 0)
        soc = np.clip(soc, 0, E_max)
        cycles += abs(soc - prev_soc) / (2 * E_max)
        prev_soc = soc
        soc_list.append(soc)
        chg_list.append(chg)
        dis_list.append(dis)
        unmet_list.append(unmet)
        export_list.append(export)
    df["soc_Wh"] = soc_list
    df["soc_frac"] = df["soc_Wh"] / E_max if E_max > 0 else 0
    df["pwr_charge_W"] = chg_list
    df["pwr_discharge_W"] = dis_list
    df["unmet_W"] = unmet_list
    df["export_W"] = export_list
    return df, cycles

# Orchestration

def run_point_sim(
    lat: float, lon: float, year: int,
    pv: PVParams, wind: WindParams, hydro: HydroParams, batt: BatteryParams,
    load_kwh_per_day: float = 0.0,
    use_era5: bool = False,
    use_hycom: bool = True,
    use_cmems: bool = False,
    uploaded_currents: Optional[pd.DataFrame] = None,
    use_manual_currents: bool = False,
    mean_v: float = 0.5,
    peak_v: float = 1.5,
    cache_dir: str = "./cache",
    cmems_dataset_id: str = "cmems_mod_nws_phy-uv_my_7km-2D_PT1H-i",
    uploaded_solar: Optional[pd.DataFrame] = None,  # NEW
    uploaded_wind: Optional[pd.DataFrame] = None,  # NEW
    use_pv: bool = True,  # NEW
    use_wind: bool = True,  # NEW
    use_hydro: bool = True,  # NEW
    interference: bool = False  # NEW: Solar-wind interference
) -> Tuple[pd.DataFrame, Dict]:
    tz = get_ltm_tz(lon)
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    met = fetch_nasa_power_hourly(lat, lon, start, end).sort_index()
    met = resample_hourly(met)
    met_local = to_local_index(met, tz)
    
    # NEW: Override with uploaded solar data if provided
    if uploaded_solar is not None:
        if uploaded_solar.index.tz is None:
            uploaded_solar = uploaded_solar.tz_localize("UTC")
        uploaded_solar = uploaded_solar.tz_convert(tz).reindex(met_local.index).interpolate(method='time').ffill().bfill()
        for col in ["GHI", "DNI", "DHI", "T2M_C", "WS10M"]:
            if col in uploaded_solar.columns:
                met_local[col] = uploaded_solar[col]
    
    # Set ws10, potentially from ERA5
    if use_era5:
        era = fetch_era5_point(lat, lon, year, cache_dir)
        ws10 = era["WS10M"].tz_convert(tz).reindex(met_local.index).interpolate(method='time').ffill().bfill() if era is not None else met_local["WS10M"]
    else:
        ws10 = met_local["WS10M"]
    
    # NEW: Override ws10 with uploaded wind data if provided
    if uploaded_wind is not None:
        if uploaded_wind.index.tz is None:
            uploaded_wind = uploaded_wind.tz_localize("UTC")
        uploaded_wind = uploaded_wind.tz_convert(tz).reindex(met_local.index).interpolate(method='time').ffill().bfill()
        if "WS10M" in uploaded_wind.columns:
            ws10 = uploaded_wind["WS10M"]
    
    # Calculate PV if enabled
    if use_pv:
        pv_ac = pv_power_hourly(lat, lon, tz, met_local, pv)
    else:
        pv_ac = pd.Series(0.0, index=met_local.index)
    
    ws_hub = shear_to_height(ws10, wind.hub_height_m, wind.roughness_z0)
    if use_wind:
        wind_p = wind_power_curve(ws_hub, wind)
    else:
        wind_p = pd.Series(0.0, index=met_local.index)
    
    # NEW: Apply interference if enabled
    if interference:
        wind_p[pv_ac > 50] = 0.0
    
    # Currents priority: Uploaded > Manual > CMEMS > HYCOM > 0
    if uploaded_currents is not None:
        cur_spd = uploaded_currents["CURR_SPD"].reindex(pv_ac.index).interpolate()
        print("Using uploaded currents.")
    elif use_manual_currents:
        cur_spd = generate_synthetic_currents(pv_ac.index, mean_v, peak_v)
        print("Using synthetic manual currents.")
    elif use_cmems:
        cur = fetch_cmems_surface_current(lat, lon, start, end, cache_dir, dataset_id=cmems_dataset_id)
        cur_spd = cur["CURR_SPD"].tz_convert(tz).reindex(pv_ac.index).interpolate() if cur is not None else pd.Series(0.0, index=pv_ac.index)
    elif use_hycom:
        cur = fetch_hycom_surface_current(lat, lon, start, end)
        cur_spd = cur["CURR_SPD"].tz_convert(tz).reindex(pv_ac.index).interpolate() if cur is not None else pd.Series(0.0, index=pv_ac.index)
    else:
        cur_spd = pd.Series(0.0, index=pv_ac.index)
    
    # Print stats for validation
    print(f"Currents Stats: Mean={cur_spd.mean():.4f} m/s, Max={cur_spd.max():.4f} m/s, Min={cur_spd.min():.4f} m/s")
    
    if use_hydro:
        hydro_p = hydro_power(cur_spd, hydro)
    else:
        hydro_p = pd.Series(0.0, index=pv_ac.index)
    
    load_W = pd.Series((load_kwh_per_day / 24) * 1000, index=pv_ac.index)
    gen_df = pd.DataFrame({"pv": pv_ac, "wind": wind_p, "hydro": hydro_p})
    batt_df, cycles = battery_dispatch(gen_df, load_W, batt)
    out = pd.concat([gen_df, batt_df], axis=1)
    kwh = out[["pv", "wind", "hydro"]].sum() / 1000
    summary = {
        "site": {"lat": lat, "lon": lon, "tz": tz, "year": year},
        "energy_kwh": {
            "pv": float(kwh["pv"]),
            "wind": float(kwh["wind"]),
            "hydro": float(kwh["hydro"]),
            "total_gen": float(out["gen_total"].sum() / 1000),
            "exports": float(out["export_W"].sum() / 1000),
            "unmet": float(out["unmet_W"].sum() / 1000),
        },
        "battery": {
            "E_max_Wh": batt.capacity_Wh * batt.usable_DoD_frac,
            "soc_min_pct": float(out["soc_frac"].min() * 100),
            "soc_max_pct": float(out["soc_frac"].max() * 100),
            "cycles_approx": float(cycles),
        }
    }
    window = 24 * 7
    roll_min = out["soc_frac"].rolling(window).mean()
    worst_start = roll_min.idxmin()
    summary["worst_week_start"] = str(worst_start) if not pd.isna(worst_start) else None
    return out, summary