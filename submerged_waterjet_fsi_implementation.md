All corrections and enhancements requested in your audit have been implemented, tested, and pushed directly to the **main** branch of [chinmay-s-patil/waterJet](https://github.com/chinmay-s-patil/waterJet) ([commit `69fc75f`](https://github.com/chinmay-s-patil/waterJet/commit/69fc75f)).

---

### Summary of Fixes & Enhancements

#### 1. Simulation Duration & Control Settings ([`submergedWaterjetFSI/system/controlDict`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/submergedWaterjetFSI/system/controlDict))

- **`endTime`**: Changed from `4e-06` to **`1e-04`** ($100\,\mu\text{s}$, giving 50 time steps at $\Delta t = 2\,\mu\text{s}$). With the $0.2\,\text{mm}$ cushion ($t_{transit} \approx 6.67\,\mu\text{s}$), the simulation now captures the full impact and developed stagnation flow.
- **`writeInterval`**: Configured to **`5`** (writes every $10\,\mu\text{s}$, producing 10 full state outputs).
- **Corrected comments** and cleaned dictionary formatting.

#### 2. `Allrun` Parameter Substitution Bug ([`submergedWaterjetFSI/Allrun`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/submergedWaterjetFSI/Allrun))

- Fixed the `${VEL}` typo so `${JET_VEL}` is used uniformly across both `0/fluid/U` and `system/fluid/setFieldsDict`.
- Added consistency grep checks immediately following the substitutions to verify that the inlet BC and `setFieldsDict` velocity agree before the solver starts.

#### 3. Investigation of the 309.4 N Interface Force

- **Area Ratio**: The FSI `plate` patch is the **entire $20 \times 20\,\text{mm}$ plate** ($A = 400\,\text{mm}^2$), which is **100 times larger** than the $2 \times 2\,\text{mm}$ nozzle orifice ($A = 4\,\text{mm}^2$).
- **Incompressible Startup Pulse**: At $t = 0$, decelerating the $5.8\,\text{mm}$ moving water column ($m \approx 2.32 \times 10^{-5}\,\text{kg}$) into the stagnant cushion within $\Delta t = 2\,\mu\text{s}$ creates an initial inertial pressure spike:
  $$
  F_{inertia} \approx m \frac{\Delta U}{\Delta t} \approx 348\,\text{N}
  $$

  Distributed across the $400\,\text{mm}^2$ plate, this represents an average transient pressure $\bar{p} \approx 0.77\,\text{MPa}$.
- **Transient Decay**: In the log, this global force rapidly drops from **$309.4\,\text{N}$** at $t = 2\,\mu\text{s}$ to **$139.6\,\text{N}$** at $t = 4\,\mu\text{s}$ as relief waves propagate to the lateral outlets ($p = 0$). As the steady wall-jet establishes, the net force approaches the theoretical momentum thrust ($F \approx 3.60\,\text{N}$ for square nozzle; $2.83\,\text{N}$ for circular).
- **Forces Monitor Added**: Configured the OpenFOAM `forces` function object in `system/controlDict` on the `plate` patch to log continuous pressure, viscous, and total force histories into `postProcessing/fluid/forces/0/forces.dat`.

#### 4. Nozzle Geometry Alignment (`boxToCell`)

- Switched `cylinderToCell` to **`boxToCell`** in [`system/fluid/setFieldsDict`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/submergedWaterjetFSI/system/fluid/setFieldsDict):
  ```openfoam
  box (-0.001001 -0.001001 0.0002) (0.001001 0.001001 0.006001);
  ```

  This eliminates corner shear mismatches between the $2 \times 2\,\text{mm}$ square block inlet and the initialized velocity field.

#### 5. 3-Panel Diagnostics & Robust Parsing ([`plot_results.py`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/submergedWaterjetFSI/plot_results.py))

- **3 Panels**:
  1. Center downward indentation depth $D_z(t)$ [$\mu\text{m}$].
  2. Peak von Mises stress $\sigma_{eq,max}(t)$ [$\text{MPa}$] compared against $\sigma_{y0} = 65\,\text{MPa}$.
  3. Peak equivalent plastic strain $\varepsilon_{p,eq,max}(t)$ [-].
- **Data Integrity**: `parse_scalar_field()` now returns `None` (flagged as `[MISSING]` in tables) if a field file does not exist, preventing unwritten fields from being masked as zero.

#### 6. Elastic vs. Elastoplastic Unloading Benchmark

- Created [`runElasticVsPlasticUnloading.sh`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/runElasticVsPlasticUnloading.sh) and [`compare_elastic_plastic.py`](file:///home/lavender/OpenFoamUbu/solvers/waterJet/compare_elastic_plastic.py) to run Case A (`linearElastic`) and Case B (`linearElasticMisesPlastic`) under identical loading, plotting the springback of Case A versus the permanent dent retention of Case B on a single comparison chart.

---

Full technical derivations and updated Mermaid workflows are documented in:
👉 **[`submerged_waterjet_fsi_implementation.md`](file:///home/lavender/.gemini/antigravity/brain/e477122c-0c75-4cf7-b0e4-f3c749159d4f/submerged_waterjet_fsi_implementation.md)**
