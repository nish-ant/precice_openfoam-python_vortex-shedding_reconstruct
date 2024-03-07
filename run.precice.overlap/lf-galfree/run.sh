#!/bin/sh
set -e -u

#- Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--nprocs) nprocs="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "RUNTIME: " $(which python)

parentDIR=$(pwd)

#- TODO parallel implementation: if [ "$nprocs" -gt 1 ]; then
if [ "$nprocs" -eq 1 ]; then
    python lf-solver.py -c ../precice-config.xml -p $parentDIR 
else
    echo "ERROR: Check number of processors assigned for LF"
    exit 1
fi