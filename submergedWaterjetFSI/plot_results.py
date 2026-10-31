#!/usr/bin/env python3
"""
Post-processing script to extract and plot:
1. Center plate indentation depth (Dz) vs time
2. Dynamic displacement history
"""

import sys
import os
import glob
import numpy as np

def main():
    disp_file = "postProcessing/0/solidPointDisplacement_centerPlateDisplacement.dat"
    if not os.path.exists(disp_file):
        # Look in postProcessing subdirs
        candidates = glob.glob("postProcessing/*/solidPointDisplacement_centerPlateDisplacement.dat")
        if candidates:
            disp_file = candidates[0]
        else:
            print(f"Error: {disp_file} not found.")
            return

    times = []
    dz = []
    with open(disp_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0])
                    # Dz is the downward deflection in meters
                    # Convert to micrometers (um) for convenient visualization
                    defl_um = -float(parts[3]) * 1e6
                    times.append(t * 1e3) # ms
                    dz.append(defl_um)
                except ValueError:
                    continue

    print("==========================================================")
    print(" Submerged Continuous Waterjet Impinging on Copper Plate  ")
    print(" Indentation Depth History Summary                        ")
    print("==========================================================")
    if times:
        print(f"Total time steps recorded: {len(times)}")
        print(f"Initial time: {times[0]:.4f} ms | Initial depth: {dz[0]:.4f} um")
        print(f"Latest time:  {times[-1]:.4f} ms | Latest depth:  {dz[-1]:.4f} um")
        print(f"Maximum dent depth: {max(dz):.4f} um")
        print("----------------------------------------------------------")
        print(f"{'Time [ms]':>12} | {'Dent Depth [um]':>16}")
        print("----------------------------------------------------------")
        for t, d in zip(times, dz):
            print(f"{t:12.4f} | {d:16.4f}")
        print("==========================================================")

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(8, 5))
            plt.plot(times, dz, 'b-o', lw=2, markersize=5, label='Indentation Depth (center)')
            plt.xlabel('Simulation Time [ms]', fontsize=12)
            plt.ylabel('Dent Depth [$\\mu$m]', fontsize=12)
            plt.title('Submerged Waterjet Impact on Copper Plate: Indentation vs Time', fontsize=13)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend(fontsize=11)
            plt.tight_layout()
            out_img = "indentation_vs_time.png"
            plt.savefig(out_img, dpi=200)
            print(f"Plot successfully saved to: {out_img}")
        except ImportError:
            print("matplotlib not available for direct PNG plotting, table printed above.")
    else:
        print("No displacement data recorded yet.")

if __name__ == "__main__":
    main()
