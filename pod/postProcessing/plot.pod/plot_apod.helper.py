#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 25/02/2022
# ---------------------------------------------------------------------------
""" 
Helper script to read binary files for gnuplot
SEE: https://stackoverflow.com/a/18599896
"""

import numpy as np
import sys

#- Read arguments
#- >> plot_apod.helper.py [chronos] [times]
aFile = sys.argv[1]
tFile = sys.argv[2]

#- Time steps
nt = len(open(tFile).readlines(  ))

#- Reshape and save
#- SEE: https://numpy.org/doc/stable/reference/arrays.dtypes.html
np.savetxt(sys.stdout.buffer, np.fromfile(aFile, dtype='d').reshape(nt, -1))