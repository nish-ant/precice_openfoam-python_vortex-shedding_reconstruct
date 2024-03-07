#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : Nishant Kumar
# Created Date: 16/02/2023
# ---------------------------------------------------------------------------
"""
Low-fidelity solver 
"""
from __future__ import division, print_function

import numpy as np
import pandas as po
import scipy.linalg as la
import os
import argparse
from pathlib import Path
# import h5py

import precice
from precice import action_write_initial_data, \
                    action_read_iteration_checkpoint, \
                    action_write_iteration_checkpoint

# ---------------------------------------------------------------------------
# UTILITY FUNCTION(S)
# ---------------------------------------------------------------------------
def make_dir(dirPATH):
    #- Check and make directory path
    Path(dirPATH).mkdir(parents=True, exist_ok=True)

def loadSerialCSV(fileID):
    #- Read the contents of a csv file in serial and return
    return np.squeeze(po.read_csv(fileID, 
                                  header=None, 
                                  delim_whitespace=True).to_numpy())

def saveCoeff(t, coeffs):
    aPressure = coeffs[0]
    aVelocity = coeffs[1]
    aTKE = coeffs[2]
    aOmega = coeffs[3]
    aNut = coeffs[4]

    # chronosPATH = os.path.join('.','chronos')
    # chronosFILE = os.path.join(chronosPATH,'chronos.h5')
    # with h5py.File(chronosFILE, 'a') as f:
    #     grp = f.create_group('{0:.2f}'.format(t))
    #     grp.create_dataset("p", aPressure, dtype='f')
    #     grp.create_dataset("U", aPressure, dtype='f')

    chronosPATH = os.path.join('.','chronos','{0:.2f}'.format(t))
    make_dir(chronosPATH)

    np.savetxt(os.path.join(chronosPATH, 'p'), aPressure, delimiter="\t")
    np.savetxt(os.path.join(chronosPATH, 'U'), aVelocity, delimiter="\t")
    np.savetxt(os.path.join(chronosPATH, 'k'), aTKE, delimiter="\t")
    np.savetxt(os.path.join(chronosPATH, 'omega'), aOmega, delimiter="\t")
    np.savetxt(os.path.join(chronosPATH, 'nut'), aNut, delimiter="\t")

# ---------------------------------------------------------------------------
# SUBFUNCTION(S)
# ---------------------------------------------------------------------------
def solveMin(A, b):
    #- Compute a vector x such that the 2-norm |b - Ax| is minimized
    #- Returns: x (and residues b - Ax, rank of A, singular values of A)
    x, _, _, _ = la.lstsq(A, b, 
                        cond=None, 
                        overwrite_a=False, 
                        overwrite_b=False, 
                        check_finite=True, 
                        lapack_driver=None)
    return x

def locateOverlap(overlapgrid, lfgrid):
    #- Return index in lfgrid that corresponds to overlapgrid, in same order
    #- Round to remove effect of offset (~0.001)
    overlapgrid = overlapgrid.round(decimals=2)
    lfgrid = lfgrid.round(decimals=2)
    #- Locate indices
    indOverlap = []
    for p in overlapgrid:
        if (p==lfgrid).all(axis=1).any():
            indOverlap.append(np.where((p==lfgrid).all(axis=1))[0][0])
        else:
            print("WARNING: Overlap node ", p, " not found in LF mesh")
            indOverlap.append(None)
    #- Indices of stacked vector array
    lfnPts = lfgrid.shape[0]
    indOverlapVec = []
    for i in range(3):
        for ind in indOverlap:
            indOverlapVec.append(ind+i*lfnPts)
    return indOverlap, indOverlapVec

# ---------------------------------------------------------------------------
# INPUT
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='LF solver')
parser.add_argument('-c', '--configurationFileName', 
                    help="Name of the xml config file.", 
                    nargs='?', 
                    type=str,
                    default="precice-config.xml")
parser.add_argument('-p', '--parentDIR', 
                    help="Location where the code is launched.", 
                    nargs='?', 
                    type=str)

try:
    args = parser.parse_args()
except SystemExit:
    print("preCICE configuration file not specified")
    quit()

nModes = 6
tStart = 100
dtSnap = 0.001 # 0.005
dt = dtSnap
snapsPATH = os.path.join(args.parentDIR,'..','hf-openfoam-galfree')
podPATH = os.path.join(args.parentDIR,'..','..', \
                      'pod','pod.np64_p-U-k-nut-omega_N6.run.overlap.hf')
