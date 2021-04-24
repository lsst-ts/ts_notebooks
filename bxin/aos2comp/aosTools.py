import os
import asyncio
import numpy as np

import pandas as pd
from matplotlib import pyplot as plt

from M1M3_FATABLE import *

from lsst.ts.idl.enums import MTM1M3

m3ORC = 2.508
m3IRC = 0.550
m1ORC = 4.18
m1IRC = 2.558

fat = np.array(FATABLE)
m1m3_actID = np.int16(fat[:, FATABLE_ID])
m1m3_nActuator = m1m3_actID.shape[0]
m1m3_xact = np.float64(fat[:, FATABLE_XPOSITION])
m1m3_yact = np.float64(fat[:, FATABLE_YPOSITION])

aa = np.loadtxt('%s/notebooks/M2_FEA/data/M2_1um_72_force.txt'%(os.environ["HOME"]))
# to have +x going to right, and +y going up, we need to transpose and reverse x and y
m2_xact = -aa[:,2]
m2_yact = -aa[:,1]


async def lowerM1M3(m1m3):
    m1m3.evt_detailedState.flush()
    await m1m3.cmd_lowerM1M3.set_start(lowerM1M3=True, timeout = 30)
    while True:
        state = await m1m3.evt_detailedState.next(flush=False, timeout=300)
        print('m1m3 state', MTM1M3.DetailedState(state.detailedState), pd.to_datetime(state.private_sndStamp, unit='s'))
        if (MTM1M3.DetailedState(state.detailedState) == MTM1M3.DetailedState.PARKED
                or MTM1M3.DetailedState(state.detailedState) == MTM1M3.DetailedState.PARKEDENGINEERING):
            break

async def raiseM1M3(m1m3):
    m1m3.evt_detailedState.flush()
    await m1m3.cmd_raiseM1M3.set_start(raiseM1M3=True, timeout = 30)
    while True:
        state = await m1m3.evt_detailedState.next(flush=False, timeout=300)
        print('m1m3 state', MTM1M3.DetailedState(state.detailedState), pd.to_datetime(state.private_sndStamp, unit='s'))
        if (MTM1M3.DetailedState(state.detailedState) == MTM1M3.DetailedState.ACTIVE
                or MTM1M3.DetailedState(state.detailedState) == MTM1M3.DetailedState.ACTIVEENGINEERING):
            break
        
async def plotM1M3Forces(m1m3):
    
    fel = await m1m3.evt_appliedElevationForces.aget(timeout=10.)
    fba = await m1m3.evt_appliedBalanceForces.aget(timeout=10.)
    fst = await m1m3.evt_appliedStaticForces.aget(timeout=10.)
    fao = await m1m3.evt_appliedActiveOpticForces.aget(timeout=10.)
    
    ftel = await m1m3.tel_forceActuatorData.aget(timeout=10.)
    
    fig, ax = plt.subplots(3,1, figsize=(15,8))
    ax[0].plot(fel.xForces, '-o', label='elevation');
    ax[0].plot(fba.xForces, label='FB')
    ax[0].plot(fst.xForces, label='static')
    ax[0].plot(ftel.xForce, '-v', label='measured')
    ax[0].legend()
    ax[0].set_title('XForces')
    ax[1].plot(fel.yForces, '-o', label='elevation');
    #ax[1].plot(fba.yForces, label='FB')
    #ax[1].plot(fst.yForces, label='static')
    ax[1].plot(ftel.yForce, '-v', label='measured')
    ax[1].legend()
    ax[1].set_title('YForces')
    ax[2].plot(fel.zForces, '-o', label='elevation');
    ax[2].plot(fba.zForces, label='FB')
    ax[2].plot(fst.zForces, label='static')
    ax[2].plot(fao.zForces, label='AOS')
    ax[2].plot(ftel.zForce, '-v', label='measured')
    ax[2].set_title('ZForces')
    ax[2].legend()
    
    fig2, ax=plt.subplots( 1,3, figsize = [15,4])
    aa = np.array(fao.zForces)
    img = ax[0].scatter(m1m3_xact, m1m3_yact, c=aa, s=abs(aa)*2)
    #plt.jet()
    ax[0].axis('equal')
    ax[0].set_title('AOS forces')
    fig.colorbar(img, ax=ax[0])

    aa = np.array(fel.zForces)
    img = ax[1].scatter(m1m3_xact, m1m3_yact, c=aa, s=abs(aa)*0.1)
    #plt.jet()
    ax[1].axis('equal')
    ax[1].set_title('elevation forces')
    fig.colorbar(img, ax=ax[1])
    
    aa = np.array(fst.zForces)
    img = ax[2].scatter(m1m3_xact, m1m3_yact, c=aa, s=abs(aa)*10)
    #plt.jet()
    ax[2].axis('equal')
    ax[2].set_title('static forces')
    fig.colorbar(img, ax=ax[2])
    
