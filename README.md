# Submerged Waterjet Elastoplastic Fluid-Structure Interaction (FSI)

[![OpenFOAM](https://img.shields.io/badge/OpenFOAM-v2412-blue.svg)](https://openfoam.com)
[![solids4foam](https://img.shields.io/badge/solids4Foam-FSI-green.svg)](https://solids4foam.github.io)
[![License](https://img.shields.io/badge/License-GPLv3-orange.svg)](LICENSE)

A validated two-way coupled fluid-structure interaction (FSI) model of a submerged continuous high-speed micro-waterjet impinging on an elastoplastic copper plate with permanent concave dent formation.

Built with **`solids4Foam`** in **OpenFOAM v2412**.

---

## 📌 Repository Architecture & Documentation

```
waterJet/
├── submergedWaterjetFSI/             # Primary 100-µs coupled FSI case
│   ├── 0.orig/                      # Clean initial field templates
│   ├── constant/                    # Fluid, solid, and FSI coupling dictionaries
│   │   ├── fluid/                   # Transport & turbulence models
│   │   ├── solid/                   # Copper mechanicalProperties & hardening curve
│   │   └── fsiProperties            # Aitken relaxation & directMap settings
│   ├── system/                      # Solvers, schemes, and controlDict (forces monitor)
│   ├── Allrun                       # Meshes, initializes, runs, and plots
│   ├── Allclean                     # Resets case and cleans generated fields
│   └── plot_results.py              # Generates indentation and hydrodynamic force plots
├── docs/                            # In-depth technical documentation
│   ├── implementation.md            # Mesh topology, boundary conditions, copper card
│   ├── numerical-methods.md         # ALE FSI coupling, Aitken relaxation, pressure physics
│   └── validation.md                # Force analysis, springback vs permanent dent
├── runElasticVsPlasticUnloading.sh   # 8-core parallel dynamic unloading benchmark
├── compare_elastic_plastic.py       # Comparative evaluator for unloading springback
├── plot_spatial_profile.py          # Spatial dent morphology & 2D indentation mapper
└── README.md                        # Project landing page and execution instructions
```

For comprehensive technical derivations and mathematical background, refer to:
- 📖 [**Implementation Guide**](docs/implementation.md): Complete geometry, structured multi-block conformal meshing, ALE patch definitions, and material constitutive modeling.
- 📐 [**Numerical Methods & Theory**](docs/numerical-methods.md): Partitioned Dirichlet-Neumann coupling, Aitken dynamic under-relaxation, `directMap` conservative transfer, and incompressible Navier-Stokes elliptic pressure physics vs acoustic wave propagation.
- 📊 [**Validation & Benchmark Report**](docs/validation.md): Detailed hydrodynamic force history, startup pressure transient breakdown, asymptotic momentum flux, and the elastic vs elastoplastic dynamic unloading benchmark.

---

## 🚀 Quickstart

### Prerequisites
- **OpenFOAM v2412**
- **solids4Foam** (compiled and sourced in your OpenFOAM environment)
- **Python 3** with `numpy` and `matplotlib`

### 1. Run the Primary FSI Simulation (100 µs)
To mesh, initialize, execute, and generate diagnostic plots for the baseline 100-µs simulation:
```bash
cd submergedWaterjetFSI
./Allrun
```
*(Optional: Pass a custom jet velocity, e.g., `./Allrun 40` to run at 40 m/s).*

### 2. Run the Dynamic Unloading Benchmark (Springback vs. Permanent Dent)
To run Case A (purely linear elastic) versus Case B (elastoplastic copper) through a dynamic 40 µs load / 60 µs unload cycle:
```bash
./runElasticVsPlasticUnloading.sh
```
This automatically produces `elastic_vs_plastic_comparison.png` and prints a summary comparing maximum deflection, residual dent, elastic springback percentage, and final plastic strain.

---

## 🔬 Key Physical & Numerical Highlights

1. **Two-Way Conformal ALE Coupling**:
   - Structured $3 \times 3$ multi-block meshes with refined $16 \times 16$ central core.
   - Exact 1-to-1 face alignment ($1{,}936$ quad faces) between fluid patch `plate` and solid patch `interface`, enabling conservative, non-dissipative `directMap` transfer.
   - True ALE mesh motion verified: fluid grid points dynamically displace conforming to plate deflection.

2. **Incompressible Elliptic Pressure Physics**:
   - The initial force surge ($\approx 120 - 150\,\text{N}$ at $t = 2-4\,\mu\text{s}$) is an elliptic pressure projection of decelerating the initialized fluid column across the entire $20 \times 20\,\text{mm}$ plate ($400\,\text{mm}^2$, $100\times$ nozzle orifice).
   - As fluid spreads radially into a lateral wall-jet, the force relieves rapidly ($4.79\,\text{N}$ at $t = 8\,\mu\text{s}$), asymptotically approaching the theoretical steady jet momentum thrust:
     $$F_{steady} = \rho_f A_{nozzle} U_0^2 = 1000 \times (4.0 \times 10^{-6}) \times (30)^2 = 3.60\,\text{N}$$

3. **Demonstrated Plastic Denting**:
   - Annealed ETP copper ($\sigma_{y0} = 65\,\text{MPa}$, $E = 110\,\text{GPa}$) yields under jet impingement.
   - At $t = 10\,\mu\text{s}$, center dent depth reaches $30.18\,\mu\text{m}$ ($> 10\%$ plate thickness) with equivalent plastic strain $\varepsilon_{p,eq} \approx 9.24 \times 10^{-4}$.
   - Dynamic unloading confirms permanent plastic indentation retention in contrast to purely elastic springback.
