#!/bin/bash
set -e

# ==============================================================================
# Parameter Study Runner: Submerged Continuous Waterjet on Copper Plate
# Velocities: 30 m/s (baseline), 50 m/s, 100 m/s
# ==============================================================================

VELOCITIES=(30 50 100)
BASE_CASE="submergedWaterjetFSI"

echo "=========================================================="
echo " Starting Parameter Study: 30 m/s, 50 m/s, 100 m/s        "
echo "=========================================================="

for VEL in "${VELOCITIES[@]}"; do
    CASE_DIR="study_vel_${VEL}ms"
    echo ""
    echo ">>> Setting up and running case for U = ${VEL} m/s in ${CASE_DIR}..."
    
    # Clean previous run if exists
    rm -rf "${CASE_DIR}"
    cp -r "${BASE_CASE}" "${CASE_DIR}"
    
    cd "${CASE_DIR}"
    ./Allclean
    
    # Configure inlet velocity and setFields velocity
    sed -i "s/uniform (0 0 -[0-9.]\+)/uniform (0 0 -${VEL})/" 0/fluid/U
    sed -i "s/volVectorFieldValue U (0 0 -[0-9.]\+)/volVectorFieldValue U (0 0 -${VEL})/" system/fluid/setFieldsDict
    sed -i "s/volVectorFieldValue U (0 0 -[0-9.]\+)/volVectorFieldValue U (0 0 -${VEL})/" system/setFieldsDict
    
    # Run meshing, setFields, and solver
    blockMesh -region solid > log.blockMeshSolid 2>&1
    blockMesh -region fluid > log.blockMeshFluid 2>&1
    setFields -region fluid > log.setFieldsFluid 2>&1
    
    echo "    Running solids4Foam for ${VEL} m/s..."
    solids4Foam > log.solids4Foam 2>&1
    
    python3 plot_results.py || true
    cd ..
    
    echo ">>> Completed case for U = ${VEL} m/s!"
done

echo ""
echo "=========================================================="
echo " Parameter Study Finished!                                "
echo " Compare results across: study_vel_30ms, study_vel_50ms, study_vel_100ms"
echo "=========================================================="
