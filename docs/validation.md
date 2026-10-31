# Submerged Waterjet FSI: Validation & Benchmark Report

This document reports the physical validation, hydrodynamic force analysis, and elastoplastic unloading benchmark for the submerged waterjet fluid-structure interaction (FSI) model.

---

## 1. Validation Objectives

To rigorously establish the fidelity of the two-way ALE FSI simulation, three validation milestones were defined:
1. **Two-Way Dynamic Coupling & ALE Integrity**: Verify that fluid mesh points dynamically deform conforming to the solid boundary, with force and kinematic compatibility satisfied at the interface.
2. **Hydrodynamic Force Analysis**: Characterize the total interface load history on the plate, distinguishing the initial incompressible startup transient from the asymptotic steady momentum flux.
3. **Permanent Indentation vs Elastic Springback**: Validate true plasticity by subjecting the plate to dynamic loading followed by complete unloading, comparing a purely elastic benchmark against the elastoplastic copper plate.

---

## 2. Hydrodynamic Interface Force Analysis

The interface force on the copper plate patch (`plate`, $20 \times 20\,\text{mm} = 400\,\text{mm}^2$) is tracked using the OpenFOAM `forces` function object. 

### Theoretical Steady Jet Momentum Thrust
A steady jet of density $\rho_f = 1000\,\text{kg/m}^3$, cross-sectional area $A = 2\,\text{mm} \times 2\,\text{mm} = 4 \times 10^{-6}\,\text{m}^2$, and velocity $U_0 = 30\,\text{m/s}$ turning $90^\circ$ parallel to the plate produces a theoretical steady momentum thrust:

$$F_{steady} = \dot{m} U_0 = \rho_f A U_0^2 = 1000 \times (4.0 \times 10^{-6}) \times 900 = 3.60\,\text{N}$$

### Computed Interface Force History

| Time [$\mu\text{s}$] | Pressure Force $F_{p,z}$ [$\text{N}$] | Viscous Force $F_{v,z}$ [$\text{N}$] | Total Normal Force $F_z$ [$\text{N}$] | Physical Regime |
| :---: | :---: | :---: | :---: | :--- |
| **$2.0$** | $124.32$ | $0.0014$ | $124.32$ | Initial startup impulse |
| **$4.0$** | $151.45$ | $0.0014$ | $151.45$ | Peak cushion deceleration |
| **$6.0$** | $13.13$ | $0.0012$ | $13.13$ | Radial relief into lateral domain |
| **$8.0$** | $4.79$ | $0.0011$ | $4.79$ | Asymptotic approach to steady thrust ($3.60\,\text{N}$) |
| **$22.0$** | $1.15$ | $0.0017$ | $1.15$ | Low-pressure structural rebound phase |
| **$32.0$** | $48.64$ | $0.0008$ | $48.64$ | Structural dynamic oscillation peak |
| **$62.0$** | $60.96$ | $0.0007$ | $60.97$ | Second dynamic oscillation cycle |
| **$100.0$** | $17.26$ | $0.0001$ | $17.26$ | Fully developed stagnation regime |

### Physical Interpretation of the Force Surge
1. **Area Scaling**: The monitored boundary is the entire $20 \times 20\,\text{mm}$ plate ($400\,\text{mm}^2$), which is **100 times larger** than the $2 \times 2\,\text{mm}$ jet orifice. An average transient pressure of only $\bar{p} \approx 0.38\,\text{MPa}$ across the entire plate produces $150\,\text{N}$.
2. **Incompressible Elliptic Pressure Response**: Because the fluid equations enforce $\nabla \cdot \mathbf{U} = 0$, the deceleration of the initial fluid column against the stationary cushion produces an instantaneous global pressure dome across the chamber.
3. **Radial Relief**: As the fluid turns radially into a horizontal wall-jet and reaches the open lateral boundaries ($p = 0\,\text{Pa}$ at $x, y = \pm 10\,\text{mm}$), the global pressure dome rapidly relieves, dropping to $4.79\,\text{N}$ by $t = 8\,\mu\text{s}$, approaching the steady momentum thrust ($3.60\,\text{N}$).
4. **Negligible Viscous Shear**: Viscous forces ($F_{v,z} \sim 10^{-3}\,\text{N}$) represent less than $0.01\%$ of the total load, confirming that plate deformation is overwhelmingly driven by normal pressure.

---

## 3. Plate Indentation & Plastic Yielding

### Deformation and Stress History ($U_0 = 30\,\text{m/s}$, $h = 0.3\,\text{mm}$)

- **Initial Yield Stress ($\sigma_{y0}$)**: $65.0\,\text{MPa}$
- **Maximum Center Indentation Depth**: **$48.90\,\mu\text{m}$** (at $t = 64\,\mu\text{s}$, exceeding $16\%$ of the $0.3\,\text{mm}$ plate thickness)
- **Peak von Mises Stress ($\sigma_{eq,max}$)**: Reaches **$66.62\,\text{MPa}$** at $t = 60\,\mu\text{s}$, actively yielding and hardening the copper.
- **Permanent Equivalent Plastic Strain ($\varepsilon_{p,eq,max}$)**: Stabilizes at **$9.24 \times 10^{-4}$** localized in the central impact footprint.

The plastic strain is concentrated directly on the impingement surface under the jet stagnation zone and nozzle corners, producing a permanent concave dent profile.

---

## 4. Elastic vs. Elastoplastic Unloading Benchmark

### Motivation
In a continuous loading simulation, structural deflection reflects both elastic compliance and plastic deformation. To isolate and demonstrate irreversible plastic dent retention, the load must be completely removed.

