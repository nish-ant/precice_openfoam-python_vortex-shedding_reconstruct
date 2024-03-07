#!/bin/bash
set -e # -u

#- Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--nprocs) nprocs="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

unset LD_LIBRARY_PATH

#- Set environment variables
source /gpfs/home/nkumar001/.bash_profile
module purge
module load gcc/7.3.0
#
module load Openblas/0.3.6
module load hdf5/1.10.5/openmpi_4.0.2/gcc_7.3.0
#
source /gpfs/home/nkumar001/tools/spack/share/spack/setup-env.sh
spack env activate preciceFoam 
#
export OPENFAST_DIR=/gpfs/home/$USER/tools/OpenFAST/install
export HDF5_DIR=/gpfs/softs/contrib/apps/hdf5/1.10.5
export BLASLIB="/gpfs/softs/contrib/apps/Openblas/0.3.6/lib -lopenblas"
#
export SOWFA_DIR=$WM_PROJECT_USER_DIR/SOWFA6
export SOWFA_APPBIN=$SOWFA_DIR/platforms/$WM_OPTIONS/bin
export SOWFA_LIBBIN=$SOWFA_DIR/platforms/$WM_OPTIONS/lib
export LD_LIBRARY_PATH=$SOWFA_LIBBIN:$OPENFAST_DIR/lib:$BLASLIB:$LD_LIBRARY_PATH
export PATH=$SOWFA_APPBIN:$OPENFAST_DIR/bin:$PATH

#- Set Open MPI MCA parameters
export OMPI_MCA_oob=tcp
export OMPI_MCA_btl_openib_allow_ib=1
export OMPI_MCA_btl_tcp_if_include=ib0

#- Clean case
# ./clean.sh

start=`date +%s.%N`

#- Get the control dictionary for solver
cp system/controlDict.1 system/controlDict

#- Solve
if [ "$nprocs" -gt 1 ]; then
    mpirun -np $np -hostfile hosts.hf pimpleFoam -parallel > log.pimpleFoam 2>&1
    reconstructPar -latestTime > log.reconstructPar 2>&1
elif [ "$nprocs" -eq 1 ]; then
    pimpleFoam > log.pimpleFoam 2>&1
fi

foamToVTK -latestTime > log.foamToVTK.latestTime 2>&1

touch hf-openfoam.foam

. ../tools/openfoam-remove-empty-dirs.sh && openfoam_remove_empty_dirs
#--------------------------------------------------

end=`date +%s.%N`

echo "HF: Runtime:" $( echo "$end - $start" | bc -l )
# --------------------------------------------------------------EOF