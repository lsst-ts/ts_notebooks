#!/usr/bin/env python                                                                                                           
# Python code for running PTC 
# on ComCam data.                                                               
#                                                                                                                               
# Initially written 14 Aug 2020 by Craig Lage.                                                                                 
# Imports
import os, sys, time, datetime, glob, subprocess, argparse
import matplotlib.pyplot as plt
import numpy as np
import pickle as pkl
import astropy.io.fits as pf
from lsst.daf.persistence import Butler

# Set up things at the beginning
# and parse input argments
DATA_DIR = '/project/shared/auxTel/' # This is the data
parser = argparse.ArgumentParser()

parser.add_argument('--dayObs', help='Date: Format 2020-08-13')
parser.add_argument('--firstBias', help='First PTC bias expId')
parser.add_argument('--lastBias', help='Last PTC bias expId')
parser.add_argument('--firstFlat', help='First PTC flat pair expId')
parser.add_argument('--lastFlat', help='Last PTC flat pair expId')
args = parser.parse_args()
dayObs = args.dayObs
firstBias = int(args.firstBias)
lastBias = int(args.lastBias)
firstFlat = int(args.firstFlat)
lastFlat = int(args.lastFlat)

numPairsWanted='All'

def setupFlatPairs(repo_dir, dayObs, raft, sensor, numPairsWanted):
    # Subroutine to setup flat pairs 
    butler = Butler(repo_dir)
    visits = butler.queryMetadata('raw', ['expId', 'EXPTIME', 'imagetype'], dayObs=dayObs)
    visits.sort(key=lambda x: x[0])
    foundPairs = []
    for i, (expId,exptime,imgtype) in enumerate(visits):
        if expId < firstFlat or expId > lastFlat - 1:
            continue
        if imgtype == 'FLAT':
            (nextexpId, nextexptime, nextimgtype) = visits[i+1]
            if nextimgtype == 'FLAT' and nextexptime == exptime:
                foundPairs.append([float(exptime),[expId, nextexpId]])
                print([float(exptime),[expId, nextexpId]])
        else:
            continue
    # Sort according to exposure time                                                                                                     
    # and keep just numPairsWanted of all of the pairs                                                                                 
    foundPairs.sort(key=lambda x: x[0])
    numPairs = len(foundPairs)
    pairs = []
    pairString = ''
    if numPairsWanted  == 'All':
        skipNum = 1
        numPairsWanted = numPairs
    else:
        numPairsWanted = int(numPairsWanted)
        skipNum = int(numPairs / numPairsWanted)
    counter = 0
    while (len(pairs) < numPairsWanted) and counter < numPairs:
        if counter != 0:
            pairString += '^'
        pairString += str(foundPairs[counter][1][0])+'^'+str(foundPairs[counter][1][1])
        pairs.append(foundPairs[counter][1])
        counter += skipNum
    print('There are %d flat pairs'%len(pairs))
    return pairString

def detector(raft, sensor):
    # Subroutine to find vendor and detector number given raft and sensor
    # This is specific to ComCam
    return 'ITL', 0

def runCommand(cmd):
    # Run a command with subprocess
    print('Running command %s\n'%cmd)
    sys.stdout.flush()
    thisStep = subprocess.Popen(cmd, shell=True)
    subprocess.Popen.wait(thisStep)
    return

RAFT = 'R22'
SENSOR = 'S00'

# Create the output directory
RERUN_DIR = DATA_DIR+'rerun/cslage/PTC_%s'%dayObs
cmd = 'mkdir -p %s'%RERUN_DIR
runCommand(cmd)
# Get the flat pairs
pairString = setupFlatPairs(DATA_DIR, dayObs, RAFT, SENSOR, numPairsWanted)
print(pairString)

CALIB_DIR = RERUN_DIR + '/CALIB'
cmd = 'mkdir -p %s'%CALIB_DIR
runCommand(cmd)

# First run the master biases
cmd = 'constructBias.py %s --calib %s --rerun %s --batch-type=smp  --cores 8 \
-c isr.doCrosstalk=False isr.doDefect=False \
isr.overscan.fitType=MEDIAN_PER_ROW isr.overscan.order=1 --clobber-config --clobber-versions \
--id expId=%d..%d detector=0'%(DATA_DIR, CALIB_DIR, RERUN_DIR, firstBias, lastBias)
runCommand(cmd)
cmd = 'ingestCalibs.py %s %s/bias/*/*.fits --validity 9999 --calib %s --mode=link \
       --config clobber=True --ignore-ingested'%(DATA_DIR, RERUN_DIR, CALIB_DIR)
runCommand(cmd)

# Now run the ISR task.
cmd = 'runIsr.py %s --rerun %s --calib %s --id detector=0 expId=%s -c isr.doBias=True isr.doDark=False isr.doFringe=False \
isr.doSuspect=True isr.doDefect=False isr.overscan.fitType=MEDIAN_PER_ROW isr.overscan.order=1 isr.doFlat=False \
isr.doCrosstalk=False isr.edgeMaskLevel=AMP isr.numEdgeSuspect=10 --clobber-config --clobber-versions -j 8'%(DATA_DIR, RERUN_DIR, CALIB_DIR, pairString)    
runCommand(cmd)

# Now run the PTC task
cmd = 'measurePhotonTransferCurve.py %s --rerun %s --id detector=0 expId=%s \
 -c ptcFitType=EXPAPPROXIMATION doPhotodiode=False --clobber-config --clobber-versions -j 1'%(RERUN_DIR, RERUN_DIR, pairString)
runCommand(cmd)

# Now plot the results
datasetFileName = '%s/calibrations/ptc/ptcDataset-det000.fits'%(RERUN_DIR)
cmd = 'plotPhotonTransferCurve.py %s --rerun %s  --id detector=0  -c datasetFileName=%s\
       --clobber-versions --clobber-config'%(RERUN_DIR, RERUN_DIR,  datasetFileName)
runCommand(cmd)