lfmeshFILE = os.path.join(args.parentDIR,'..','..', \
                      'run.simuation_snapshots','system','sampling','pointCloud.xy')

# ---------------------------------------------------------------------------
# preCICE coupling
# ---------------------------------------------------------------------------
solver_process_index = 0
solver_process_size = 1
interface = precice.Interface("lf", 
                              args.configurationFileName,
                              solver_process_index,
                              solver_process_size)

dimensions = interface.get_dimensions()

#- Read snapshots and coordinates data
fieldDIR = os.path.join(snapsPATH,'postProcessing','internalField')
# fieldDIR = os.path.join(snapsPATH,'postProcessing','boundaryField')

#- Read overlap mesh
snapTimeDIR = os.path.join(fieldDIR, '{0:.12g}'.format(tStart))
snapData = loadSerialCSV(os.path.join(snapTimeDIR, 'cloud_p_k_omega_nut.xy'))
#-
overlapgrid = snapData[:, :3]
overlapnPts = overlapgrid.shape[0]
#- Locate overlap domain
lfgrid = loadSerialCSV(lfmeshFILE)
lfnPts = lfgrid.shape[0]
indOverlap, indOverlapVec = locateOverlap(overlapgrid, lfgrid)

#- Read field at t=0
pressure = snapData[:, 3]
tke = snapData[:, 4]
omega = snapData[:, 5]
nut = snapData[:, 6]
#-
snapData = loadSerialCSV(os.path.join(snapTimeDIR, 'cloud_U.xy'))
velocity = snapData[:, 3:]
#-
# pressure = pressure[:, None]
velocity = velocity.reshape((overlapnPts*3, 1), order='F')

#- Read POD data
modePressure = np.fromfile(os.path.join(podPATH, 'modes.p', 'mode.bin'), dtype=float)
modeVelocity = np.fromfile(os.path.join(podPATH, 'modes.U', 'mode.bin'), dtype=float)
modeTKE = np.fromfile(os.path.join(podPATH, 'modes.k', 'mode.bin'), dtype=float)
modeOmega = np.fromfile(os.path.join(podPATH, 'modes.omega', 'mode.bin'), dtype=float)
modeNut = np.fromfile(os.path.join(podPATH, 'modes.nut', 'mode.bin'), dtype=float)
#- 
modePressure = modePressure.reshape((nModes, lfnPts*1)).T
modeVelocity = modeVelocity.reshape((nModes, lfnPts*3)).T
modeTKE = modeTKE.reshape((nModes, lfnPts*1)).T
modeOmega = modeOmega.reshape((nModes, lfnPts*1)).T
modeNut = modeNut.reshape((nModes, lfnPts*1)).T
#- 
modePressure = modePressure[indOverlap,:]
modeVelocity = modeVelocity[indOverlapVec,:]
modeTKE = modeTKE[indOverlap,:]
modeOmega = modeOmega[indOverlap,:]
modeNut = modeNut[indOverlap,:]

#- Mesh information
lfmeshID = interface.get_mesh_id("lf-Mesh")
hfmeshID = interface.get_mesh_id("hf-Mesh")
pressureGradientID = interface.get_data_id("PressureGradient", lfmeshID)
pressureID = interface.get_data_id("Pressure", lfmeshID)
velocityID = interface.get_data_id("Velocity", lfmeshID)
# tkeID = interface.get_data_id("TKE", lfmeshID)
# omegaID = interface.get_data_id("TurbulentSpecificDissipationRate", lfmeshID)
# nutID = interface.get_data_id("EddyViscosity", lfmeshID)
vertexIDs = interface.set_mesh_vertices(lfmeshID, overlapgrid)

t = tStart
it = 0

#- preCICE defines timestep size of solver via precice-config.xml
precice_dt = interface.initialize()

if interface.is_read_data_available():
    pressureGradient = interface.read_block_scalar_data(pressureGradientID, vertexIDs)

