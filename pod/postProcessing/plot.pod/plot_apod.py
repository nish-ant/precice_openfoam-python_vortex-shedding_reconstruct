#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 25/02/2022
# ---------------------------------------------------------------------------
""" 
Plot temporal POD coefficient
NOTE: (Obsolete) Prefer gnuplot script plot_apod.p
"""

import numpy as np
import pandas as po
import sys
from tqdm import tqdm
from pathlib import Path

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class readChronos():
    def __init__(self, timeList, chronosDIR, nModes):
        self.timeList = timeList
        self.chronosDIR = chronosDIR
        self.nModes = nModes

    def readData(self):
        #- Times
        ts = po.read_csv(self.timeList, 
                          delim_whitespace=True, 
                          header=None, 
                          usecols=[0,])
        self.t = ts.to_numpy().squeeze()

        #- Size
        self.nt = len(self.t)
        # self.t = self.t.reshape(self.nt, 1, order='C')

        #- Read chronos
        # print('\nReading chronos from binary files...\n')
        self.chronos = np.fromfile(self.chronosDIR+'/chronos.bin', dtype=float)
        self.chronos = self.chronos.reshape(self.nt, self.nModes)
        
    def plotter(self):
        nModesPlot=10
        for m in range(nModesPlot):
            plt.plot(self.t, self.chronos[:, m+1], label='a_{'+str(m+1)+'}')
        plt.legend()
        # plt.show()
        # plt.xlim([max(self.t)-25, max(self.t)])
        plt.savefig(self.chronosDIR+'/plot.apod.png', bbox_inches='tight')

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    #- NOTE: sys.argv[0] is always the script name
    # outDIR="xx/POD"
    # timeList=outDIR+"/pod.xx.cxx/snapshotTimes"
    # chronosDIR=outDIR+"/pod.xx.cxx/chronos"
    # nModes=xx
    #
    timeList = sys.argv[1]
    chronosDIR = sys.argv[2]
    nModes = int(sys.argv[3])

    p = readChronos(timeList, chronosDIR, nModes)
    p.readData()
    p.plotter()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()