#!/bin/bash
set -e

# ==============================================================================
# Benchmark Experiment: Purely Elastic vs Elastoplastic Dynamic Unloading
# Stage 1 (0 to 40 us): Impinging jet loading at 30 m/s
# Stage 2 (40 to 45 us): Jet ramp-down to 0 m/s
# Stage 3 (45 to 300 us): Complete shut-off and hydrodynamic unloading / relaxation
# Goal: Directly measure elastic springback vs permanent plastic dent retention
# ==============================================================================

BASE_CASE="submergedWaterjetFSI"

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
            (0.000300   (0 0 0))
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

# Function to set extended simulation duration (300 us)
configure_extended_duration() {
    local case_dir="$1"
    sed -i 's/endTime\s\+[0-9.eE+-]\+;/endTime         3e-04;/' "${case_dir}/system/controlDict"
    sed -i 's/writeInterval\s\+[0-9]\+;/writeInterval   10;/' "${case_dir}/system/controlDict"
}

echo "=========================================================="
echo " Setting up Case A: Purely Elastic Copper (linearElastic) "
echo " Duration: 300 us (Loading 0-40us, Ramp 40-45us, Unload 45-300us)"
echo "=========================================================="
rm -rf case_elastic
cp -r "${BASE_CASE}" case_elastic
cd case_elastic
./Allclean

# 1. Configure loading-unloading inlet & 300 us duration
configure_unloading_inlet "0/fluid/U"
configure_unloading_inlet "0.orig/fluid/U"
configure_extended_duration "."

# 2. Configure purely linear elastic copper material
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

echo "Meshing and running Case A (Elastic)..."
blockMesh -region solid > log.blockMeshSolid 2>&1
blockMesh -region fluid > log.blockMeshFluid 2>&1
setFields -region fluid > log.setFieldsFluid 2>&1
solids4Foam > log.solids4Foam 2>&1
cd ..
echo ">>> Case A completed."

echo "=========================================================="
echo " Setting up Case B: Elastoplastic Copper (Mises Plastic)  "
echo " Duration: 300 us (Loading 0-40us, Ramp 40-45us, Unload 45-300us)"
echo "=========================================================="
rm -rf case_plastic
cp -r "${BASE_CASE}" case_plastic
cd case_plastic
./Allclean

# 1. Configure loading-unloading inlet & 300 us duration
configure_unloading_inlet "0/fluid/U"
configure_unloading_inlet "0.orig/fluid/U"
configure_extended_duration "."

echo "Meshing and running Case B (Elastoplastic)..."
blockMesh -region solid > log.blockMeshSolid 2>&1
blockMesh -region fluid > log.blockMeshFluid 2>&1
setFields -region fluid > log.setFieldsFluid 2>&1
solids4Foam > log.solids4Foam 2>&1
cd ..
echo ">>> Case B completed."

# Run comparison and springback evaluation
python3 compare_elastic_plastic.py