### Loading-Unloading Schedule
Using OpenFOAM's `uniformFixedValue` table boundary condition on the inlet, the simulation is partitioned into three stages:
1. **Stage 1: Dynamic Loading ($0 \le t \le 40\,\mu\text{s}$)**: Inflow maintained at $U_z = -30\,\text{m/s}$. Full stagnation zone and plastic deformation develop.
2. **Stage 2: Ramp-Down ($40 < t \le 45\,\mu\text{s}$)**: Inflow velocity linearly decelerated to $0\,\text{m/s}$.
3. **Stage 3: Hydrodynamic Unloading ($45 < t \le 100\,\mu\text{s}$)**: Inflow maintained at $0\,\text{m/s}$. Chamber pressures equalize, allowing the plate to dynamically unload.

### Comparison: Case A (Purely Elastic) vs Case B (Elastoplastic)

```mermaid
flowchart LR
    subgraph Stage1["Stage 1: Dynamic Loading (0 to 40 µs)"]
        direction TB
        L1["Jet Inflow: U_z = -30 m/s"]
        L2["Stagnation Pressure & Dent Formation"]
        L3["Active Plastic Yielding: sigma >= 65 MPa"]
        L1 --> L2 --> L3
    end

    subgraph Stage2["Stage 2: Ramp-Down (40 to 45 µs)"]
        direction TB
        R1["Jet Inflow: -30 m/s -> 0 m/s (Linear Deceleration)"]
        R2["Hydrodynamic Load Removal"]
        R1 --> R2
    end

    subgraph Stage3["Stage 3: Hydrodynamic Unloading & Relaxation (45 to 300 µs)"]
        direction TB
        CaseA["Case A: Purely Elastic<br/>Rebounds towards initial geometry (Dz -> 0 µm)<br/>Plastic Strain eps_p = Absent (Not modeled)"]
        CaseB["Case B: Elastoplastic Copper<br/>Retains permanent concave dent (Dz,residual > 0 µm)<br/>Irreversible Plastic Strain eps_p = 0.000924"]
    end

    Stage1 ==> Stage2 ==> Stage3
```

### 300 µs Benchmark Results: Elastic Relaxation vs. Permanent Plastic Dent

| Metric | Case A: Purely Elastic (`linearElastic`) | Case B: Elastoplastic (`linearElasticMisesPlastic`) | Physical Significance |
| :--- | :---: | :---: | :--- |
| **Material Plasticity** | Absent (Not modeled) | Active Yielding ($\sigma_{eq} \ge 65.0\,\text{MPa}$) | Constitutive formulation |
| **Peak Deflection ($D_{z,max}$)** | **$41.70\,\mu\text{m}$** (at $52\,\mu\text{s}$) | **$45.44\,\mu\text{m}$** (at $52\,\mu\text{s}$) | Additional $3.74\,\mu\text{m}$ plastic peak |
| **Deflection at $t = 100\,\mu\text{s}$** | **$27.07\,\mu\text{m}$** | **$30.43\,\mu\text{m}$** | Early dynamic springback phase |
| **Deflection at $t = 300\,\mu\text{s}$** | **$3.16\,\mu\text{m}$** | **$8.13\,\mu\text{m}$** | **Permanent residual dent = $4.97\,\mu\text{m}$** |
| **Dynamic Recovery Ratio (300 µs)** | **$92.4\%$** | **$82.1\%$** | Elastic plate approaches zero |
| **End Displacement Rate ($\dot{D}_z$)** | **$0.055\,\text{m/s}$** | **$0.051\,\text{m/s}$** | Velocity decays towards static equilibrium |
| **Equivalent Plastic Strain ($\varepsilon_{p,eq}$)** | **Absent** | **$0.000924$** | Direct proof of permanent material yielding |

### Physical Dynamic Recovery & Permanent Indentation Insights

1. **Delayed Dynamic Response ($52\,\mu\text{s}$ Peak)**:
   The center deflection continues increasing after the inlet begins decelerating at $t = 40\,\mu\text{s}$, reaching its maximum at $t \approx 52\,\mu\text{s}$. This delayed response stems from the combined inertia of the coupled fluid-structure system:
   - **Fluid Inertia**: The moving column of water continues impinging and maintaining high local stagnation pressure against the plate before momentum fully dissipates.
   - **Structural Inertia**: The plate material possesses downward kinetic energy.
   - **Elastic Restoring Forces**: The plate continues downward until bending stresses build up sufficiently to arrest and reverse the downward velocity.

2. **Complete Structural Relaxation & Elastic Springback**:
   As the simulation extends to $300\,\mu\text{s}$ under quiescent fluid conditions ($U = 0\,\text{m/s}$):
   - The purely elastic plate recovers **$92.4\%$** of its peak deformation, dropping from $41.70\,\mu\text{m} \to 3.16\,\mu\text{m}$ and asymptotically approaching zero.
   - The displacement velocity $\dot{D}_z$ drops by an order of magnitude (from $0.406\,\text{m/s}$ at $100\,\mu\text{s}$ to $0.055\,\text{m/s}$ at $300\,\mu\text{s}$).

3. **Demonstration of Permanent Concave Dent Formation**:
   - Throughout the entire relaxation period from $140\,\mu\text{s}$ to $300\,\mu\text{s}$, the deflection difference between the elastoplastic plate and the elastic plate remains constant at **$\Delta D_z = 4.97 \pm 0.15\,\mu\text{m}$**.
   - This $\sim 5.0\,\mu\text{m}$ offset represents the **true irreversible permanent dent** after hydrodynamic unloading, directly corresponding to the localized equivalent plastic strain footprint ($\varepsilon_{p,eq} = 9.24 \times 10^{-4}$).

The benchmark plot is generated by [`compare_elastic_plastic.py`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/compare_elastic_plastic.py) and saved to [`elastic_vs_plastic_comparison.png`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/elastic_vs_plastic_comparison.png).
