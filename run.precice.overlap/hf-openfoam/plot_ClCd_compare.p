#!/usr/bin/gnuplot
# set term postscript eps size 1024, 720 color blacktext "Helvetica" 24
# set term png size 1024,700
set term pngcairo size 1024,700
set termoption dashed

caseID="galfree" # "internalValue" # "pod"
nModes="" # ".N31" #- Empty when caseID="internalValue"

parentDIR="/scratch/nkumar001/OpenFOAM/nkumar001-6/run/precice_openfoam-python_vortex-shedding_reconstruct/run.precice.overlap/hf-openfoam-".caseID
datFile=parentDIR."/postProcessing/forceCoeffs/100/forceCoeffs.dat"

refDIR="/scratch/nkumar001/OpenFOAM/nkumar001-6/run/precice_openfoam-python_vortex-shedding_reconstruct/run.simulation_snapshots"
refFile1=refDIR."/postProcessing/forceCoeffs_object/0/forceCoeffs.dat"
refFile2=refDIR."/postProcessing/forceCoeffs_object/100/forceCoeffs.dat"

outDIR="/scratch/nkumar001/OpenFOAM/nkumar001-6/run/precice_openfoam-python_vortex-shedding_reconstruct/run.precice.overlap/hf-openfoam-".caseID
set output outDIR."/postProcessing/plot_ClCd.c8.precice.".caseID.nModes.".png"
set datafile commentschar '# '

set autoscale
unset log
unset label

set xtic auto
set ytic auto
unset title

set xlabel "Time [s]"
set ylabel "Coefficients"

# set yrange [-1.0:2.5]
set yrange [-0.5:2.5]
set xrange [100:150]

set style line 1 \
    linecolor rgb '#dd181f' \
    linetype 1 linewidth 1
set style line 2 \
    linecolor rgb '#0060ad' \
    linetype 1 linewidth 1
set style line 3 \
    linecolor rgb '#dd181f' \
    linetype 3 linewidth 1
set style line 4 \
    linecolor rgb '#0060ad' \
    linetype 3 linewidth 1

plot datFile using 1:3 title "C_D" with lines linestyle 1, \
     ''      using 1:4 title "C_L" with lines linestyle 2, \
     refFile1 using 1:3 title "C_D Ref" with lines linestyle 3, \
     ''       using 1:4 title "C_L Ref" with lines linestyle 4, \
     refFile2 using 1:3 notitle with lines linestyle 3, \
     ''       using 1:4 notitle with lines linestyle 4
