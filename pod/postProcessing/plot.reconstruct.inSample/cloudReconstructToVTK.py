#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 21/12/2021
# ---------------------------------------------------------------------------
""" 
Convert reconstructed field in the form of cloud point data to VTK
USAGE: python cloudReconstructToVTK.py [timeList] [coordList] [snapsDir] [recDir]
"""

import numpy as np
import pandas as po
import sys
from tqdm import tqdm
from pathlib import Path

from pyevtk.hl import pointsToVTK

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- Check and make directory path
def make_dir(dirpath):
    Path(dirpath).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class convertReconToVTK():
    def __init__(self, timeFile, pointFile, snapsDir, recDir):
        self.timeFile = timeFile
        self.pointFile = pointFile
        self.snapsDir = snapsDir
        self.recDir = recDir
        self.varSize = 3

    def readData(self):
        #- Select time directories
        self.timeList=np.loadtxt(self.timeFile)

        #- Number of snapshots
        self.N = len(self.timeList)

        #- Coordinates
        if self.pointFile.endswith('.dat'):
            useInd = [1,2,3]
        elif self.pointFile.endswith('.xy'):
            useInd = [0,1,2]
        pts = po.read_csv(self.pointFile, 
                          delim_whitespace=True, 
                          header=None, 
                          names=['x', 'y', 'z'], 
                          usecols=useInd)
        self.x = pts[['x']].to_numpy().squeeze()
        self.y = pts[['y']].to_numpy().squeeze()
        self.z = pts[['z']].to_numpy().squeeze()

        #- Size
        self.MM = len(self.x)

        self.x = self.x.reshape(self.MM, 1, order='C')
        self.y = self.y.reshape(self.MM, 1, order='C')
        self.z = self.z.reshape(self.MM, 1, order='C')

        assert(len(self.x) == len(self.y))
        assert(len(self.y) == len(self.z))

        #- Read the original field
        self.U_V = np.zeros([self.varSize*self.MM, self.N],'float')
        print('\nReading initial velocity fields from dat files...\n')
        for i in tqdm(range(self.N)):
            t = self.timeList[i]
            self.U_V[:,i] = np.loadtxt(self.snapsDir+'/%s/cloud_U.xy' 
                            %(str(t if t%1 else int(t))), 
                            skiprows=0, 
                            unpack=True).reshape(self.varSize*self.MM)

        #- Read the reconstructed field
        print('\nReading reconstructed velocity fields from binary files...\n')
        self.U_R_V = np.fromfile(self.recDir+'/reconstruction.bin', dtype=float)
        self.U_R_V = self.U_R_V.reshape(self.N, self.varSize*self.MM)

    def saveVTK(self):
        vtkDir = self.recDir+"/VTK/"
        make_dir(vtkDir)
        print('\nWriting the fields and reconstructions in VTK files...\n')
        MM = self.MM
        for i in tqdm(range(self.N)):
            t = self.timeList[i]
            U_V_C = np.ascontiguousarray(self.U_V[:,i], dtype=np.float32)
            U = (U_V_C[:MM], U_V_C[MM:2*MM], U_V_C[2*MM:3*MM])
            U_R = (self.U_R_V[i, :MM], self.U_R_V[i, MM:2*MM], self.U_R_V[i, 2*MM:3*MM])
            pointsToVTK(vtkDir+"U_%s"%(str(t if t % 1 else int(t))), 
                    self.x, self.y, self.z, data={"U": U, "U_R": U_R})

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    #- NOTE: sys.argv[0] is always the script name
    timeFile = sys.argv[1]
    pointFile = sys.argv[2]
    snapsDir = sys.argv[3]
    recDir = sys.argv[4]

    p = convertReconToVTK(timeFile, pointFile, snapsDir, recDir)
    p.readData()
    p.saveVTK()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# indStart = 0
# indEnd = 49
# indStep = 5
# N = int((indEnd-indStart)/indStep)+1
# listInd = [i for i in range(indStart, indEnd+1, indStep)]