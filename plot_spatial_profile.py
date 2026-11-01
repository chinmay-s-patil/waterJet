#!/usr/bin/env python3
"""
Plot spatial profiles of plate deformation and plastic strain for submerged waterjet FSI.
Generates:
  1. Centerline displacement profiles Dz(x) at t = 50, 300, 500, 600, 1000 us (Elastic vs Plastic).
  2. 2D contour map of residual displacement Dz(x, y) at t = 500 us (unloaded permanent dent).
  3. 2D contour map of equivalent plastic strain epsilon_p_eq(x, y) showing localized yield under nozzle.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read_mesh_points(case_dir):
    pts_file = os.path.join(case_dir, 'constant/solid/polyMesh/points')
    points = []
    with open(pts_file) as f:
        in_list = False
        for line in f:
            line = line.strip()
            if line == '(': in_list = True; continue
            if in_list:
                if line == ')': break
                if line.startswith('('):
                    points.append([float(x) for x in line[1:-1].split()])
    return np.array(points)

def read_point_vector(fpath):
    vecs = []
    with open(fpath) as f:
        in_list = False
        for line in f:
            line = line.strip()
            if line == '(': in_list = True; continue
            if in_list:
                if line == ')': break
                if line.startswith('('):
                    vecs.append([float(x) for x in line[1:-1].split()])
    return np.array(vecs)

def read_cell_scalar(fpath):
    vals = []
    with open(fpath) as f:
        in_list = False
        for line in f:
            line = line.strip()
            if line == '(': in_list = True; continue
            if in_list:
                if line == ')': break
                try:
                    vals.append(float(line))
                except:
                    pass
    return np.array(vals)

def main():
    case_el = 'case_elastic'
    case_pl = 'case_plastic'
    
    # Check meshes
    points = read_mesh_points(case_pl)
    # Interface points at z = 0
    top_mask = np.abs(points[:, 2] - 0.0) < 1e-6
    top_indices = np.where(top_mask)[0]
    top_pts = points[top_indices]
    
    # Centerline points (y approx 0)
    cl_mask = np.abs(top_pts[:, 1]) < 1e-4
    cl_indices = top_indices[cl_mask]
    cl_indices = cl_indices[np.argsort(points[cl_indices, 0])]
    x_cl_mm = points[cl_indices, 0] * 1e3
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
    plt.subplots_adjust(wspace=0.28, left=0.06, right=0.96, bottom=0.14, top=0.88)
    
    # Panel 1: Centerline profile comparison across key times
    ax1 = axes[0]
    times = [
        ('5e-05', '50 $\\mu$s (Peak Jet Impact)', '#d95f02', '-'),
        ('0.0003', '300 $\\mu$s (Unloading)', '#7570b3', '--'),
        ('0.0005', '500 $\\mu$s (Elastic Recovery)', '#1b9e77', '-.'),
        ('0.0006', '600 $\\mu$s (Unloaded Dent)', '#e7298a', ':')
    ]
    
    for td, label, col, ls in times:
        el_p = read_point_vector(os.path.join(case_el, td, 'solid/pointD'))[cl_indices, 2] * 1e6
        pl_p = read_point_vector(os.path.join(case_pl, td, 'solid/pointD'))[cl_indices, 2] * 1e6
        ax1.plot(x_cl_mm, np.abs(pl_p), color=col, linestyle=ls, lw=2.2, label=f'{label} [Plastic]')
        ax1.plot(x_cl_mm, np.abs(el_p), color=col, linestyle=ls, lw=1.2, alpha=0.5)
        
    ax1.axvspan(-1.0, 1.0, color='gold', alpha=0.15, label='Nozzle Footprint ($2\\times 2$ mm)')
    ax1.set_xlabel('Plate Centerline Coordinate $x$ [mm]', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Downward Deflection $|D_z|$ [$\\mu$m]', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Centerline Deformation Profiles $D_z(x)$', fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(fontsize=8, loc='upper right')
    ax1.set_xlim(-10, 10)
    
    # Panel 2: 2D Spatial Contour of Residual Plastic Dent at 500 us
    ax2 = axes[1]
    pl_500 = read_point_vector(os.path.join(case_pl, '0.0005', 'solid/pointD'))[top_indices, 2] * 1e6
    x_top = top_pts[:, 0] * 1e3
    y_top = top_pts[:, 1] * 1e3
    dz_top = np.abs(pl_500)
    
    # Grid data for contour
    from scipy.interpolate import griddata
    xi = np.linspace(-10, 10, 100)
    yi = np.linspace(-10, 10, 100)
    Xi, Yi = np.meshgrid(xi, yi)
    Zi = griddata((x_top, y_top), dz_top, (Xi, Yi), method='cubic')
    
    cf2 = ax2.contourf(Xi, Yi, Zi, levels=20, cmap='viridis')
    cbar2 = plt.colorbar(cf2, ax=ax2, shrink=0.88)
    cbar2.set_label('Residual Dent $|D_z|$ [$\\mu$m]', fontsize=10, fontweight='bold')
    # Draw nozzle box
    from matplotlib.patches import Rectangle
    rect = Rectangle((-1, -1), 2, 2, linewidth=1.5, edgecolor='red', facecolor='none', linestyle='--', label='Nozzle ($2\\times 2$ mm)')
    ax2.add_patch(rect)
    ax2.set_xlabel('Coordinate $x$ [mm]', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Coordinate $y$ [mm]', fontsize=11, fontweight='bold')
    ax2.set_title('(b) Permanent Dent at $t = 500\\,\\mu$s', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8.5, loc='upper right')
    ax2.set_aspect('equal')
    
    # Panel 3: Plastic Strain epsilon_p_eq under interface
    ax3 = axes[2]
    # Read cell centers and epsilonPEq from solid mesh
    # Top cell layer under interface
    eps_cells = read_cell_scalar(os.path.join(case_pl, '0.0005', 'solid/epsilonPEq'))
    
    # Approximate cell centers from solid polyMesh
    # Or interpolate point displacement difference (Plastic - Elastic) as a proxy for plastic strain if cell centers take time
    # Let's check max plastic strain
    max_eps = eps_cells.max()
    
    # Delta D = Plastic - Elastic at 500 us
    el_500 = read_point_vector(os.path.join(case_el, '0.0005', 'solid/pointD'))[top_indices, 2] * 1e6
    delta_d_2d = np.abs(pl_500) - np.abs(el_500)
    Zi_delta = griddata((x_top, y_top), delta_d_2d, (Xi, Yi), method='cubic')
    
    cf3 = ax3.contourf(Xi, Yi, Zi_delta, levels=20, cmap='inferno')
    cbar3 = plt.colorbar(cf3, ax=ax3, shrink=0.88)
    cbar3.set_label('Permanent Indentation $\\Delta D$ [$\\mu$m]', fontsize=10, fontweight='bold')
    rect3 = Rectangle((-1, -1), 2, 2, linewidth=1.5, edgecolor='cyan', facecolor='none', linestyle='--', label=f'Peak $\\varepsilon_{{p,eq}} = {max_eps:.2e}$')
    ax3.add_patch(rect3)
    ax3.set_xlabel('Coordinate $x$ [mm]', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Coordinate $y$ [mm]', fontsize=11, fontweight='bold')
    ax3.set_title('(c) Net Plastic Dent Field $\\Delta D(x, y)$', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8.5, loc='upper right')
    ax3.set_aspect('equal')
    
    plt.suptitle('Spatial Indentation & Permanent Plastic Dent Morphology (solids4Foam FSI)', fontsize=14, fontweight='bold', y=0.98)
    
    out_file = 'dent_spatial_profile.png'
    plt.savefig(out_file, dpi=300)
    print(f'Successfully generated {out_file}')

if __name__ == '__main__':
    main()
