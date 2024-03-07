#!/bin/bash
rm -f hosts.intel hosts.ompi
for host in `scontrol show hostname $SLURM_JOB_NODELIST`; do
    # IntelMPI requires one entry per node
    echo $host >> hosts.intel;
    # OpenMPI requires one entry per slot
    for j in $(seq 1 ${SLURM_TASKS_PER_NODE%%(*}); do
        echo $host >> hosts.ompi;
    done
done