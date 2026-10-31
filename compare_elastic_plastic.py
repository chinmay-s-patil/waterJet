#!/usr/bin/env python3
"""
Benchmark Comparison: Purely Elastic vs Elastoplastic Copper Plate Dynamic Unloading
Evaluates dynamic loading, ramp-down, and unloading relaxation.
"""

import sys
import os
import glob
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read_displacement(case_dir):
    pattern = os.path.join(case_dir, "postProcessing/*/solidPointDisplacement_centerPlateDisplacement.dat")
    files = glob.glob(pattern)
    if not files:
        return [], []
    times, dz_um = [], []
    with open(files[0], 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0]) * 1e6 # us
                    defl = -float(parts[3]) * 1e6 # um (downward)
                    times.append(t)
                    dz_um.append(defl)
                except ValueError:
                    continue
    return times, dz_um

def get_expected_end_time(case_dir):
    control_dict = os.path.join(case_dir, "system", "controlDict")
    if not os.path.exists(control_dict):
        return None
    try:
        with open(control_dict, 'r') as f:
            content = f.read()
        m = re.search(r'endTime\s+([0-9.eE+-]+)\s*;', content)
        if m:
            return float(m.group(1)) * 1e6 # us
    except Exception:
        pass
    return None

def parse_plastic_strain(case_dir):
    """
    Distinguishes absent field (linearElastic) vs zero plastic strain vs nonzero plastic strain.
    Returns (status_str, value_float)
    """
    time_dirs = []
    for entry in os.listdir(case_dir):
        path = os.path.join(case_dir, entry)
        if os.path.isdir(path):
            try:
                t_val = float(entry)
                if t_val > 0:
                    time_dirs.append((t_val, path))
            except ValueError:
                pass
    if not time_dirs:
        return "Absent (No time output)", None
    time_dirs.sort(key=lambda x: x[0])
    latest_solid = os.path.join(time_dirs[-1][1], "solid", "epsilonPEq")
    
    if not os.path.exists(latest_solid):
        return "Absent (Not modeled)", None

    try:
        with open(latest_solid, 'r', errors='ignore') as f:
            text = f.read()
        match_nonuniform = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;', text, re.DOTALL)
        if match_nonuniform:
            vals = [float(x) for x in match_nonuniform.group(1).split()]
            max_val = max(vals) if vals else 0.0
            if max_val > 1e-9:
                return f"{max_val:.6f} (Active Yield)", max_val
            else:
                return "0.000000 (Elastic zone)", 0.0
        match_uniform = re.search(r'internalField\s+uniform\s+([0-9.eE+-]+);', text)
        if match_uniform:
            val = float(match_uniform.group(1))
            if val > 1e-9:
                return f"{val:.6f} (Active Yield)", val
            else:
                return "0.000000 (Elastic zone)", 0.0
    except Exception as e:
        return f"Error reading: {e}", None

    return "Unknown", None

def compute_displacement_rate(times, dz_um):
    """
    Computes displacement rate d(Dz)/dt in um/us (equivalent to m/s).
    """
    if len(times) < 2:
        return []
    rates = []
    for i in range(len(times)):
        if i == 0:
            dt = times[1] - times[0]
            rate = (dz_um[1] - dz_um[0]) / dt if dt > 0 else 0.0
        elif i == len(times) - 1:
            dt = times[-1] - times[-2]
            rate = (dz_um[-1] - dz_um[-2]) / dt if dt > 0 else 0.0
        else:
            dt = times[i+1] - times[i-1]
            rate = (dz_um[i+1] - dz_um[i-1]) / dt if dt > 0 else 0.0
        rates.append(rate)
    return rates

