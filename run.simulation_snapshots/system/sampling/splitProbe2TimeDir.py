#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 21/12/2022
# ---------------------------------------------------------------------------
""" 
Split field-wise probes data into individual time directories while
    mimicing OpenFOAM's cloud data output format.
"""

import numpy as np 
import pandas as po
import re
import os
import sys
import argparse
from pathlib import Path
from itertools import islice

from mpi4py import MPI

comm = MPI.COMM_WORLD
MPI_RANK = comm.Get_rank()
MPI_SIZE = comm.Get_size()

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
#- Check and make directory path
def make_dir(dirPATH):
    Path(dirPATH).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class splitProbe2TimeDir():
    def __init__(self, probesSUBDIR, fieldNAME, coordFILE):
        self.probesSUBDIR = os.path.abspath(probesSUBDIR)
        self.fieldNAME = fieldNAME
        self.coordFILE = coordFILE

        #- Variable types
        self.scaList=["p", "p_rgh", "T", "Tprime", "k", "kSGS", "kSGSmean", 
                      "kappat", "nuSgs", "nuSGSmean", "nut", "omega"]
        self.vecList=["U", "Uprime"]
        self.tenList=["Rmean"]

    def getCoordinates(self):
        #- Get number of probe points
        self.fieldFILE = os.path.join(self.probesSUBDIR, self.fieldNAME)
        with open(self.fieldFILE, 'r') as f:
            for line in f:
                if line.startswith('#             Probe'):
                    self.nCoord = len(line.split())-2
                    break

        #- Get probe coordinates
        self.coordPts = np.empty((self.nCoord, 3))
        if MPI_RANK == 0:
            coordFILE = Path(self.coordFILE)
            if not coordFILE.is_file():
                coordPts = []
                with open(self.fieldFILE, 'r') as f:
                    for line in f:
                        if line.startswith('# Probe '):
                            #- Read content between ()
                            coord = line[line.find("(")+1:line.find(")")]
                            #- Convert string to list of floats
                            coord = [float(s) for s in coord.split()]
                            coordPts.append(coord)
                        elif line.startswith('#              Time '):
                            break
                #- Save coordinates
                self.coordPts = np.array(coordPts).astype(float)
                np.savetxt(self.coordFILE, self.coordPts, delimiter='\t', fmt='%.12g')
            else:
                #- Read coordinates
                useInd = [0,1,2]
                self.coordPts = po.read_csv(coordFILE, 
                              delim_whitespace=True, 
                              header=None, 
                              usecols=useInd).to_numpy()
        #     #- P2P send
        #     for i in range(1, MPI_SIZE):
        #         comm.Send([self.coordPts, MPI.DOUBLE], dest=i, tag=77)
        # else:
        #     self.coordPts = np.empty((897,3))
        #     #- P2P receive
        #     comm.Recv([self.coordPts, MPI.DOUBLE], source=0, tag=77)

        comm.Bcast([self.coordPts, MPI.DOUBLE], root=0)
        self.nCoord = self.coordPts.shape[0]

        #- Number of header lines in file
        self.nHeader = self.nCoord+2

    def getCloud(self):
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

        #- Scatter time
        self._scatterTime()

        #- Output snapshots directory
        #- SEE: https://stackoverflow.com/a/31724762/7473705
        probesDIR, _ = os.path.split(self.probesSUBDIR)
        suffixes = ['Orig', '.probes.orig']
        self.snapsDIR = None
        for suffix in suffixes:
            if probesDIR.endswith(suffix):
                self.snapsDIR = probesDIR.removesuffix(suffix)
        if self.snapsDIR:
            make_dir(self.snapsDIR)
        else:
            print("ERROR: Directory name {0} must end with {1}".format(probesDIR, suffix))
            comm.abort()

        #- Read line and transform to column
        timeIndFull = np.arange(self.nt)
        ntPerRank = len(self.timeIndPerRank)

        #- Option [1]
        # for i in range(ntPerRank):
        #     #- NOTE: Line count starts from 0
        #     lineN = timeIndFull[self.timeIndPerRank[i]]+self.nHeader
        #     with open(self.fieldFILE, 'r') as f:
        #         for lineNinFile, lineStr in enumerate(f):
        #             if lineNinFile == lineN:
        #                 print("Rank: ", MPI_RANK, "lineN: ", timeIndFull[self.timeIndPerRank[i]]+1, "tN: ", lineStr.split()[0])
        #                 tN = lineStr.split()[0]
        #                 timeDIR = os.path.join(self.snapsDIR, tN)
        #                 make_dir(timeDIR)
        #                 cloudFILE = os.path.join(timeDIR, 'cloud_'+self.fieldNAME+'.xy')
        #                 #- Format lines to mimic cloud data set
        #                 if self.nv == 1:
        #                     fieldStr = lineStr.split()[1:]
        #                     with open(cloudFILE, 'w') as fout:
        #                         fout.write('\n'.join(fieldStr))
        #                 elif self.nv > 1:
        #                     fieldStr = re.findall('\(([^)]+)', lineStr)
        #                     with open(cloudFILE, 'w') as fout:
        #                         fout.write(('\n'.join(fieldStr)).replace(' ', '\t'))
        #             elif lineNinFile > lineN:
        #                 break

        #- Option [2]
        lineNInRank = [timeIndFull[self.timeIndPerRank[i]]+self.nHeader+1
                                for i in range(ntPerRank)]
        for n in lineNInRank:
            with open(self.fieldFILE, 'r') as f:
                for line in islice(f, n-1, n):
                    self._formatLine(line)

    def _formatLine(self, line):
        tN = line.split()[0]
        #- Use 'tN' as the directory name for the output file
        timeDIR = os.path.join(self.snapsDIR, tN)
        make_dir(timeDIR)
        #- Write to cloud file with each element in a new line
        cloudFILE = os.path.join(timeDIR, 'cloud_'+self.fieldNAME+'.xy')
        with open(cloudFILE, 'w') as fout:
            if self.nv == 1:
                fieldStr = line.split()[1:]
                fout.write('\n'.join(fieldStr))
            elif self.nv > 1:
                fieldStr = re.findall('\(([^)]+)', line)
                fout.write(('\n'.join(fieldStr)).replace(' ', '\t'))

    def _scatterTime(self):
        #- Get number of time steps from number of lines in file
        with open(self.fieldFILE, 'rb') as f:
            self.nt = sum(1 for _ in f)-self.nHeader
        if self.nt <= 0:
            print("WARNING: Nothing to read in {0}".format(self.fieldFILE))
            comm.abort()
        #- Scatter time steps across processes    
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
            #-
            ntPerRank = [len(tList) for tList in self.timeIndPerRank]
            # print(# "Rank   : ", MPI_RANK, '\n'
            #       "subDIR : ", os.path.basename(os.path.normpath(self.probesSUBDIR)), '\n'
            #       "Field  : ", self.fieldNAME, '\n'
            #       "Value  : ", ntPerRank, "=", sum(ntPerRank), "of", self.nt)
        else:
            self.timeIndPerRank = None
        self.timeIndPerRank = comm.scatter(self.timeIndPerRank, root=0)

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    CLI = argparse.ArgumentParser()
    CLI.add_argument('-p', '--probesSUBDIR', 
                    help="Probe sub-directory", 
                    nargs='?', 
                    type=str)
    CLI.add_argument('-f', '--fieldNAME', 
                    help="Field name", 
                    nargs='?', # '*'
                    type=str,
                    default='U')
    CLI.add_argument('-c', '--coordFILE', 
                    help="Output coordinates file", 
                    nargs='?', 
                    type=str)
    try:
        args = CLI.parse_args()
    except SystemExit:
        print("Check inputs")
        quit()
    p = splitProbe2TimeDir(args.probesSUBDIR,
                           args.fieldNAME,
                           args.coordFILE)
    p.getCoordinates()
    p.getCloud()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()