#!/usr/bin/env python3
"""
Benchmark Comparison: Purely Elastic vs Elastoplastic Copper Plate Dynamic Unloading
Evaluates dynamic loading, ramp-down, and extended unloading relaxation.
Produces 4-panel diagnostic figure and quantitative offset & force statistics.
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
        raise FileNotFoundError(f"Missing displacement data in {case_dir}/postProcessing/")
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
    if not times:
        raise ValueError(f"No valid displacement rows found in {files[0]}")
    return np.array(times), np.array(dz_um)

def read_forces(case_dir):
    candidates = glob.glob(os.path.join(case_dir, "postProcessing/fluid/*/0/force*.dat")) + \
                 glob.glob(os.path.join(case_dir, "postProcessing/fluid/*/*/force*.dat")) + \
                 glob.glob(os.path.join(case_dir, "postProcessing/*/force*.dat"))
    if not candidates:
        raise FileNotFoundError(f"Missing force data in {case_dir}/postProcessing/")
    path = candidates[0]
    times, ft_z, fp_z, fv_z = [], [], [], []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            # Expected space-separated columns in OpenFOAM:
            # Time total_x total_y total_z pressure_x pressure_y pressure_z viscous_x viscous_y viscous_z
            if len(parts) >= 10:
                try:
                    t = float(parts[0]) * 1e6 # us
                    tot = float(parts[3]) # signed N (positive = downward normal on plate)
                    pz = float(parts[6])  # signed N
                    vz = float(parts[9])  # signed N
                    times.append(t)
                    ft_z.append(tot)
                    fp_z.append(pz)
                    fv_z.append(vz)
                except ValueError:
                    continue
    if not times:
        raise ValueError(f"No valid force records found in {path}")
    return np.array(times), np.array(ft_z), np.array(fp_z), np.array(fv_z)

def read_fluid_velocity(case_dir):
    candidates = glob.glob(os.path.join(case_dir, "postProcessing/fluid/fluidMeanVelocity/*/volFieldValue.dat")) + \
                 glob.glob(os.path.join(case_dir, "postProcessing/*/fluidMeanVelocity/*/volFieldValue.dat"))
    if not candidates:
        return np.array([]), np.array([])
    times, mag_u = [], []
    with open(candidates[0], 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            # Expected: Time (Ux Uy Uz) or Time magU
            if len(parts) >= 2:
                try:
                    t = float(parts[0]) * 1e6
                    m = re.findall(r'\(([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\)', line)
                    if m:
                        ux, uy, uz = float(m[0][0]), float(m[0][1]), float(m[0][2])
                        speed = np.sqrt(ux**2 + uy**2 + uz**2)
                    else:
                        speed = abs(float(parts[1]))
                    times.append(t)
                    mag_u.append(speed)
                except ValueError:
                    continue
    return np.array(times), np.array(mag_u)

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
    if len(times) < 2:
        return np.array([])
    rates = np.zeros_like(dz_um)
    for i in range(len(times)):
        if i == 0:
            dt = times[1] - times[0]
            rates[i] = (dz_um[1] - dz_um[0]) / dt if dt > 0 else 0.0
        elif i == len(times) - 1:
            dt = times[-1] - times[-2]
            rates[i] = (dz_um[-1] - dz_um[-2]) / dt if dt > 0 else 0.0
        else:
            dt = times[i+1] - times[i-1]
            rates[i] = (dz_um[i+1] - dz_um[i-1]) / dt if dt > 0 else 0.0
    return rates

def main():
    case_elastic = "case_elastic"
    case_plastic = "case_plastic"

    try:
        t_el, d_el = read_displacement(case_elastic)
        t_pl, d_pl = read_displacement(case_plastic)
    except Exception as e:
        print(f"Error loading displacement data: {e}")
        return

    try:
        tf_el, ft_el, fp_el, fv_el = read_forces(case_elastic)
        tf_pl, ft_pl, fp_pl, fv_pl = read_forces(case_plastic)
    except Exception as e:
        print(f"Error loading interface force data: {e}")
        return

    expected_end_el = get_expected_end_time(case_elastic)
    expected_end_pl = get_expected_end_time(case_plastic)

    epsp_str_el, _ = parse_plastic_strain(case_elastic)
    epsp_str_pl, epsp_val_pl = parse_plastic_strain(case_plastic)

    rate_el = compute_displacement_rate(t_el, d_el)
    rate_pl = compute_displacement_rate(t_pl, d_pl)

    t_end_el = t_el[-1] if len(t_el) > 0 else 0.0
    t_end_pl = t_pl[-1] if len(t_pl) > 0 else 0.0

    # Relaxation check
    def check_relaxation(t_arr, r_arr):
        cutoff = t_arr[-1] - 100.0 if t_arr[-1] > 100.0 else t_arr[-1] * 0.85
        recent = [abs(r_arr[i]) for i in range(len(t_arr)) if t_arr[i] >= cutoff]
        mean_rate = np.mean(recent) if recent else abs(r_arr[-1])
        if mean_rate < 0.02: # < 0.02 m/s
            return "Relaxed (Stationary)", mean_rate
        else:
            return "Extended Unloading / Oscillating", mean_rate

    rel_status_el, mean_v_el = check_relaxation(t_el, rate_el)
    rel_status_pl, mean_v_pl = check_relaxation(t_pl, rate_pl)

    # Offset analysis
    n_pts = min(len(t_el), len(t_pl))
    delta_d = d_pl[:n_pts] - d_el[:n_pts]
    t_common = t_el[:n_pts]

    # Calculate statistics over the final 100 us of available data
    t_window_start = max(45.0, t_common[-1] - 100.0)
    mask_window = t_common >= t_window_start
    t_win = t_common[mask_window]
    delta_win = delta_d[mask_window]

    mean_delta = np.mean(delta_win) if len(delta_win) > 0 else 0.0
    std_delta = np.std(delta_win) if len(delta_win) > 0 else 0.0
    slope_delta = 0.0
    if len(t_win) > 2:
        slope_delta, _ = np.polyfit(t_win, delta_win, 1)

    # Force statistics over final 100 us
    mask_f_el = tf_el >= t_window_start
    mask_f_pl = tf_pl >= t_window_start
    mean_f_el = np.mean(ft_el[mask_f_el])
    mean_f_pl = np.mean(ft_pl[mask_f_pl])
    std_f_el = np.std(ft_el[mask_f_el])
    std_f_pl = np.std(ft_pl[mask_f_pl])

    print("==========================================================================")
    print(" Elastic vs Elastoplastic Dynamic Unloading & Recovery Benchmark          ")
    print("==========================================================================")
    print(f"{'Metric':<34} | {'Case A (Purely Elastic)':<22} | {'Case B (Elastoplastic)':<22}")
    print("--------------------------------------------------------------------------")
    
    warn_el = f" [WARN: Stopped at {t_end_el:.1f}us]" if expected_end_el and t_end_el < expected_end_el * 0.98 else ""
    warn_pl = f" [WARN: Stopped at {t_end_pl:.1f}us]" if expected_end_pl and t_end_pl < expected_end_pl * 0.98 else ""

    print(f"{'Simulation Duration':<34} | {f'{t_end_el:.1f} us{warn_el}':<22} | {f'{t_end_pl:.1f} us{warn_pl}':<22}")

    max_d_el = np.max(d_el)
    fin_d_el = d_el[-1]
    max_d_pl = np.max(d_pl)
    fin_d_pl = d_pl[-1]

    rec_d_el = max_d_el - fin_d_el
    rec_d_pl = max_d_pl - fin_d_pl
    rec_ratio_el = (rec_d_el / max_d_el * 100) if max_d_el > 0 else 0.0
    rec_ratio_pl = (rec_d_pl / max_d_pl * 100) if max_d_pl > 0 else 0.0

    print(f"{'Peak Deflection [um]':<34} | {max_d_el:20.4f} um | {max_d_pl:20.4f} um")
    print(f"{'Deflection at End of Sim [um]':<34} | {fin_d_el:20.4f} um | {fin_d_pl:20.4f} um")
    print(f"{'Recovered Displacement [um]':<34} | {rec_d_el:20.4f} um | {rec_d_pl:20.4f} um")
    print(f"{'Dynamic Recovery Ratio [%]':<34} | {rec_ratio_el:20.1f} %  | {rec_ratio_pl:20.1f} %")
    print(f"{'Structural Relaxation Status':<34} | {rel_status_el:<22} | {rel_status_pl:<22}")
    print(f"{'Final Displacement Rate [m/s]':<34} | {f'{mean_v_el:.4f} m/s':<22} | {f'{mean_v_pl:.4f} m/s':<22}")
    
    print(f"{'Final Interface Force Fz [N]':<34} | {f'{ft_el[-1]:.3f} N':<22} | {f'{ft_pl[-1]:.3f} N':<22}")
    print(f"{'Mean Force (Final 100us) [N]':<34} | {f'{mean_f_el:.3f} +/- {std_f_el:.3f} N':<22} | {f'{mean_f_pl:.3f} +/- {std_f_pl:.3f} N':<22}")
    print(f"{'Plastic Strain (epsilonPEq)':<34} | {epsp_str_el:<22} | {epsp_str_pl:<22}")
    print("--------------------------------------------------------------------------")
    print(f" Irreversible Offset Statistics over Final 100 us ({t_window_start:.0f} to {t_common[-1]:.0f} us):")
    print(f"  * Mean Offset (Delta D_mean):    {mean_delta:.4f} um")
    print(f"  * Std Deviation (sigma_Delta):  {std_delta:.4f} um")
    print(f"  * Offset Drift Rate:            {slope_delta:.6f} um/us ({slope_delta*1000:.3f} nm/us)")
    print(f"  * Instantaneous End Offset:     {delta_d[-1]:.4f} um")
    print("==========================================================================")

    # 4-Panel Master Diagnostic Plot
    fig, axes = plt.subplots(4, 1, figsize=(11, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1.3, 1.2, 1.2]})
    (ax1, ax2, ax3, ax4) = axes

    t_max = max(t_end_el, t_end_pl, 100.0)

    # Shaded phases across all subplots
    for ax in axes:
        ax.axvspan(0, 40, color='#fff7bc', alpha=0.55, label='Stage 1: Loading (30 m/s)')
        ax.axvspan(40, 45, color='#fee391', alpha=0.7, label='Stage 2: Ramp-Down (30->0 m/s)')
        ax.axvspan(45, t_max, color='#e5f5e0', alpha=0.55, label='Stage 3: Unloading (0 m/s)')

    # Panel 1: Center Displacement
    ax1.plot(t_el, d_el, 'b--', lw=2.2, label=f'Case A: Purely Elastic (End: {fin_d_el:.2f} $\\mu$m)')
    ax1.plot(t_pl, d_pl, 'r-', lw=2.4, label=f'Case B: Elastoplastic (End: {fin_d_pl:.2f} $\\mu$m)')
    ax1.axhline(0, color='gray', linestyle=':', lw=1)
    ax1.set_ylabel('Center $D_z$ [$\\mu$m]', fontsize=11, fontweight='bold')
    ax1.set_title('Submerged Waterjet Dynamic Unloading: Elastic Springback vs Permanent Plastic Dent', fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.6)
    handles1, labels1 = ax1.get_legend_handles_labels()
    by_label1 = dict(zip(labels1, handles1))
    ax1.legend(by_label1.values(), by_label1.keys(), fontsize=8.5, loc='upper left')

    # Panel 2: Plastic Offset Delta D(t)
    ax2.plot(t_common, delta_d, 'm-', lw=2.0, label='$\\Delta D(t) = D_{plastic} - D_{elastic}$')
    ax2.axhline(mean_delta, color='k', linestyle='--', lw=1.5, label=f'Mean Offset $\\overline{{\\Delta D}} = {mean_delta:.2f}\\,\\mu$m ($\\pm {std_delta:.2f}\\,\\mu$m)')
    ax2.fill_between(t_common, mean_delta - std_delta, mean_delta + std_delta, color='m', alpha=0.15)
    ax2.set_ylabel('Offset $\\Delta D$ [$\\mu$m]', fontsize=11, fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(fontsize=8.5, loc='upper left')

    # Panel 3: Hydrodynamic Interface Force F_z(t)
    ax3.plot(tf_el, ft_el, 'b:', lw=1.8, label=f'Elastic Normal Force $F_z$ (End: {ft_el[-1]:.2f} N)')
    ax3.plot(tf_pl, ft_pl, 'r-', lw=1.8, label=f'Elastoplastic Normal Force $F_z$ (End: {ft_pl[-1]:.2f} N)')
    ax3.axhline(0, color='black', linestyle='-', lw=0.8)
    ax3.set_ylabel('Force $F_z$ [N]', fontsize=11, fontweight='bold')
    ax3.grid(True, linestyle='--', alpha=0.6)
    ax3.legend(fontsize=8.5, loc='upper right')

    # Panel 4: Deflection Rate d(Dz)/dt
    ax4.plot(t_el, rate_el, 'b--', lw=1.8, label='Elastic Rate $\\dot{D}_z$')
    ax4.plot(t_pl, rate_pl, 'r-', lw=1.8, label='Elastoplastic Rate $\\dot{D}_z$')
    ax4.axhline(0, color='black', linestyle='-', lw=0.8)
    ax4.set_xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Rate $\\dot{D}_z$ [m/s]', fontsize=11, fontweight='bold')
    ax4.grid(True, linestyle='--', alpha=0.6)
    ax4.legend(fontsize=8.5, loc='lower left')

    plt.tight_layout()
    out_img = "elastic_vs_plastic_comparison.png"
    plt.savefig(out_img, dpi=200)
    print(f"4-Panel comparison plot saved to: {out_img}")

if __name__ == "__main__":
    main()
