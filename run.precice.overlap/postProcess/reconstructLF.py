#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 25/02/2023
# ---------------------------------------------------------------------------
""" 
Convert cloud data of field values obtained from wind-turbine simulation to VTK
"""

import numpy as np
import pandas as po
import argparse
import re
import sys
import os
from pathlib import Path

from pyevtk.hl import pointsToVTK

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- List subdirectories (not recursive)
#- SEE: https://stackoverflow.com/a/800201/7473705
def get_subdir(dirPATH):
    return [name for name in os.listdir(dirPATH)
            if os.path.isdir(os.path.join(dirPATH, name))]
#- Check and make directory path
def make_dir(dirPATH):
    Path(dirPATH).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class reconstructToVTK():
    def __init__(self, podPATH, chronosPATH, refPATH, fieldNAME, nModes):
        #- User input
        self.timeRange = [100.01, 100.5] 
        self.ntSkip = 1

        self.podPATH = podPATH
        self.chronosPATH = chronosPATH
        self.refPATH = refPATH
        self.fieldNAME = fieldNAME
        self.nModes = nModes

        #- Variable types
        self.scaList=["p", "p_rgh", "T", "Tprime", "k", "kSGS", "kSGSmean", 
                      "kappat", "nuSgs", "nuSGSmean", "nut", "omega"]
        self.vecList=["U", "Uprime"]
        self.tenList=["Rmean"]

        #- Component names
        self.vecCompNames = ["x", "y", "z"]
        self.tenCompNames = ["xx", "xy", "xz", "yy", "yz", "zz"]

    def createTimeList(self):
        #- Precision after decimal for float conversion
        nPrecFloat = 2
        listDir = np.array(get_subdir(self.chronosPATH))
        listDirFloat = np.array([round(float(i), nPrecFloat) for i in listDir])
        #- Trim
        #- SEE: https://stackoverflow.com/a/45039108/7473705
        listDir = listDir[(listDirFloat >= self.timeRange[0]) & (listDirFloat <= self.timeRange[1])]
        listDirFloat = listDirFloat[(listDirFloat >= self.timeRange[0]) & (listDirFloat <= self.timeRange[1])]
        #- Sort
        sortInd = sorted(range(len(listDirFloat)), key=lambda k: listDirFloat[k])
        listDir = [listDir[i] for i in sortInd]
        timeList = np.array([listDirFloat[i] for i in sortInd])
        ntFull = len(timeList)

        #- NOTE: Both timeListDIRS and timeList saved to avoid loss of precision
        self.timeListDIRS = listDir[::self.ntSkip]
        self.timeList = timeList[::self.ntSkip]
        self.nt = len(self.timeList)

    def getCoord(self):
        #- Read coordinates
        coordPATH = os.path.join(self.podPATH, 'internalField')
        coordFILENAME = 'pointCloud'
        #- List of pointCloud* files (NOT full path)
        coordListFILE = []
        for f in os.listdir(coordPATH):
            if f.startswith(coordFILENAME):
                coordListFILE.append(os.path.basename(f))
        #- Assign coordinate file 
        if coordFILENAME+'.mask' in coordListFILE:
            coordFILE = os.path.join(coordPATH,coordFILENAME+'.mask')
            useInd = [0,1,2]
        else:
            if coordFILENAME+'.xy' in coordListFILE:
                coordFILE = os.path.join(coordPATH,coordFILENAME+'.xy')
                useInd = [0,1,2]
            # if coordFILENAME+'.dat' in coordListFILE:
            #     coordFILE = os.path.join(coordPATH,coordFILENAME+'.dat')
            #     useInd = [1,2,3]
        #- Read coodinates
        self.coord = po.read_csv(coordFILE, 
                              delim_whitespace=True, 
                              header=None, 
                              usecols=useInd).to_numpy()
        self.npts = len(self.coord)

    def reconstruct(self):
        #- Flags
        isScalar = isVector = isTensor = False
        #- Column index/indices in the snapshot file to use
        if self.fieldNAME in self.scaList:
            isScalar = True
            nv = 1
        if self.fieldNAME in self.vecList:
            isVector = True
            nv = 3
        if self.fieldNAME in self.tenList:
            isTensor = True
            nv = 6

        #- Modes
        modeFILE = os.path.join(self.podPATH, 'modes.'+self.fieldNAME, 'mode.bin')
        modes = np.fromfile(modeFILE, dtype=float)
        modes = modes.reshape((self.nModes, self.npts*nv)).T

        #- Reconstruct
        for ti in range(self.nt):
            #- Coefficients
            chronosFILE = os.path.join(self.chronosPATH, self.timeListDIRS[ti], self.fieldNAME)
            chronos = po.read_csv(chronosFILE, delim_whitespace=True, header=None).to_numpy()
            #- Reconstruction
            predValue = modes@chronos
            if isScalar:
                predValue = predValue.squeeze()
            else:
                predValue = predValue.reshape((self.npts, nv), order='F')
                predValue = predValue[:,0]
            #- Reference value
            refFILE = os.path.join(self.refPATH, '{0:.12g}'.format(self.timeList[ti]), 'cloud_'+self.fieldNAME+'.xy')
            refValue = po.read_csv(refFILE, delim_whitespace=True, header=None).to_numpy()
            refValue = refValue[:,0]

            self._saveVTK(predValue, refValue, ti)

    def _saveVTK(self, fieldValue, refValue, ti):
        X = np.ascontiguousarray(self.coord[:,0])
        Y = np.ascontiguousarray(self.coord[:,1])
        Z = np.ascontiguousarray(self.coord[:,2])
        vtkFILENAME = self.fieldNAME+'_'+self.timeListDIRS[ti] # '{0:05d}'.format(ti)
        vtkDIR = os.path.join('.', 'VTK')
        make_dir(vtkDIR)
        pointsToVTK(os.path.join(vtkDIR, vtkFILENAME), 
                    X, Y, Z, 
                    data={self.fieldNAME: fieldValue, self.fieldNAME+'ref': refValue})

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    #- SEE: https://stackoverflow.com/a/32763023/7473705
    CLI = argparse.ArgumentParser(description='Compare field values')
    CLI.add_argument('-p', '--podPATH', 
                    help="POD directory", 
                    nargs='?', 
                    type=str,
                    default="../../pod/pod.np64_p-U-k-nut-omega_N31.run.overlap.hf"
                    )
    CLI.add_argument('-c', '--chronosPATH', 
                    help="Mode coefficients directory", 
                    nargs='?', 
                    type=str,
                    default="../lf-galfree/chronos"
                    )
    CLI.add_argument('-r', '--refPATH', 
                    help="Reference snapshots directory", 
                    nargs='?', 
                    type=str,
                    default="../../run.hf/postProcessing/internalField"
                    )
    CLI.add_argument('-f', '--fieldNAME', 
                    help="Field name", 
                    nargs='?', 
                    type=str,
                    default='U') #- 'p', 'p_rgh', 'T', 'U'
    CLI.add_argument('-n', '--nModes', 
                    help="Number of modes", 
                    nargs='?', 
                    type=int)

    try:
        args = CLI.parse_args()
    except SystemExit:
        print("Check inputs")
        quit()

    p = reconstructToVTK(args.podPATH, 
                         args.chronosPATH,
                         args.refPATH,
                         args.fieldNAME,
                         args.nModes)
    p.createTimeList()
    p.getCoord()
    p.reconstruct()

    print('DONE!')

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
