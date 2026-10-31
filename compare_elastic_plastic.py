#!/usr/bin/env python3
"""
Comparison script for Case A (Purely Elastic) vs Case B (Elastoplastic).
Plots overlay of indentation depth Dz(t) and residual permanent dent.
"""

import sys
import os
import glob
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
                    defl = -float(parts[3]) * 1e6 # um
                    times.append(t)
                    dz_um.append(defl)
                except ValueError:
                    continue
    return times, dz_um

def main():
    case_elastic = "case_elastic"
    case_plastic = "case_plastic"

    t_el, d_el = read_displacement(case_elastic)
    t_pl, d_pl = read_displacement(case_plastic)

    if not t_el and not t_pl:
        print("Notice: No displacement data found in case_elastic or case_plastic yet.")
        return

    print("==========================================================================")
    print(" Elastic vs Elastoplastic Copper Plate Unloading Comparison               ")
    print("==========================================================================")
    if t_el:
        print(f"Case A (Elastic)       - Max Deflection: {max(d_el):.4f} um | Final: {d_el[-1]:.4f} um")
    if t_pl:
        print(f"Case B (Elastoplastic) - Max Deflection: {max(d_pl):.4f} um | Final: {d_pl[-1]:.4f} um (Residual Dent)")
    print("--------------------------------------------------------------------------")

    plt.figure(figsize=(9, 5.5))
    if t_el:
        plt.plot(t_el, d_el, 'b--', lw=2, label='Case A: Purely Elastic Copper (Springback)')
    if t_pl:
        plt.plot(t_pl, d_pl, 'r-', lw=2.5, label='Case B: Elastoplastic Copper (Permanent Dent)')

    plt.axhline(0, color='gray', linestyle=':', lw=1)
    plt.xlabel('Simulation Time [$\\mu$s]', fontsize=11, fontweight='bold')
    plt.ylabel('Center Deflection $D_z$ [$\\mu$m]', fontsize=11, fontweight='bold')
    plt.title('Benchmark: Purely Elastic vs Elastoplastic Dynamic Unloading', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    out_img = "elastic_vs_plastic_comparison.png"
    plt.savefig(out_img, dpi=200)
    print(f"Comparison plot saved to: {out_img}")

if __name__ == "__main__":
    main()
