#!/usr/bin/env python3
"""
Benchmark Comparison: Purely Elastic vs Elastoplastic Copper Plate Dynamic Unloading
Validates permanent indentation retention vs elastic springback.
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

def parse_max_scalar(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', errors='ignore') as f:
            text = f.read()
        match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;', text, re.DOTALL)
        if match:
            vals = [float(x) for x in match.group(1).split()]
            return max(vals) if vals else 0.0
        match = re.search(r'internalField\s+uniform\s+([0-9.eE+-]+);', text)
        if match:
            return float(match.group(1))
    except Exception:
        return None
    return None

def get_final_epsp(case_dir):
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
        return None
    time_dirs.sort(key=lambda x: x[0])
    latest_solid = os.path.join(time_dirs[-1][1], "solid", "epsilonPEq")
    return parse_max_scalar(latest_solid)

def main():
    case_elastic = "case_elastic"
    case_plastic = "case_plastic"

    t_el, d_el = read_displacement(case_elastic)
    t_pl, d_pl = read_displacement(case_plastic)

    if not t_el and not t_pl:
        print("Notice: No displacement data found in case_elastic or case_plastic yet.")
        return

    epsp_el = get_final_epsp(case_elastic)
    epsp_pl = get_final_epsp(case_plastic)

    print("==========================================================================")
    print(" Elastic vs Elastoplastic Copper Plate Dynamic Unloading Benchmark        ")
    print("==========================================================================")
    print(f"{'Metric':<32} | {'Case A (Purely Elastic)':<22} | {'Case B (Elastoplastic)':<22}")
    print("--------------------------------------------------------------------------")
    
    max_d_el = max(d_el) if d_el else 0.0
    fin_d_el = d_el[-1] if d_el else 0.0
    max_d_pl = max(d_pl) if d_pl else 0.0
    fin_d_pl = d_pl[-1] if d_pl else 0.0

    springback_el = ((max_d_el - fin_d_el) / max_d_el * 100) if max_d_el > 0 else 0.0
    springback_pl = ((max_d_pl - fin_d_pl) / max_d_pl * 100) if max_d_pl > 0 else 0.0

    print(f"{'Peak Deflection [um]':<32} | {max_d_el:20.4f} um | {max_d_pl:20.4f} um")
    print(f"{'Final Residual Dent [um]':<32} | {fin_d_el:20.4f} um | {fin_d_pl:20.4f} um")
    print(f"{'Elastic Springback [%]':<32} | {springback_el:20.1f} %  | {springback_pl:20.1f} %")
    print(f"{'Final Plastic Strain (eps_p)':<32} | {'0.000000 (None)':<22} | {f'{epsp_pl:.6f}' if epsp_pl is not None else 'N/A':<22}")
    print("==========================================================================")

    plt.figure(figsize=(10, 6))
    
    # Highlight Loading and Unloading regimes
    plt.axvspan(0, 40, color='lightyellow', alpha=0.5, label='Loading Phase (U = 30 m/s)')
    plt.axvspan(40, 100, color='honeydew', alpha=0.5, label='Unloading Phase (U = 0 m/s)')

    if t_el:
        plt.plot(t_el, d_el, 'b--', lw=2.2, label=f'Case A: Purely Elastic (Springback -> {fin_d_el:.2f} um)')
    if t_pl:
        plt.plot(t_pl, d_pl, 'r-', lw=2.5, label=f'Case B: Elastoplastic (Residual Dent = {fin_d_pl:.2f} um)')

    plt.axhline(0, color='gray', linestyle=':', lw=1)
    plt.xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
    plt.ylabel('Center Downward Displacement $D_z$ [$\\mu$m]', fontsize=11, fontweight='bold')
    plt.title('Benchmark: Dynamic Loading & Unloading of Copper Plate', fontsize=13, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=10, loc='upper left')
    plt.tight_layout()
    out_img = "elastic_vs_plastic_comparison.png"
    plt.savefig(out_img, dpi=200)
    print(f"Comparison plot saved to: {out_img}")

if __name__ == "__main__":
    main()
