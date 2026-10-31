#!/usr/bin/env python3
"""
Comprehensive Post-Processing & Validation Diagnostics for Submerged Waterjet FSI.
Tracks:
1. Center plate downward indentation depth (Dz) vs time [um].
2. Peak von Mises stress (sigmaEq) in solid plate vs initial yield limit (sigmaY0 = 65 MPa).
3. Peak equivalent plastic strain (epsilonPEq) in solid plate (permanent dent metric).
4. Interface forces (pressure, viscous, total) from fluid/forces functionObject.
"""

import sys
import os
import glob
import re
import numpy as np

def parse_scalar_field(path):
    """
    Parses an OpenFOAM scalar field file (e.g., sigmaEq, epsilonPEq).
    Returns max scalar value as float if present, or None if file is missing.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', errors='ignore') as f:
            text = f.read()
        
        # Check for nonuniform list
        match = re.search(r'internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;', text, re.DOTALL)
        if match:
            vals = [float(x) for x in match.group(1).split()]
            return max(vals) if vals else 0.0
        
        # Check for uniform scalar
        match = re.search(r'internalField\s+uniform\s+([0-9.eE+-]+);', text)
        if match:
            return float(match.group(1))
    except Exception as e:
        print(f"Warning parsing {path}: {e}")
        return None
    
    return None

def parse_forces(path):
    """
    Parses OpenFOAM forces.dat file.
    Returns (times, F_pressure_z, F_viscous_z, F_total_z)
    """
    if not os.path.exists(path):
        return [], [], [], []
    times, fp_z, fv_z, ft_z = [], [], [], []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Format: time ((px py pz) (vx vy vz) (porox poroy poroz)) ...
            # Extract numbers inside parentheses
            m = re.findall(r'\(([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\)', line)
            parts = line.split()
            if len(parts) > 0 and len(m) >= 2:
                try:
                    t = float(parts[0])
                    pz = float(m[0][2]) # Pressure force Z
                    vz = float(m[1][2]) # Viscous force Z
                    times.append(t * 1e6) # us
                    fp_z.append(pz)
                    fv_z.append(vz)
                    ft_z.append(pz + vz)
                except ValueError:
                    continue
    return times, fp_z, fv_z, ft_z

def main():
    disp_file = "postProcessing/0/solidPointDisplacement_centerPlateDisplacement.dat"
    if not os.path.exists(disp_file):
        candidates = glob.glob("postProcessing/*/solidPointDisplacement_centerPlateDisplacement.dat")
        if candidates:
            disp_file = candidates[0]
        else:
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
                        # Dz downward deflection in meters -> convert to um
                        defl = -float(parts[3]) * 1e6
                        times.append(t * 1e6) # us
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
        
        s_val = parse_scalar_field(sigma_file)
        p_val = parse_scalar_field(epsp_file)
        
        saved_times_us.append(t_val * 1e6)
        max_sigma_mpa.append(s_val / 1e6 if s_val is not None else None)
        max_epsp.append(p_val)

    # Check for forces file
    forces_candidates = glob.glob("postProcessing/fluid/forces/*/forces.dat") + \
                        glob.glob("postProcessing/forces/*/forces.dat") + \
                        glob.glob("postProcessing/*/forces.dat")
    f_times, fp_z, fv_z, ft_z = [], [], [], []
    if forces_candidates:
        f_times, fp_z, fv_z, ft_z = parse_forces(forces_candidates[0])

    print("==========================================================================")
    print(" Submerged Continuous Waterjet on Copper Plate: FSI Diagnostics Summary   ")
    print("==========================================================================")
    print("Annealed Copper Yield Stress: 65.0 MPa | Plate Thickness: 0.3 mm")
    print("Jet Velocity: 30 m/s | Square Nozzle: 2x2 mm (Area: 4 mm²)")
    print("Theoretical Steady Jet Momentum Thrust: F = rho * A * U² = 3.60 N")
    print("--------------------------------------------------------------------------")
    
    if times:
        print(f"Total time steps tracked: {len(times)}")
        print(f"Time span: {times[0]:.2f} us -> {times[-1]:.2f} us")
        print(f"Maximum center indentation depth: {max(dz_um):.4f} um")
        print("--------------------------------------------------------------------------")
        print(f"{'Time [us]':>10} | {'Dent Depth [um]':>16} | {'Max Sigma [MPa]':>16} | {'Max Plastic Strain':>18}")
        print("--------------------------------------------------------------------------")
        
        for t, d in zip(times, dz_um):
            s_str = "---"
            p_str = "---"
            if saved_times_us:
                idx = np.argmin(np.abs(np.array(saved_times_us) - t))
                if abs(saved_times_us[idx] - t) < 1e-3:
                    s_val = max_sigma_mpa[idx]
                    p_val = max_epsp[idx]
                    s_str = f"{s_val:.2f}" if s_val is not None else "[MISSING]"
                    p_str = f"{p_val:.6f}" if p_val is not None else "[MISSING]"
            print(f"{t:10.2f} | {d:16.4f} | {s_str:>16} | {p_str:>18}")
        print("==========================================================================")
    else:
        print("No displacement history records found.")

    # 3-Panel Diagnostic Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 10), sharex=True)
        
        # Panel 1: Center Displacement
        if times:
            ax1.plot(times, dz_um, 'b-o', lw=2, markersize=4, label='Center Indentation Depth ($D_z$)')
            ax1.set_ylabel('Dent Depth [$\\mu$m]', fontsize=11, fontweight='bold', color='navy')
            ax1.grid(True, linestyle='--', alpha=0.6)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.set_title('Submerged Waterjet Impact on Copper Plate: FSI Diagnostics', fontsize=13, fontweight='bold')

        # Panel 2: Peak von Mises Stress vs Yield Stress
        valid_s_pts = [(t, s) for t, s in zip(saved_times_us, max_sigma_mpa) if s is not None]
        if valid_s_pts:
            ts, ss = zip(*valid_s_pts)
            ax2.plot(ts, ss, 'r-s', lw=2, markersize=5, label='Peak von Mises Stress $\\sigma_{eq}$')
            ax2.axhline(65.0, color='darkred', linestyle='--', lw=1.5, label='Initial Yield Stress $\\sigma_{y0} = 65$ MPa')
            ax2.set_ylabel('Stress [MPa]', fontsize=11, fontweight='bold', color='darkred')
            ax2.grid(True, linestyle='--', alpha=0.6)
            ax2.legend(loc='upper left', fontsize=10)

        # Panel 3: Equivalent Plastic Strain
        valid_p_pts = [(t, p) for t, p in zip(saved_times_us, max_epsp) if p is not None]
        if valid_p_pts:
            tp, pp = zip(*valid_p_pts)
            ax3.plot(tp, pp, 'g-^', lw=2, markersize=5, label='Peak Equivalent Plastic Strain $\\varepsilon_{p,eq}$')
            ax3.set_ylabel('Plastic Strain [-]', fontsize=11, fontweight='bold', color='darkgreen')
            ax3.grid(True, linestyle='--', alpha=0.6)
            ax3.legend(loc='upper left', fontsize=10)

        ax3.set_xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
        plt.tight_layout()
        out_img = "indentation_vs_time.png"
        plt.savefig(out_img, dpi=200)
        print(f"3-Panel diagnostic plot saved to: {out_img}")
    except Exception as e:
        print(f"Plot generation note: {e}")

if __name__ == "__main__":
    main()
