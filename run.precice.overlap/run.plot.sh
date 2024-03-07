#!/bin/bash
#
#SBATCH --job-name=plotter
#SBATCH --output=log.plot
#SBATCH --ntasks=2
#SBATCH --time=0-00:30:00
#SBATCH --partition=preemptible
#SBATCH --ear=off

echo "#############################"
echo "User:" $USER
echo "Submit time:" $(squeue -u $USER -o '%30j %20V' | \
    grep -e $SLURM_JOB_NAME | awk '{print $2}')
echo "Host:" `hostname`
echo "Directory:" `pwd`
echo "SLURM_JOBID:" $SLURM_JOBID
echo "SLURM_JOB_NAME:" $SLURM_JOB_NAME
echo "SLURM_SUBMIT_DIR:" $SLURM_SUBMIT_DIR
echo "SLURM_JOB_NODELIST:" $SLURM_JOB_NODELIST
echo "#############################"

unset LD_LIBRARY_PATH

# Print executed commands
# set -e -u

#- User input
runStr="of-py"

#- Ensure only owner can read the output
umask 0077

export SLURM_COMP_VERBOSE=3
export SLURM_LOADER_VERBOSE=3

#- Source the bash profile
source /gpfs/home/nkumar001/.bash_profile

#- Load modules
module purge
module load gcc/7.3.0
module load openmpi/4.1.1/gcc/11.2.0
#
source /gpfs/home/nkumar001/tools/spack/share/spack/setup-env.sh
spack env activate preciceFoam 

parentDIR=$(pwd)

#- Visualize configuration
module load graphviz/2.40.1
cat ./precice-config.xml | precice-config-visualizer | dot -Tpdf > config.lvs-couple.${runStr}.pdf

echo "DONE!"

# ----------------------------------------------------------------- end-of-file
