#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 16/02/2023
# ---------------------------------------------------------------------------
""" 
Post-evaluation of coupling data error
"""
from __future__ import division, print_function

import numpy as np
import pandas as po
import argparse
import glob
import re
import os
import sys

import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- List subdirectories (not recursive)
#- See: https://stackoverflow.com/a/800201/7473705
def get_subdir(dirPATH):
    return [name for name in os.listdir(dirPATH)
            if os.path.isdir(os.path.join(dirPATH, name))]
#- Read field
def loadFoamCSV(fileID):
    return po.read_csv(f"{fileID}", header=None, delim_whitespace=True, comment='#')

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class getError():
    def __init__(self, referenceDIR, solutionDIR, podDIR, coordFILE, fields):
        self.referenceDIR = referenceDIR
        self.solutionDIR = solutionDIR
        self.podDIR = podDIR
        self.coordFILE = coordFILE
        self.fields = fields

        runID = re.split('_|\*|\n', self.podDIR)
        for s in runID:
            if s.startswith('N'):
                self.nModes = int(s[1:])
                break

    def createTimeList(self):
        listDir = get_subdir(self.solutionDIR)
        listDirFloat = np.array([float(i) for i in listDir])
        
        #- Sort
        sortInd = sorted(range(len(listDirFloat)), key=lambda k: listDirFloat[k])
        # listDir = [listDir[i] for i in sortInd]
        self.timeList = np.array([listDirFloat[i] for i in sortInd])
        self.nt = len(self.timeList)

    def readData(self):
        #- Read coordinate
        self.grid = loadFoamCSV(self.coordFILE)
        self.nPts = self.grid.shape[0]

        #- Read data
        self.referenceData = {}
        self.solutionData = {}
        self.podData = {}
        for fldID in self.fields:
            if fldID in ['p', 'T', ]:
                self.nv = 1
            elif fldID in ['U', ]:
                self.nv = 3
            self.referenceData[fldID] = np.zeros((self.nPts, self.nv, self.nt))
            self.solutionData[fldID] = np.zeros((self.nPts, self.nv, self.nt))
            self.podData[fldID] = np.zeros((self.nPts, self.nv, self.nt))
            for it, t in enumerate(self.timeList):
                refFILE = os.path.join(self.referenceDIR, '{0:g}'.format(t-0.01), 'cloud_'+fldID+'.xy')
                pointData = loadFoamCSV(refFILE)
                self.referenceData[fldID][:,:,it] = pointData.to_numpy()
                #
                solFILE = os.path.join(self.solutionDIR, '{0:g}'.format(t), 'cloud_'+fldID+'.xy')
                pointData = loadFoamCSV(solFILE)
                self.solutionData[fldID][:,:,it] = pointData.to_numpy()

            #- Read POD modes
            modeFld = np.fromfile(os.path.join(self.podDIR, 'modes.'+fldID, 'mode.bin'), dtype=float)
            modeFld = modeFld.reshape((self.nModes, self.nPts*self.nv)).T
            for it, t in enumerate(self.timeList):
                fldData = self.referenceData[fldID][:,:,it].reshape((self.nPts*self.nv, 1), order='F')
                aFld = fldData.T@modeFld
                predFld = modeFld@aFld.T #- + modeFld[:, 0, None]
                self.podData[fldID][:,:,it] = predFld.reshape((self.nPts, self.nv), order='F')

    def getRelativeError(self):
        self.solutionRelError = {}
        self.podRelError = {}
        for fldID in self.fields:
            #- Get magnitude (no effect on scalars)
            referenceNorm = np.linalg.norm(self.referenceData[fldID], axis=1)
            solutionNorm = np.linalg.norm(self.solutionData[fldID], axis=1)
            podNorm = np.linalg.norm(self.podData[fldID], axis=1)
            #-
            solutionErr = np.abs(solutionNorm-referenceNorm)
            podErr = np.abs(podNorm-referenceNorm)
            
            #- Relative spatial mean (for plotting)
            referenceNormSpaceMean = np.mean(referenceNorm**2, axis=0)
            self.solutionRelError[fldID] = np.sqrt(np.mean(solutionErr**2, axis=0)/referenceNormSpaceMean)
            self.podRelError[fldID] = np.sqrt(np.mean(podErr**2, axis=0)/referenceNormSpaceMean)

            #- Relative temporal error mean
            referenceNormTimeMean = np.mean(referenceNorm**2, axis=1)
            solutionRelErrTimeMean = np.sqrt(np.mean(solutionErr**2, axis=1)/referenceNormTimeMean)
            podRelErrTimeMean = np.sqrt(np.mean(podErr**2, axis=1)/referenceNormTimeMean)
            
            #- Spatial mean
            solutionErrSpaceMean = np.mean(solutionRelErrTimeMean)
            podErrSpaceMean = np.mean(podRelErrTimeMean)

            #- Maximum
            solutionErrSpaceMax = np.max(solutionRelErrTimeMean)
            podErrSpaceMax = np.max(podRelErrTimeMean)

            print('Solution error {0}: mean={1}, max={2}'.format(fldID, solutionErrSpaceMean, solutionErrSpaceMax))
            print('POD error, Field {0}: mean={1}, max={2}'.format(fldID, podErrSpaceMean, podErrSpaceMax))

    def plotErrorHistory(self):
        fig, ax = plt.subplots(figsize=(10, 6))
        for fldID in self.fields:
            ax.semilogy(self.timeList, self.solutionRelError[fldID], label='Solution: '+fldID)
            ax.semilogy(self.timeList, self.podRelError[fldID], label='POD: '+fldID)
        ax.set(# title = "Relative L2 error - Postprocess",
               xlabel = "t",
               ylabel = "Error")
        plt.legend(loc=0, frameon=False)
        plt.tight_layout()

        outDIR = os.path.join(self.solutionDIR, '..')
        # Path(outDIR).mkdir(parents=True, exist_ok=True)

        outFILE = os.path.join(outDIR, 'plot_overlap_relError.png')
        plt.savefig(outFILE, bbox_inches='tight')

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Read arguments
    #- SEE: https://stackoverflow.com/a/32763023/7473705
    CLI = argparse.ArgumentParser(description='Postprocess relative error')
    CLI.add_argument('--referenceDIR', 
                    help="Reference directory", 
                    nargs='?', 
                    type=str,
                    default="../run.m0.1Re100/postProcessing/boundaryField")
    CLI.add_argument('--solutionDIR', 
                    help="Solution directory", 
                    nargs='?', 
                    type=str,
                    default="./hf-openfoam-pod/postProcessing/boundaryField")
    CLI.add_argument('--podDIR', 
                    help="POD directory", 
                    nargs='?', 
                    type=str,
                    default="../pod/pod.run.couple.np32_p-U_N15")
    CLI.add_argument('--coordFILE', 
                    help="File path of coordinates", 
                    nargs='?', 
                    type=str,
                    default="./hf-openfoam-pod/system/sampling/getBoundaryPoints/faceCenter.dat")
    CLI.add_argument('--fields', 
                    help="Field names", 
                    nargs='*', 
                    type=str,
                    default=['p', 'U'])

    try:
        args = CLI.parse_args()
    except SystemExit:
        print("Check inputs")
        quit()

    print('\nPost-evaluation boundary data error...')
    p = getError(args.referenceDIR, 
                 args.solutionDIR, 
                 args.podDIR, 
                 args.coordFILE,
                 args.fields)
    p.createTimeList()
    p.readData()
    p.getRelativeError()
    p.plotErrorHistory()

    print('DONE!')

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()