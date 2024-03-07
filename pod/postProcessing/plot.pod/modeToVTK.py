#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 25/02/2022
# ---------------------------------------------------------------------------
""" 
Convert POD modes to VTK
RUN:
    $ python plot/modeToVTK.py $modesDIR $nModes
"""

import numpy as np
import pandas as po
import sys
import os
# from tqdm import tqdm
from pathlib import Path
from pyevtk.hl import pointsToVTK

# import time as clock
# start_time = clock.time()

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- Count number of lines in a file
#- See: https://stackoverflow.com/a/845081/7473705
def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

#- Check and make directory path
def make_dir(dirpath):
    Path(dirpath).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class convertModeToVTK():
    def __init__(self, modesDIR, varSize, nModes):
        self.modesDIR = modesDIR
        self.varSize = varSize
        self.nModes = nModes
        
    def readData(self):
        fieldDIR = os.path.join(self.modesDIR,'..','internalField')
        #- List of pointCloud* files (NOT full path)
        coordFILES = []
        for f in os.listdir(fieldDIR):
            if f.startswith('pointCloud'):
                coordFILES.append(os.path.basename(f))
        #- Assign coordinate file 
        if 'pointCloud.mask' in coordFILES:
            self.coordFILE = os.path.join(fieldDIR,'pointCloud.mask')
            useInd = [0,1,2]
        else:
            if 'pointCloud.xy' in coordFILES:
                self.coordFILE = os.path.join(fieldDIR,'pointCloud.xy')
                useInd = [0,1,2]
            elif 'pointCloud.dat' in coordFILES:
                self.coordFILE = os.path.join(fieldDIR,'pointCloud.dat')
                useInd = [1,2,3]

        pts = po.read_csv(self.coordFILE, 
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

        #- Read the modes
        print('\nReading modes from binary files...\n')
        self.mode = np.fromfile(self.modesDIR+'/mode.bin', dtype=float)
        self.mode = self.mode.reshape(self.nModes, self.varSize*self.MM)

    def saveVTK(self):
        vtkDIR = self.modesDIR+"/VTK"
        make_dir(vtkDIR)
        print('\nWriting the modes in VTK files...\n')
        MM = self.MM
        # for i in tqdm(range(self.nModes)):
        for i in range(self.nModes):
            #- NOTE: Tuple data is identified as vector in pointsToVTK
            if self.varSize == 1:
                modei = self.mode[i, :]
            else:
                modei = ()
                for j in range(self.varSize):
                    modei += (self.mode[i, j*MM:(j+1)*MM], )
            pointsToVTK(vtkDIR+"/mode_%s"%(str(i)), 
                        self.x, self.y, self.z, 
                        data={"mode": modei})

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    #- NOTE: sys.argv[0] is always the script name
    modesDIR = sys.argv[1]
    varSize = int(sys.argv[2])
    nModes = int(sys.argv[3])

    p = convertModeToVTK(modesDIR, varSize, nModes)
    p.readData()
    p.saveVTK()

    print('\nDONE!...\n')

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()