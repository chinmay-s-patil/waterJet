#!/bin/bash
set -e

# ==============================================================================
# Parallel Benchmark Experiment: Purely Elastic vs Elastoplastic Copper Plate
# Parallel Decomposition: 8 cores (hierarchical 4x2x1)
# Stage 1 (0 to 40 us): Impinging jet loading at 30 m/s
# Stage 2 (40 to 45 us): Jet ramp-down to 0 m/s
# Stage 3 (45 to 1000 us): Extended hydrodynamic relaxation & static equilibrium
# Goal: Directly measure elastic springback vs permanent plastic dent retention
# ==============================================================================

BASE_CASE="submergedWaterjetFSI"
NUM_PROCS=8

# Function to configure loading-unloading time-dependent inlet
configure_unloading_inlet() {
    local target_u="$1"
    cat << 'U_EOF' > "${target_u}"
/*--------------------------------*- C++ -*----------------------------------*\
| solids4foam: solid mechanics and fluid-solid interaction simulations        |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0/fluid";
    object      U;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{
    inlet
    {
        type            uniformFixedValue;
        value           uniform (0 0 -30);
        uniformValue    table
        (
            (0.000000   (0 0 -30))
            (0.000040   (0 0 -30))
            (0.000045   (0 0 0))
            (0.001000   (0 0 0))
        );
    }

    topWall
    {
        type            fixedValue;
        value           uniform (0 0 0);
    }

    outlet
    {
        type            inletOutlet;
        inletValue      uniform (0 0 0);
        value           uniform (0 0 0);
    }

    plate
    {
        type            movingWallVelocity;
        value           uniform (0 0 0);
    }
}

// ************************************************************************* //
U_EOF
}

# Function to configure decomposeParDict (hierarchical 4 2 1 for conformal directMap)
create_decompose_dict() {
    local target_file="$1"
    cat << 'DEC_EOF' > "${target_file}"
/*--------------------------------*- C++ -*----------------------------------*\
| solids4foam: solid mechanics and fluid-solid interaction simulations        |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      decomposeParDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

numberOfSubdomains 8;

method          hierarchical;

hierarchicalCoeffs
{
    n           (4 2 1);
    delta       0.001;
    order       xyz;
}

// ************************************************************************* //
DEC_EOF
}

# Function to set extended simulation duration (1000 us = 1e-3 s) and per-step monitoring
configure_extended_duration() {
    local case_dir="$1"
    sed -i 's/^endTime\s\+[0-9.eE+-]\+;/endTime         1e-03;/' "${case_dir}/system/controlDict"
    sed -i 's/^writeInterval\s\+[0-9]\+;/writeInterval   25;/' "${case_dir}/system/controlDict"
    
    # Ensure all functionObjects write every timeStep
    sed -i '/centerPlateDisplacement/,/}/ s/writeInterval\s\+[0-9]\+;/writeInterval       1;/' "${case_dir}/system/controlDict"
    sed -i '/interfaceForces/,/}/ s/writeInterval\s\+[0-9]\+;/writeInterval       1;/' "${case_dir}/system/controlDict"
    sed -i '/fluidMeanVelocity/,/}/ s/writeInterval\s\+[0-9]\+;/writeInterval       1;/' "${case_dir}/system/controlDict"
}

echo "=========================================================="
echo " Setting up Case A: Purely Elastic Copper (linearElastic) "
echo " Running on ${NUM_PROCS} cores in parallel (1000 us duration)     "
echo "=========================================================="
rm -rf case_elastic
cp -r "${BASE_CASE}" case_elastic
cd case_elastic
./Allclean

# 1. Configure loading-unloading inlet & 1000 us duration
configure_unloading_inlet "0/fluid/U"
configure_unloading_inlet "0.orig/fluid/U"
configure_extended_duration "."

# 2. Configure decomposition dictionaries
create_decompose_dict "system/decomposeParDict"
create_decompose_dict "system/fluid/decomposeParDict"
create_decompose_dict "system/solid/decomposeParDict"

# 3. Configure purely linear elastic copper material
cat << 'MEC_EOF' > constant/solid/mechanicalProperties
/*--------------------------------*- C++ -*----------------------------------*\
| solids4foam: solid mechanics and fluid-solid interaction simulations        |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant/solid";
    object      mechanicalProperties;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

planeStress     no;

mechanical
(
    copper
    {
        type            linearElastic;
        rho             rho [1 -3 0 0 0 0 0] 8960;
        E               E [1 -1 -2 0 0 0 0] 110e9;
        nu              nu [0 0 0 0 0 0 0] 0.34;
    }
);

// ************************************************************************* //
MEC_EOF
cp constant/solid/mechanicalProperties constant/mechanicalProperties

echo "Step 1: Meshing Case A..."
blockMesh -region solid > log.blockMeshSolid 2>&1
blockMesh -region fluid > log.blockMeshFluid 2>&1
setFields -region fluid > log.setFieldsFluid 2>&1

echo "Step 2: Decomposing regions into ${NUM_PROCS} subdomains..."
decomposePar -region solid > log.decomposeSolid 2>&1
decomposePar -region fluid > log.decomposeFluid 2>&1

echo "Step 3: Running solids4Foam on ${NUM_PROCS} cores..."
mpirun -np ${NUM_PROCS} solids4Foam -parallel > log.solids4Foam 2>&1

echo "Step 4: Reconstructing domain..."
reconstructPar -region solid > log.reconstructSolid 2>&1 || true
reconstructPar -region fluid > log.reconstructFluid 2>&1 || true
cd ..
echo ">>> Case A completed successfully!"

echo "=========================================================="
echo " Setting up Case B: Elastoplastic Copper (Mises Plastic)  "
echo " Running on ${NUM_PROCS} cores in parallel (1000 us duration)    "
echo "=========================================================="
rm -rf case_plastic
cp -r "${BASE_CASE}" case_plastic
cd case_plastic
./Allclean

# 1. Configure loading-unloading inlet & 1000 us duration
configure_unloading_inlet "0/fluid/U"
configure_unloading_inlet "0.orig/fluid/U"
configure_extended_duration "."

# 2. Configure decomposition dictionaries
create_decompose_dict "system/decomposeParDict"
create_decompose_dict "system/fluid/decomposeParDict"
create_decompose_dict "system/solid/decomposeParDict"

echo "Step 1: Meshing Case B..."
blockMesh -region solid > log.blockMeshSolid 2>&1
blockMesh -region fluid > log.blockMeshFluid 2>&1
setFields -region fluid > log.setFieldsFluid 2>&1

echo "Step 2: Decomposing regions into ${NUM_PROCS} subdomains..."
decomposePar -region solid > log.decomposeSolid 2>&1
decomposePar -region fluid > log.decomposeFluid 2>&1

echo "Step 3: Running solids4Foam on ${NUM_PROCS} cores..."
mpirun -np ${NUM_PROCS} solids4Foam -parallel > log.solids4Foam 2>&1

echo "Step 4: Reconstructing domain..."
reconstructPar -region solid > log.reconstructSolid 2>&1 || true
reconstructPar -region fluid > log.reconstructFluid 2>&1 || true
cd ..
echo ">>> Case B completed successfully!"

# Run comparison and springback evaluation
python3 compare_elastic_plastic.py
