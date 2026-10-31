#!/bin/bash
set -e

# ==============================================================================
# Benchmark Experiment: Purely Elastic vs Elastoplastic Copper Plate
# Goal: Prove permanent indentation retention vs elastic springback
# ==============================================================================

BASE_CASE="submergedWaterjetFSI"

echo "=========================================================="
echo " Setting up Case A: Purely Elastic Copper (linearElastic) "
echo "=========================================================="
rm -rf case_elastic
cp -r "${BASE_CASE}" case_elastic
cd case_elastic
./Allclean

# Configure purely linear elastic copper material
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
echo "=========================================================="
rm -rf case_plastic
cp -r "${BASE_CASE}" case_plastic
cd case_plastic
./Allclean
echo "Meshing and running Case B (Elastoplastic)..."
blockMesh -region solid > log.blockMeshSolid 2>&1
blockMesh -region fluid > log.blockMeshFluid 2>&1
setFields -region fluid > log.setFieldsFluid 2>&1
solids4Foam > log.solids4Foam 2>&1
cd ..
echo ">>> Case B completed."

# Run comparison script
python3 compare_elastic_plastic.py
