#!/usr/bin/gnuplot
# set term postscript eps size 1024, 720 color blacktext "Helvetica" 24
set term png size 1024,700

parentDIR="/scratch/nkumar001/OpenFOAM/nkumar001-6/run/precice_openfoam-python_vortex-shedding_reconstruct/run.simulation_snapshots"
datFile1=parentDIR."/postProcessing/forceCoeffs_object/0/forceCoeffs.dat"
datFile2=parentDIR."/postProcessing/forceCoeffs_object/150/forceCoeffs.dat"

outDIR="/scratch/nkumar001/OpenFOAM/nkumar001-6/run/precice_openfoam-python_vortex-shedding_reconstruct/run.simulation_snapshots"
set output outDIR."/postProcessing/plot_ClCd.png"
set datafile commentschar '# '

set autoscale
unset log
unset label

set xtic auto
set ytic auto
unset title

set xlabel "Time [s]"
set ylabel "Coefficients"

set yrange [-1.0:2.5]

set style line 1 \
    linecolor rgb '#dd181f' \
    linetype 1 linewidth 2
set style line 2 \
    linecolor rgb '#0060ad' \
    linetype 1 linewidth 2

plot datFile1 using 1:3 title "C_D" with lines linestyle 1, \
     ''       using 1:4 title "C_L" with lines linestyle 2, \
     datFile2 using 1:3 notitle with lines linestyle 1, \
     ''       using 1:4 notitle with lines linestyle 2
