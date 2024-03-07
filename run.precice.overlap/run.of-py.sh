#!/bin/bash
#
#SBATCH --job-name=galfree.pod.of-py
#SBATCH --output=log.%x
#SBATCH --ntasks=2
#SBATCH --time=0-12:00:00
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

#- Ensure only owner can read the output
umask 0077

export SLURM_COMP_VERBOSE=3
export SLURM_LOADER_VERBOSE=3

#- Number of processors per participant
nprocs1=1
nprocs2=1

#- Select LF solver type
caseID='galfree'

#- Rename HF directory
parentDIR=$(pwd)
cp -r $parentDIR/hf-openfoam $parentDIR/hf-openfoam-$caseID

rm -rf $parentDIR/precice-run

#- Generate hostfiles
if [ "$nprocs1" -gt 1 ] && [ "$nprocs2" -gt 1 ]; then
    rm -f hosts.ompi # hosts.intel
    for host in `scontrol show hostname $SLURM_JOB_NODELIST`; do
        #- IntelMPI requires one entry per node
        # echo $host >> hosts.intel;
        #- OpenMPI requires one entry per slot
        for j in $(seq 1 ${SLURM_TASKS_PER_NODE%%(*}); do
            echo $host >> hosts.ompi;
        done
    done

    #- Partition the hosts for each participant
    sed -n " 1,${nprocs1}p" hosts.ompi > hf-openfoam-$caseID/hosts.hf
    sed -n "$(($nprocs1+1)),$(($nprocs1+$nprocs2))p" hosts.ompi > lf-pod/hosts.lf
fi

#- Source the bash profile
source /gpfs/home/nkumar001/.bash_profile

#- Load modules
module purge
module load gcc/7.3.0
module load openmpi/4.1.1/gcc/11.2.0
#
source /gpfs/home/nkumar001/tools/spack/share/spack/setup-env.sh
spack env activate preciceFoam 

#- Set Open MPI MCA parameters
export OMPI_MCA_oob=tcp
export OMPI_MCA_btl_openib_allow_ib=1
export OMPI_MCA_btl_tcp_if_include=ib0

echo "Starting job in ${parentDIR}"

start=`date +%s.%N`

# ----------------------------------------------------------------- 
echo "OF-PY job"

#- Print executed commands
set -e

#- Group runs to prevent a failure from wasting resources
set -m
(
    # Launch solver LF
    echo "Running low fidelity ..."
    cd $parentDIR/lf-$caseID
    ./run.sh -n $nprocs2 &> log.lf &

    # Launch solver HF
    echo "Running high fidelity ..."
    cd $parentDIR/hf-openfoam-$caseID
    ./run.sh -n $nprocs1 &> log.hf &

    # Wait for every solver to finish
    wait
)
echo "All participants succeeded"
cd $parentDIR

#- Plot error history wrt POD reconstruction
# python tools/test.checkOutputPOD.py

end=`date +%s.%N`
td=$( echo "$end - $start" | bc -l )
echo "Time elapsed:" $( date -d "@$td" -u "+$((${td%.*}/86400))-%H:%M:%S" )

# --------------------------------------------------------------EOF