def main():
    case_elastic = "case_elastic"
    case_plastic = "case_plastic"

    t_el, d_el = read_displacement(case_elastic)
    t_pl, d_pl = read_displacement(case_plastic)

    if not t_el and not t_pl:
        print("Notice: No displacement data found in case_elastic or case_plastic yet.")
        return

    expected_end_el = get_expected_end_time(case_elastic)
    expected_end_pl = get_expected_end_time(case_plastic)

    epsp_str_el, _ = parse_plastic_strain(case_elastic)
    epsp_str_pl, epsp_val_pl = parse_plastic_strain(case_plastic)

    rate_el = compute_displacement_rate(t_el, d_el) if t_el else []
    rate_pl = compute_displacement_rate(t_pl, d_pl) if t_pl else []

    # Final relaxation check: average rate over the last 10% of simulation time
    def check_relaxation(t_arr, r_arr):
        if not t_arr or not r_arr:
            return "N/A", 0.0
        cutoff = t_arr[-1] * 0.90
        recent = [abs(r_arr[i]) for i in range(len(t_arr)) if t_arr[i] >= cutoff]
        mean_rate = np.mean(recent) if recent else abs(r_arr[-1])
        if mean_rate < 0.05: # < 0.05 um/us = 0.05 m/s
            return "Relaxed (Equilibrium)", mean_rate
        else:
            return "Dynamically Oscillating", mean_rate

    rel_status_el, mean_v_el = check_relaxation(t_el, rate_el)
    rel_status_pl, mean_v_pl = check_relaxation(t_pl, rate_pl)

    print("==========================================================================")
    print(" Elastic vs Elastoplastic Copper Plate Dynamic Unloading Benchmark        ")
    print("==========================================================================")
    print(f"{'Metric':<34} | {'Case A (Purely Elastic)':<22} | {'Case B (Elastoplastic)':<22}")
    print("--------------------------------------------------------------------------")
    
    # Check completeness
    t_end_el = t_el[-1] if t_el else 0.0
    t_end_pl = t_pl[-1] if t_pl else 0.0
    warn_el = ""
    if expected_end_el and t_end_el < expected_end_el * 0.98:
        warn_el = f" [WARN: Early stop at {t_end_el:.1f}us]"
    warn_pl = ""
    if expected_end_pl and t_end_pl < expected_end_pl * 0.98:
        warn_pl = f" [WARN: Early stop at {t_end_pl:.1f}us]"

    print(f"{'Simulation Duration':<34} | {f'{t_end_el:.1f} us{warn_el}':<22} | {f'{t_end_pl:.1f} us{warn_pl}':<22}")

    max_d_el = max(d_el) if d_el else 0.0
    fin_d_el = d_el[-1] if d_el else 0.0
    max_d_pl = max(d_pl) if d_pl else 0.0
    fin_d_pl = d_pl[-1] if d_pl else 0.0

    rec_d_el = max_d_el - fin_d_el
    rec_d_pl = max_d_pl - fin_d_pl
    springback_el = (rec_d_el / max_d_el * 100) if max_d_el > 0 else 0.0
    springback_pl = (rec_d_pl / max_d_pl * 100) if max_d_pl > 0 else 0.0

    print(f"{'Peak Deflection [um]':<34} | {max_d_el:20.4f} um | {max_d_pl:20.4f} um")
    print(f"{'Deflection at End of Sim [um]':<34} | {fin_d_el:20.4f} um | {fin_d_pl:20.4f} um")
    print(f"{'Recovered Displacement [um]':<34} | {rec_d_el:20.4f} um | {rec_d_pl:20.4f} um")
    print(f"{'Dynamic Recovery Ratio [%]':<34} | {springback_el:20.1f} %  | {springback_pl:20.1f} %")
    print(f"{'Structural Relaxation Status':<34} | {rel_status_el:<22} | {rel_status_pl:<22}")
    print(f"{'Mean End Displacement Rate':<34} | {f'{mean_v_el:.3f} um/us (m/s)':<22} | {f'{mean_v_pl:.3f} um/us (m/s)':<22}")
    print(f"{'Plastic Strain (epsilonPEq)':<34} | {epsp_str_el:<22} | {epsp_str_pl:<22}")
    print("==========================================================================")

    # Multi-panel Comparison Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    t_max = max(t_end_el, t_end_pl, 100.0)

    # Shaded phases
    for ax in (ax1, ax2):
        ax.axvspan(0, 40, color='#fff7bc', alpha=0.6, label='Stage 1: Loading (U = 30 m/s)')
        ax.axvspan(40, 45, color='#fee391', alpha=0.7, label='Stage 2: Ramp-Down (30 -> 0 m/s)')
        ax.axvspan(45, t_max, color='#e5f5e0', alpha=0.6, label='Stage 3: Unloading (U = 0 m/s)')

    # Top panel: Displacements
    if t_el:
        ax1.plot(t_el, d_el, 'b--', lw=2.2, label=f'Case A: Purely Elastic (End: {fin_d_el:.2f} $\\mu$m)')
    if t_pl:
        ax1.plot(t_pl, d_pl, 'r-', lw=2.4, label=f'Case B: Elastoplastic Copper (End: {fin_d_pl:.2f} $\\mu$m)')

    ax1.axhline(0, color='gray', linestyle=':', lw=1)
    ax1.set_ylabel('Center Deflection $D_z$ [$\\mu$m]', fontsize=11, fontweight='bold')
    ax1.set_title('Submerged Waterjet Dynamic Unloading: Elastic vs Elastoplastic Copper Plate', fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    # Deduplicate legend handles for ax1
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), fontsize=9, loc='upper left')

    # Bottom panel: Velocity / Displacement rate d(Dz)/dt
    if t_el and rate_el:
        ax2.plot(t_el, rate_el, 'b--', lw=1.8, label='Elastic Rate $\\dot{D}_z$')
    if t_pl and rate_pl:
        ax2.plot(t_pl, rate_pl, 'r-', lw=1.8, label='Elastoplastic Rate $\\dot{D}_z$')

    ax2.axhline(0, color='black', linestyle='-', lw=0.8)
    ax2.set_xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Deflection Rate [m/s]', fontsize=11, fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(fontsize=9, loc='lower left')

    plt.tight_layout()
    out_img = "elastic_vs_plastic_comparison.png"
    plt.savefig(out_img, dpi=200)
    print(f"Comparison plot saved to: {out_img}")

if __name__ == "__main__":
    main()