if interface.is_action_required(action_write_initial_data()):
    #- Calculate coefficient at t=0
    aPressure = solveMin(modePressure.T@modePressure, modePressure.T@pressure)
    aVelocity = solveMin(modeVelocity.T@modeVelocity, modeVelocity.T@velocity)
    aTKE = solveMin(modeTKE.T@modeTKE, modeTKE.T@tke)
    aOmega = solveMin(modeOmega.T@modeOmega, modeOmega.T@omega)
    aNut = solveMin(modeNut.T@modeNut, modeNut.T@nut)
    saveCoeff(t, [aPressure, aVelocity, aTKE, aOmega, aNut])

    predPressure = modePressure@aPressure #- .T + modePressure[:, 0, None]
    predVelocity = modeVelocity@aVelocity #- .T + modeVelocity[:, 0, None]
    predTKE = modeTKE@aTKE #- .T + modeTKE[:, 0, None]
    predOmega = modeOmega@aOmega #- .T + modeOmega[:, 0, None]
    predNut = modeNut@aNut #- .T + modeNut[:, 0, None]
    #-
    predPressure = predPressure.squeeze()
    predVelocity = predVelocity.reshape((overlapnPts, 3), order='F')
    predTKE = predTKE.squeeze()
    predOmega = predOmega.squeeze()
    predNut = predNut.squeeze()

    interface.write_block_scalar_data(pressureID, vertexIDs, predPressure)
    interface.write_block_vector_data(velocityID, vertexIDs, predVelocity)
    # interface.write_block_scalar_data(tkeID, vertexIDs, predTKE)
    # interface.write_block_scalar_data(omegaID, vertexIDs, predOmega)
    # interface.write_block_scalar_data(nutID, vertexIDs, predNut)
    interface.mark_action_fulfilled(action_write_initial_data())

interface.initialize_data()

while interface.is_coupling_ongoing():
    #- When an implicit coupling scheme is used, checkpointing is required
    if interface.is_action_required(action_write_iteration_checkpoint()):
        interface.mark_action_fulfilled(action_write_iteration_checkpoint())

    if interface.is_read_data_available():
        pressureGradient = interface.read_block_scalar_data(pressureGradientID, vertexIDs)

    if interface.is_write_data_required(precice_dt):
        snapTimeDIR = os.path.join(fieldDIR, '{0:.12g}'.format(t))
        snapData = loadSerialCSV(os.path.join(snapTimeDIR, 'cloud_p_k_omega_nut.xy'))
        pressure = snapData[:, 3]
        tke = snapData[:, 4]
        omega = snapData[:, 5]
        nut = snapData[:, 6]
        snapData = loadSerialCSV(os.path.join(snapTimeDIR, 'cloud_U.xy'))
        velocity = snapData[:, 3:]
        #-
        # pressure = pressure[:, None]
        velocity = velocity.reshape((overlapnPts*3, 1), order='F')

        #- Calculate coefficient (t=t_it)
        aPressure = solveMin(modePressure.T@modePressure, modePressure.T@pressure)
        aVelocity = solveMin(modeVelocity.T@modeVelocity, modeVelocity.T@velocity)
        aTKE = solveMin(modeTKE.T@modeTKE, modeTKE.T@tke)
        aOmega = solveMin(modeOmega.T@modeOmega, modeOmega.T@omega)
        aNut = solveMin(modeNut.T@modeNut, modeNut.T@nut)
        saveCoeff(t, [aPressure, aVelocity, aTKE, aOmega, aNut])

        predPressure = modePressure@aPressure #- .T + modePressure[:, 0, None]
        predVelocity = modeVelocity@aVelocity #- .T + modeVelocity[:, 0, None]
        predTKE = modeTKE@aTKE #- .T + modeTKE[:, 0, None]
        predOmega = modeOmega@aOmega #- .T + modeOmega[:, 0, None]
        predNut = modeNut@aNut #- .T + modeOmega[:, 0, None]
        #- 
        predPressure = predPressure.squeeze()
        predVelocity = predVelocity.reshape((overlapnPts, 3), order='F')
        predTKE = predTKE.squeeze()
        predOmega = predOmega.squeeze()
        predNut = predNut.squeeze()

    if interface.is_action_required(action_write_iteration_checkpoint()):
        interface.mark_action_fulfilled(action_write_iteration_checkpoint())

    interface.write_block_scalar_data(pressureID, vertexIDs, predPressure.squeeze())
    interface.write_block_vector_data(velocityID, vertexIDs, predVelocity)
    # interface.write_block_scalar_data(tkeID, vertexIDs, predTKE)
    # interface.write_block_scalar_data(omegaID, vertexIDs, predOmega)
    # interface.write_block_scalar_data(nutID, vertexIDs, predNut)

    #- Potentially adjust non-matching timestep sizes
    precice_dt = interface.advance(dt)
    dt = np.min([dt, precice_dt])

    it += 1
    t = tStart + it*dt # dtSnap

    #- Not yet converged
    if interface.is_action_required(action_read_iteration_checkpoint()):
        interface.mark_action_fulfilled(action_read_iteration_checkpoint())
    # #- Converged, timestep complete
    # else: 
    #     t += precice_dt

interface.finalize()