async def plotM2Forces(m2):
    
    axialForces = await m2.tel_axialForce.aget(timeout=2)
    tangentForces = await m2.tel_tangentForce.aget(timeout=2)

    fig, ax = plt.subplots(2,1, figsize=(15,8))
    ax[0].plot(axialForces.measured, label='measured');
    ax[0].plot(axialForces.applied, label='applied');
    ax[0].plot(axialForces.hardpointCorrection,'.', label='FB');
    ax[0].plot(axialForces.lutGravity, label='LUT G');
    ax[0].legend()
    ax[1].plot(tangentForces.measured, label='measured');
    ax[1].plot(tangentForces.applied, label='applied');
    ax[1].plot(tangentForces.hardpointCorrection, 'o', label='FB');
    ax[1].plot(tangentForces.lutGravity, label='LUT G');
    ax[1].legend()

    fig2, ax=plt.subplots( 1,2, figsize = [10,4])
    aa = np.array(axialForces.measured)
    img = ax[0].scatter(m2_xact, m2_yact, c=aa, s=abs(aa)*2)
    #plt.jet()
    ax[0].axis('equal')
    ax[0].set_title('measured forces')
    fig.colorbar(img, ax=ax[0])

    aa = np.array(axialForces.applied)
    img = ax[1].scatter(m2_xact, m2_yact, c=aa, s=abs(aa)*2)
    #plt.jet()
    ax[1].axis('equal')
    ax[1].set_title('applied forces')
    fig.colorbar(img, ax=ax[1])    
    

async def readyHexForAOS(hex):
    settings = hex.evt_settingsApplied.get()
    print(settings.settingsVersion)
    if not settings.settingsVersion[:12] == 'default.yaml':
        print('YOU NEED TO SEND THIS HEXAPOD TO STANDBY, THEN LOAD THE PROPER CONFIG')
    else:
        lutMode = await hex.evt_compensationMode.aget(timeout=10)
        if not lutMode.enabled:
            await hex.cmd_setCompensationMode.set_start(enable=1, timeout=10)
        print("compsensation mode enabled?",lutMode.enabled, pd.to_datetime(lutMode.private_sndStamp, unit='s'))
        print("Does the hexapod has enough inputs to do LUT compensation?")
        #Note: the target events are what the hex CSC checks; if one is missing, the entire LUT will not be applied
        a = hex.evt_compensationOffset.get()
        print(a.elevation, a.azimuth, a.rotation, a.temperature)
        print('x,y,z,u,v,w = ', a.x, a.y, a.z, a.u, a.v, a.w)
        
async def moveHexTo0(hex):
    ### command it to collimated position (based on LUT)
    hex.evt_inPosition.flush()
    #according to XML, units are micron and degree
    await hex.cmd_move.set_start(x=0,y=0,z=0, u=0,v=0,w=0,sync=True)
    while True:
        state = await hex.evt_inPosition.next(flush=False, timeout=10)
        print("hex in position?",state.inPosition, pd.to_datetime(state.private_sndStamp, unit='s'))
        if state.inPosition:
            break
    await printHexPosition(hex)
    
async def printHexPosition(hex):
    pos = await hex.tel_application.next(flush=True, timeout=10.)
    print("Current Hexapod position")
    print(" ".join(f"{p:10.2f}" for p in pos.position[:3]), end = ' ') 
    print(" ".join(f"{p:10.6f}" for p in pos.position[3:]) )
    
async def printHexUncompensatedAndCompensated(hex):
    posU = await hex.evt_uncompensatedPosition.aget(timeout=10.)
    print('Uncompensated position')
    print(" ".join(f"{p:10.2f}" for p in [getattr(posU, i) for i in 'xyz']), end = '    ')
    print(" ".join(f"{p:10.6f}" for p in [getattr(posU, i) for i in 'uvw']),'  ',
         pd.to_datetime(posU.private_sndStamp, unit='s'))    
    posC = await hex.evt_compensatedPosition.aget(timeout=10.)
    print('Compensated position')
    print(" ".join(f"{p:10.2f}" for p in [getattr(posC, i) for i in 'xyz']), end = '     ')
    print(" ".join(f"{p:10.6f}" for p in [getattr(posC, i) for i in 'uvw']),'  ',
         pd.to_datetime(posC.private_sndStamp, unit='s'))


