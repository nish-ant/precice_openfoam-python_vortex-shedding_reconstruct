#!/usr/bin/gnuplot
# set term postscript eps size 1024, 720 color blacktext "Helvetica" 24
# set term epslatex color
set term eps enhanced size 5,3

#- Field
fld="U" #"p"
podID='/pod.np64_p-U-k-nut-omega_N6.run.overlap.hf'

#- Number of (most-energetic) modes to plot
nModes=100
nCutoff=6

#- Python path
pythonPATH="/gpfs/home/nkumar001/anaconda3/envs/sowfa/bin/python"

#- Paths
parentDIR=GPVAL_PWD
podDIR=parentDIR.podID
outDIR=parentDIR.podID."/plot"
system "mkdir -p ".outDIR

eigFile=podDIR."/chronos.".fld."/eigenValues.bin"

set output outDIR."/plot.spectrum.".fld.".eps"
set datafile commentschar '# '

set autoscale
unset log
unset label

set xtic auto
set ytic auto
unset title

set logscale y
set format y "10^{%L}"

set xlabel "Modes"
set ylabel "Eigenvalue"
# set ylabel "$\lambda$"

set xrange [1:nModes]

set style line 1 \
    linecolor rgb '#dd181f' \
    linetype 1 linewidth 2 \
    pointtype 6 pointsize 0.5
set style line 2 \
    linecolor rgb '#0060ad' \
    linetype 1 linewidth 2 \
    pointtype 6 pointsize 0.5
# set style line 3 \
#     linecolor rgb '#06c248' \
#     linetype 1 linewidth 2 \
#     pointtype 6 pointsize 0.5

#- Vertical line to indicate cut-off
# set arrow from nCutoff,10 to nCutoff,100000 nohead lc rgb '#000000' lt 2

# plot eigFile binary format="%double" every ::1::50 using ($0+1):1 notitle with linepoints linewidth 1
plot eigFile binary format="%double" every ::1::nModes using 2 notitle with linespoints linestyle 1

# plot "< ".pythonPATH." plot/plot_spectrum.helper.py ".eigFile using ($0+1):1 notitle with linepoints linewidth 1
# plot "< ".pythonPATH." plot/plot_spectrum.helper.py ".eigFile

# plot eigvalFile every ::1 using ($0+1):1 notitle with linespoints linestyle 1