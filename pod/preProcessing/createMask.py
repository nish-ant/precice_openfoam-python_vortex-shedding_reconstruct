#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 21/12/2021
# ---------------------------------------------------------------------------
""" 
Generate mask points
"""

import numpy as np
import sys
import os
import pandas as po
import json

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
class spatialFilter():
    def __init__(self, maskRegion, fp):
        self.maskRegion = maskRegion
        self.fp = fp

    def maskPoints(self):
        #- Coordinates
        coordOutFILE = self.fp['coordOutFILE']
        if coordOutFILE.endswith('.dat'):
            useInd = [1,2,3]
        elif coordOutFILE.endswith('.xy'):
            useInd = [0,1,2]
        ptCloud = po.read_csv(coordOutFILE, 
                          delim_whitespace=True, 
                          header=None, 
                          # names=['x', 'y', 'z'], 
                          usecols=useInd).to_numpy()

        #- Index of points to mask
        self.maskInd = []
        maskFilter = np.zeros((ptCloud.shape[0], ), dtype=bool)
        offset = 0.005
        minxyz = np.array(self.maskRegion['minBound'])+offset
        maxxyz = np.array(self.maskRegion['maxBound'])+offset
        for pind, p in enumerate(ptCloud):
            if (p>=minxyz).all() and (p<=maxxyz).all():
                self.maskInd.append(pind)
                maskFilter[pind] = 1

        #- Apply mask
        self.coordMask = ptCloud[~maskFilter]
        
        # nptsMask = len(self.maskInd)
        # print('Points to mask: {0:d}'.format(nptsMask, ))

    def savedat(self):
        #- Precision and format of saved coordinates
        prec = '%.3f '
        ncoords = self.coordMask.shape[1] # 3

        #- Save data
        coordMaskFILE = self.fp['coordMaskFILE']
        np.savetxt(coordMaskFILE, self.coordMask, fmt=prec*ncoords) 
        # print('Saved: {0:s}'.format(coordMaskFILE, ))

        #- Save masked index
        coordMaskIndFILE = self.fp['coordMaskIndFILE']
        np.savetxt(coordMaskIndFILE, np.array(self.maskInd), fmt='%d')
        # with open(coordMaskIndFILE, 'w') as f:
        #     f.write('\n'.join(str(ind) for ind in self.maskInd))
        # print('Saved: {0:s}'.format(coordMaskIndFILE, ))

        #- Save parameters
        npts = self.coordMask.shape[0]
        with open(coordMaskFILE+'.prm', 'w') as fp:
            json.dump({'npts': npts}, fp, indent=4)
            json.dump(self.maskRegion, fp, indent=4, sort_keys=True)

# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def main():
    #- Parse arguments
    fp = {}
    fp['coordOutFILE'] = sys.argv[1]
    fp['coordMaskFILE'] = sys.argv[2] #- To export coordinates
    fp['coordMaskIndFILE'] = sys.argv[3] #- To export indices

    #- Define region to mask (e.g. to exclude from POD calculation)
    #- NOTE: Currently only accepts a box region with min-max bounds
    maskRegion = {}
    maskRegion['minBound'] = [400., 1065., 0.]
    maskRegion['maxBound'] = [2800., 1935., 500.]

    p = spatialFilter(maskRegion, fp)
    p.maskPoints()
    p.savedat()

# ---------------------------------------------------------------------------
# COMMAND LINE EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()