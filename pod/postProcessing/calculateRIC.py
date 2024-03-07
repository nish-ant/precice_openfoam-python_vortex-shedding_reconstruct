#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 28/02/2021
# ---------------------------------------------------------------------------
""" 
Post-calculation of relative information content (RIC) calculation
RUN: 
    $ python postProcessing/calculateRIC.py $chronosDIR $T
"""

import numpy as np
import sys

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class convertModeToVTK():
    def __init__(self, coordFILE, modeDIR, nModes):
        self.coordFILE = coordFILE
        self.modeDIR = modeDIR
        self.nModes = nModes
        self.varSize = 3

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class funcRIC():
    def __init__(self, T, chronosDIR):
        self.T = T
        self.chronosDIR = chronosDIR
        self.eigFILE = chronosDIR+'/eigenValues.bin'

        #- Convert string to number (e.g. bash input)
        if isinstance(self.T, str):
            self.T = int(float(T)) if int(float(T))==float(T) else float(T)

    def calcRIC(self):
        #- Read eigenvalues
        #- NOTE: '[1:]' to exclude base mode.
        self.eigvals = np.fromfile(self.eigFILE, dtype=float)[1:]

        #- Total energy
        self.totE = np.sum(self.eigvals)

        #- Calculate RIC corresponding to the number of modes T
        if isinstance(self.T, int) and self.T>0:
            ric = np.sum(self.eigvals[:self.T])/self.totE
            print('RIC corresponding to {0} modes is {1}'.format(self.T, ric))
        #- Calculate number of modes corresponding to RIC of T
        elif isinstance(self.T, float) and 0<=self.T<=1:
            ric = np.cumsum(self.eigvals)/self.totE
            #- Find first index of value greater than T
            #- See: https://stackoverflow.com/a/2236935/7473705
            ricidx = next(i for i,v in enumerate(ric) if v > self.T)
            print('Number of modes corresponding to RIC={0} is {1}'.format(self.T, ricidx))
        else:
            print("ERROR: Check value and type of threshold T.")

    def savedat(self):
        #- Calculate RIC
        ric = (np.cumsum(self.eigvals)/self.totE).tolist()

        #- Save
        modeN = list(range(1, len(ric) + 1))
        ricFILE = self.chronosDIR+'/ric.table.dat'
        np.savetxt(ricFILE, np.transpose([modeN, ric]), fmt='%i %.6f', header="N RIC")

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- POD directory
    chronosDIR = sys.argv[1]
    #- Threshold
    #-   T = [1, Nt-1] (int)   calculates RIC corresponding to the number of modes T, or
    #-       [0., 1.]  (float) calculates number of modes corresponding to RIC of T
    T = sys.argv[2]

    #- RIC calculation
    p = funcRIC(T, chronosDIR)
    p.calcRIC()
    #- Save table of RIC corresponding to modes retained (optional)
    p.savedat()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()