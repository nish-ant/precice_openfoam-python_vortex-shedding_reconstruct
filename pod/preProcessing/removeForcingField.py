#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 21/12/2022
# ---------------------------------------------------------------------------
""" 
Calculate forcing field, subtract from the fields and save as snapshots
"""

import numpy as np
import pandas as po
import argparse
import sys
import os
import shutil
import glob
import json
from pathlib import Path
from mpi4py import MPI

comm = MPI.COMM_WORLD
MPI_RANK = comm.Get_rank()
MPI_SIZE = comm.Get_size()

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- Check and make directory path
#- SEE: https://stackoverflow.com/a/273227
def make_dir(dirPATH):
    Path(dirPATH).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class getForcingField():
    def __init__(self, fieldNAME, timeList, sampleDIR, outDIR, runType):
        self.fieldNAME = fieldNAME
        self.timeList = timeList
        self.sampleDIR = sampleDIR
        self.outDIR = outDIR
        self.runType = runType

        #- Read input 
        if self.runType == "init":
            inputFILE = "./preProcessing/userInput.json"
        elif self.runType in ["predict", "predictOT"]:
            inputFILE = "./postProcessing/userInput.predict.json"
        #- 
        with open(inputFILE) as f:
            inputJSON = json.load(f)
        #- Inflow domain limits of bounding box
        self.inflowDomain = inputJSON['inflowDomain']

        #- Run index (starts from 1)
        self.runINDEX = inputJSON['sampleDirectories'].index(self.sampleDIR)+1

        #- Variable types
        self.scaList=["p", "p_rgh", "T", "Tprime", "k", "kSGS", "kSGSmean", 
                      "kappat", "nuSgs", "nuSGSmean", "nut", "omega"]
        self.vecList=["U", "Uprime"]
        self.tenList=["Rmean"]

    def getInflowDomain(self):
        #- Full domain coordinates
        coordFILEName = os.path.join(self.sampleDIR, 
                                'system','sampling','pointCloud') #- .dat or .xy
        coordFILEList = glob.glob(coordFILEName+'.*')
        if [True if f.endswith('.xy') else False for f in coordFILEList][0]:
            coordFILE = [f if f.endswith('.xy') else None for f in coordFILEList][0]
            useInd = [0,1,2]
        elif [True if f.endswith('.dat') else False for f in coordFILEList][0]:
            coordFILE = [f if f.endswith('.dat') else None for f in coordFILEList][0]
            useInd = [1,2,3]
        assert coordFILE != None, f"Coordinate file not found!"
        self.allCoord = po.read_csv(coordFILE, 
                          delim_whitespace=True, 
                          header=None, 
                          names=['x', 'y', 'z'], 
                          usecols=useInd).to_numpy()
        self.nAllCoord = len(self.allCoord)
        #- Copy coordinates file
        coordFILEBaseName = os.path.basename(coordFILE)
        coordFILEOut = os.path.join(self.outDIR, coordFILEBaseName)
        if not os.path.isfile(coordFILEOut):
            make_dir(self.outDIR)
            shutil.copy2(coordFILE, coordFILEOut)

        #- Bounding domain index
        self.boundInd = np.empty(self.nAllCoord)
        if MPI_RANK == 0:
            xyzMin = self.inflowDomain['xyzMin']
            xyzMax = self.inflowDomain['xyzMax']
            self.boundInd = np.all((xyzMin <= self.allCoord) & 
                                   (xyzMax >= self.allCoord), 
                                   axis=1).astype(float)
        comm.Bcast([self.boundInd, MPI.DOUBLE], root=0)
        self.boundInd = self.boundInd.astype(bool)

    def scatterTime(self):
        self.ts = po.read_csv(self.timeList, 
                          delim_whitespace=True, 
                          header=None).to_numpy().flatten()
        self.ts = [int(float(t)) if int(float(t))==float(t) else float(t) for t in self.ts]
        self.nt = len(self.ts)
        self.timeIndPerRank = None
        if MPI_RANK == 0:
            #- Determine the size of each sub-task
            v, res = divmod(self.nt, MPI_SIZE)
            taskSizePerRank = [v+1 if p<res else v for p in range(MPI_SIZE)]
            #- Determine starting and ending indices of each sub-task
            startIndPerTask = [sum(taskSizePerRank[:p]) for p in range(MPI_SIZE)]
            endIndPerTask = [sum(taskSizePerRank[:p+1]) for p in range(MPI_SIZE)] 
            #- Split full time list into sub-list
            timeInd = np.arange(self.nt).tolist()
            self.timeIndPerRank = [timeInd[startIndPerTask[p]:endIndPerTask[p]] \
                                    for p in range(MPI_SIZE)]
        self.timeIndPerRank = comm.scatter(self.timeIndPerRank, root=0)

    def getMeanProfile(self):
        #- Column index/indices in the snapshot file to use
        fld = self.fieldNAME
        self.nv = 0
        if fld in self.scaList:
            self.nv = 1
        if fld in self.vecList:
            self.nv = 3
        if fld in self.tenList:
            self.nv = 6
        assert self.nv>0, f"Field size not assigned!"
        
        #- Group z-coordinates for each unique (x,y) locations
        self.zAllIndList = self._groupZCoord(self.allCoord)
        self.nzAll = len(self.zAllIndList[0])
        #-
        boundCoord = self.allCoord[self.boundInd.astype(bool)]
        zBoundIndList = self._groupZCoord(boundCoord)
        nzBound = len(zBoundIndList[0])
        nxyUniqueBound = len(zBoundIndList)
        assert self.nzAll==nzBound, \
               f"Profile length mismatch: All={self.nzAll}, Bound={nzBound}"
        
        #- Paths
        forcingFieldDIR = os.path.join(self.outDIR, 'forcingField')
        make_dir(forcingFieldDIR)

        #- Number of time steps in the current rank
        self.ntPerRank = len(self.timeIndPerRank)
        
        #- Get profiles
        npvAll = self.nAllCoord*self.nv
        self.snapAllPerRank = np.zeros((self.ntPerRank, npvAll))
        boundZSnapSum = np.zeros(nzBound*self.nv)
        for i in range(self.ntPerRank):
            snapFILE = os.path.join(self.sampleDIR, 
                        'postProcessing', 'internalField', 
                        str(self.ts[self.timeIndPerRank[i]]),
                        'cloud_'+fld+'.xy')
            allField = po.read_csv(snapFILE, 
                                   header=None, 
                                   delimiter="\t").to_numpy()
            self.snapAllPerRank[i,:] = allField.reshape(npvAll)
            #- Get rank-wise sum of profiles
            if self.runType == "predict":
                boundField = allField[self.boundInd, :]
                #- Sum and mean over all unique (x,y) location
                for j in range(nxyUniqueBound):
                    zInd = zBoundIndList[j]
                    boundZSnapSum += boundField[zInd,:].reshape(nzBound*self.nv)

        #- Calculate or get forcing field based on runType
        if self.runType == "predict":
            #- Get mean over all unique (x,y) locations
            self.boundZSnapMean = boundZSnapSum/nxyUniqueBound
            
            #- Get mean over all time
            #- NOTE: The rank-specific variables boundZSnapSum and boundZSnapMean 
            #-       are reused to represent their counterparts over all ranks.
            comm.Barrier()
            boundZSnapSum = np.zeros(nzBound*self.nv)
            comm.Allreduce(self.boundZSnapMean, boundZSnapSum, op=MPI.SUM)
            if MPI_RANK == 0:
                self.boundZSnapMean = boundZSnapSum/self.nt
            comm.Bcast([self.boundZSnapMean, MPI.DOUBLE], root=0)
            
            #- Reshape
            self.boundZSnapMean = self.boundZSnapMean.reshape((nzBound, self.nv))
            
            #- Save mean profile
            outMeanFILE = os.path.join(forcingFieldDIR, 
                                       str(self.runINDEX)+'.ff_'+self.fieldNAME+'.xy')
            np.savetxt(outMeanFILE, self.boundZSnapMean, fmt='%g', delimiter='\t')

            #- Save zCoord
            zBoundCoord = boundCoord[zBoundIndList[0],2]
            outFILE = os.path.join(forcingFieldDIR, 'zCoordBound.xy')
            if not Path(outFILE).is_file():
                np.savetxt(outFILE, zBoundCoord, fmt='%g', delimiter='\t')

        elif self.runType == "predictOT":
            meanOTProfileFILE = os.path.join(forcingFieldDIR, 
                                   str(self.runINDEX)+'.ff_'+self.fieldNAME+'.xy')
            self.boundZSnapMean = po.read_csv(meanOTProfileFILE, 
                                       header=None, 
                                       delimiter="\t").to_numpy()

    def removeForcingField(self):
        nxyUniqueAll = len(self.zAllIndList)
        for i in range(self.ntPerRank):
            #- Calculate fluctuation
            fluctAllField = self.snapAllPerRank[i,:].reshape((self.nAllCoord, self.nv))
            for j in range(nxyUniqueAll):
                zInd = self.zAllIndList[j]
                fluctAllField[zInd,:] -= self.boundZSnapMean
            #- Save fluctuating field
            ti = str(self.runINDEX)+'.'+str(self.ts[self.timeIndPerRank[i]])
            outDIR = os.path.join(self.outDIR, ti)
            make_dir(outDIR)
            outFILE = os.path.join(outDIR, 'cloud_'+self.fieldNAME+'.xy')
            np.savetxt(outFILE, fluctAllField, fmt='%g', delimiter='\t')

    def _groupZCoord(self, coord):
        #- Get unique (x,y) locations
        xyUniqueInd = np.unique(coord[:,[0, 1]], axis=0, return_index=True)[1]
        xyUnique = coord[xyUniqueInd, :2]
        nxyUnique = len(xyUniqueInd)
        #- Get indices of all points grouped by the (x,y) locations
        zIndList = []
        for i in range(nxyUnique):
            zIndList += [np.where(np.all(coord[:,:2]==xyUnique[i], axis=1))[0], ]
        return zIndList

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    CLI = argparse.ArgumentParser(description='Compare field values')
    CLI.add_argument('-f', '--fieldNAME', 
                    help="Field name", 
                    nargs='?', # '*'
                    type=str,
                    default='U')
    CLI.add_argument('-t', '--timeList', 
                    help="List of time steps", 
                    nargs='?',
                    type=str)
    CLI.add_argument('-s', '--sampleDIR', 
                    help="Input sample directory to read snapshots", 
                    nargs='?', 
                    type=str)
    CLI.add_argument('-o', '--outDIR', 
                    help="Output directory to store snapshots", 
                    nargs='?', 
                    type=str)
    CLI.add_argument('-r', '--runType', 
                    help="Stage of run: basis generation or predict (optional)", 
                    nargs='?', 
                    type=str,
                    default='init')

    try:
        args = CLI.parse_args()
    except SystemExit:
        print("Check inputs")
        quit()

    p = getForcingField(args.fieldNAME,
                        args.timeList,
                        args.sampleDIR,
                        args.outDIR,
                        args.runType)

    p.getInflowDomain()
    p.scatterTime()
    p.getMeanProfile()
    p.removeForcingField()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()