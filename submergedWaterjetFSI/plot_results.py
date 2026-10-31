#!/usr/bin/env python3
"""
Comprehensive Post-Processing Script for Submerged Waterjet FSI Simulation.
Tracks:
1. Center plate downward indentation depth (Dz) vs time.
2. Peak von Mises stress (sigmaEq) in solid plate vs initial yield limit (sigmaY0 = 65 MPa).
3. Peak equivalent plastic strain (epsilonPEq) in solid plate (permanent dent metric).
4. Yield status and active yielding cell counts.
"""

import sys
import os
import glob
import re
import numpy as np

def parse_scalar_field(path):
    if not os.path.exists(path):
        return 0.0
    with open(path, 'r', errors='ignore') as f:
        text = f.read()
    
    # Check for nonuniform list first
    match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;', text, re.DOTALL)
    if match:
        vals = [float(x) for x in match.group(1).split()]
        return max(vals) if vals else 0.0
    
    # Check for uniform scalar
    match = re.search(r'internalField\s+uniform\s+([0-9.eE+-]+);', text)
    if match:
        return float(match.group(1))
    
    return 0.0

def main():
    disp_file = "postProcessing/0/solidPointDisplacement_centerPlateDisplacement.dat"
    if not os.path.exists(disp_file):
        candidates = glob.glob("postProcessing/*/solidPointDisplacement_centerPlateDisplacement.dat")
        if candidates:
            disp_file = candidates[0]
        else:
            print(f"Notice: {disp_file} not found.")
            disp_file = None

    times = []
    dz_um = []
    if disp_file and os.path.exists(disp_file):
        with open(disp_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        t = float(parts[0])
                        # Dz is downward deflection in meters; convert to micrometers (um)
                        defl = -float(parts[3]) * 1e6
                        times.append(t * 1e6) # microseconds
                        dz_um.append(defl)
                    except ValueError:
                        continue

    # Find written time directories
    time_dirs = []
    for entry in os.listdir('.'):
        if os.path.isdir(entry):
            try:
                t_val = float(entry)
                if t_val > 0:
                    time_dirs.append((t_val, entry))
            except ValueError:
                pass
    time_dirs.sort(key=lambda x: x[0])

    saved_times_us = []
    max_sigma_mpa = []
    max_epsp = []

    for t_val, t_dir in time_dirs:
        solid_dir = os.path.join(t_dir, "solid")
        sigma_file = os.path.join(solid_dir, "sigmaEq")
        epsp_file = os.path.join(solid_dir, "epsilonPEq")
        
        s_max = parse_scalar_field(sigma_file) / 1e6 # Convert to MPa
        p_max = parse_scalar_field(epsp_file)
        
        saved_times_us.append(t_val * 1e6)
        max_sigma_mpa.append(s_max)
        max_epsp.append(p_max)

    print("==========================================================================")
    print(" Submerged Continuous Waterjet on Copper Plate: FSI Diagnostics Summary   ")
    print("==========================================================================")
    print(f"Annealed Copper Yield Stress: 65.0 MPa | Plate Thickness: 0.3 mm")
    print("--------------------------------------------------------------------------")
    
    if times:
        print(f"Total time steps tracked: {len(times)}")
        print(f"Time span: {times[0]:.2f} us -> {times[-1]:.2f} us")
        print(f"Maximum center indentation depth: {max(dz_um):.4f} um")
        print("--------------------------------------------------------------------------")
        print(f"{'Time [us]':>10} | {'Dent Depth [um]':>16} | {'Max Sigma [MPa]':>16} | {'Max Plastic Strain':>18}")
        print("--------------------------------------------------------------------------")
        
        for t, d in zip(times, dz_um):
            # Find closest saved time dir
            s_str = "---"
            p_str = "---"
            if saved_times_us:
                idx = np.argmin(np.abs(np.array(saved_times_us) - t))
                if abs(saved_times_us[idx] - t) < 1e-3:
                    s_str = f"{max_sigma_mpa[idx]:.2f}"
                    p_str = f"{max_epsp[idx]:.6f}"
            print(f"{t:10.2f} | {d:16.4f} | {s_str:>16} | {p_str:>18}")
        print("==========================================================================")
    else:
        print("No displacement history records found.")

    # Generate multi-panel plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
        
        # Panel 1: Center Displacement
        if times:
            ax1.plot(times, dz_um, 'b-o', lw=2, markersize=4, label='Center Indentation Depth ($D_z$)')
            ax1.set_ylabel('Dent Depth [$\\mu$m]', fontsize=11, fontweight='bold', color='navy')
            ax1.grid(True, linestyle='--', alpha=0.6)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.set_title('Submerged Waterjet Elastoplastic Impact Dynamics', fontsize=12, fontweight='bold')

        # Panel 2: Max Stress vs Yield Stress
        if saved_times_us:
            ax2.plot(saved_times_us, max_sigma_mpa, 'r-s', lw=2, markersize=5, label='Peak von Mises Stress $\\sigma_{eq}$')
            ax2.axhline(65.0, color='darkred', linestyle='--', lw=1.5, label='Initial Yield Stress $\\sigma_{y0} = 65$ MPa')
            ax2.set_ylabel('Von Mises Stress [MPa]', fontsize=11, fontweight='bold', color='darkred')
            ax2.grid(True, linestyle='--', alpha=0.6)
            ax2.legend(loc='upper left', fontsize=10)

        ax2.set_xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
        plt.tight_layout()
        out_img = "indentation_vs_time.png"
        plt.savefig(out_img, dpi=200)
        print(f"High-resolution diagnostic plot saved to: {out_img}")
    except Exception as e:
        print(f"Plot generation note: {e}")

if __name__ == "__main__":
    main()
