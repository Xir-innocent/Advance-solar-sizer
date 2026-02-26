# xir_sizer.py - The core sizing function

import numpy as np
from scipy.optimize import minimize_scalar

def xir_smart_sizer(
    E_load_daily, PSH=5.0, eta_PV=0.18, eta_sys=0.75, D_aut=2, V_bat=48, DoD=0.8, eta_bat=0.9, 
    P_peak_factor=1.25, cost_PV_per_kW=1200000, cost_bat_per_kWh=200000, cost_inv_per_kW=150000, 
    cost_cc_per_A=5000, cost_breaker=20000, cost_wiring_per_m=500, r=0.1, M=25, tariff=225, 
    EF_grid=0.5, target_LPSP=0.05
):
    E_load = E_load_daily * 1.3
    P_PV_base = E_load / (PSH * eta_PV * eta_sys)
    P_peak = (E_load / 8) * 2  # Rough peak
    P_inv = P_peak * P_peak_factor
    C_bat_kWh = (E_load * D_aut) / (DoD * eta_bat) * 1.2
    panel_kW = 0.3  # Assume 300W panels
    I_sc_panel = 5.5
    N_parallel_base = np.ceil(P_PV_base / panel_kW)
    I_cc_base = I_sc_panel * N_parallel_base * 1.3

    # Breaker: DC side = 1.25 × I_cc, AC side = P_inv / V_ac (assume 240V)
    breaker_DC = 1.25 * I_cc_base
    breaker_AC = (P_inv * 1000) / 240 * 1.25  # A

    # Wiring: Approximate length 50m, voltage drop <3%, use AWG table lookup (simplified)
    wire_current = max(I_cc_base, breaker_AC)
    if wire_current > 100:
        wire_AWG = '4 AWG'
    elif wire_current > 50:
        wire_AWG = '6 AWG'
    else:
        wire_AWG = '8 AWG'
    wiring_cost = 50 * cost_wiring_per_m  # 50m estimate

    # Optimization: Minimize LCOE with LPSP penalty
    def objective(scale):
        P_PV = P_PV_base * scale
        C_bat_adj = C_bat_kWh * scale
        I_cc = I_sc_panel * np.ceil(P_PV / panel_kW) * 1.3
        TNPC = (P_PV * cost_PV_per_kW) + (C_bat_adj * cost_bat_per_kWh) + (P_inv * cost_inv_per_kW) + (I_cc * cost_cc_per_A) + (2 * cost_breaker) + wiring_cost
        CRF = r * (1 + r)**M / ((1 + r)**M - 1)
        ACS = TNPC * CRF
        E_gen_annual = P_PV * PSH * 365 * eta_sys
        LCOE = ACS / E_gen_annual if E_gen_annual > 0 else np.inf

        irradiance_var = 0.2
        E_gen_daily_avg = P_PV * PSH * eta_sys
        LPSP = max(0, 1 - (E_gen_daily_avg / E_load)) + irradiance_var * 0.05
        if LPSP > target_LPSP:
            LCOE += (LPSP - target_LPSP) * 10
        return LCOE

    res = minimize_scalar(objective, bounds=(0.8, 1.5), method='bounded')
    opt_scale = res.x
    P_PV_opt = P_PV_base * opt_scale
    C_bat_opt = C_bat_kWh * opt_scale
    N_panels = np.ceil(P_PV_opt / panel_kW)
    I_cc_opt = I_sc_panel * np.ceil(N_panels / 10) * 1.3  # Assume strings of 10 panels
    breaker_DC_opt = 1.25 * I_cc_opt
    breaker_AC_opt = (P_inv * 1000) / 240 * 1.25

    TNPC_opt = (P_PV_opt * cost_PV_per_kW) + (C_bat_opt * cost_bat_per_kWh) + (P_inv * cost_inv_per_kW) + (I_cc_opt * cost_cc_per_A) + (2 * cost_breaker) + wiring_cost
    E_gen_annual_opt = P_PV_opt * PSH * 365 * eta_sys
    LCOE_opt = (TNPC_opt * (r * (1 + r)**M / ((1 + r)**M - 1))) / E_gen_annual_opt
    annual_savings = E_load_daily * 365 * tariff
    payback = TNPC_opt / annual_savings
    CO2_avoided = E_gen_annual_opt * EF_grid

    return {
        'PV Capacity (kW)': round(P_PV_opt, 2),
        'Number of Panels (300W)': int(N_panels),
        'Inverter Capacity (kW)': round(P_inv, 2),
        'Battery Capacity (kWh)': round(C_bat_opt, 2),
        'Charge Controller (A)': round(I_cc_opt, 2),
        'DC Breaker (A)': round(breaker_DC_opt, 2),
        'AC Breaker (A)': round(breaker_AC_opt, 2),
        'Wire Gauge Recommendation': wire_AWG,
        'Total Estimated Cost (₦)': round(TNPC_opt),
        'LCOE (₦/kWh)': round(LCOE_opt, 2),
        'Payback Period (years)': round(payback, 1),
        'Annual CO2 Saved (kg)': round(CO2_avoided, 0)
    }