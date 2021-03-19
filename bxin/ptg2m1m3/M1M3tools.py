import os
import sys
import h5py
import numpy as np
from scipy import interpolate
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta

from os.path import expanduser

from FATABLE import *


m3ORC = 2.508
m3IRC = 0.550
m1ORC = 4.18
m1IRC = 2.558

fat = np.array(FATABLE)
actID = np.int16(fat[:, FATABLE_ID])
nActuator = actID.shape[0]
xact = np.float64(fat[:, FATABLE_XPOSITION])
yact = np.float64(fat[:, FATABLE_YPOSITION])

def get_dataframe_EFD(myt, table_name = 'm1m3_logevent_AppliedForces', dtMinutes=4, doQuery=False):
    [month, day, hour, minute] = myt
    b0 = datetime(2019, month, day, hour, minute, 0)
    b1 = b0 + timedelta(minutes = -dtMinutes/2)
    b2 = b0 + timedelta(minutes = dtMinutes/2)
    #we do not use private_sndStamp to do query, because it is not sequential in the DB !!! takes forever !!!
    # see get_Fxyz_from_EFD.ipynb or forceError.ipynb
    query = 'select * from {0} where {0}.date_time between \'{1}\' and \'{2}\';'.format(table_name, b1, b2)
    namestr = table_name.split('_')[-1]
    if namestr == 'ForceActuatorData':
        namestr = 'MeasuredForces'
    filename = 'efdData/%s_%s.csv'%(namestr, (b1+(b2-b1)/2).strftime("%y%m%d_%H%M"))
    if doQuery or not os.path.isfile(filename):
        print(query)
        if month ==1:
            df1 = pd.read_sql_query(query, engine1)
        elif month ==2:
            df1 = pd.read_sql_query(query, engine2)
        else:
            df1 = pd.read_sql_query(query, engine3)
        if not doQuery:
            df1.to_csv(filename)
    else:
        print('-------Reading from %s-------------'%filename)
        df1 = pd.read_csv(filename,parse_dates=['date_time']) #make sure dtype for date_time column is understood
    return df1

def get_F_EFD(myt, table_name = 'm1m3_logevent_AppliedForces'):
    df1 = get_dataframe_EFD(myt, table_name)
    F = assembleFfromEFD(df1, campn = myt[0])
    return F

def get_F_EFD_C1C2(myt, table_name='m1m3_logevent_AppliedCylinderForces'):
    df1 = get_dataframe_EFD(myt, table_name)
    F = assembleFfromEFD_C1C2(df1, campn = myt[0])
    return F

def assembleFfromEFD(df1, campn = 1, output=0):
    '''
    df1 is a pandas frame, which is result of a query to table m1m3_logevent_AppliedForces
    This assumes x/y/z forces from invidual actuators are stored as separate columns

    output: AVERAGED forces for all records in df1
    col 0: actuator IDs
    col 1: x force
    col 2: y force
    col 3: z force
    '''
    myF = np.zeros((nActuator, 4)) #ID, x, y, z
    myF[:, 0] = actID
    xexist = 1
    yexist = 1
    zexist = 1
    for i in range(nActuator):
        ix = FATABLE[i][FATABLE_XINDEX]
        iy = FATABLE[i][FATABLE_YINDEX]
        if campn == 1:
            try:
                myF[i, 3] = np.mean(df1['ZForces_%d'%(i+1)]) #Fz
            except KeyError:
                myF[i, 3] = np.mean(df1['ZForce_%d'%(i+1)]) #Fz
        elif campn == 2:
            if len(df1.ZForces)>0 and len(df1.ZForces[0].split())==156:
                myF[i, 3] = np.mean([float(df1.ZForces[ii].split()[i])
                       for ii in range(len(df1.ZForces))])
            else:
                zexist = 0
        if ix != -1:
            # x forces in campn 2 were NOT changed into strings. Only y and z forces
            try:
                myF[i, 1] = np.mean(df1['XForces_%d'%(ix+1)]) #Fx, note ix starts with 0
            except KeyError:
                try:
                    myF[i, 1] = np.mean(df1['XForce_%d'%(ix+1)]) #Fx, note ix starts with 0
                except KeyError:
                    xexist = 0
        if iy != -1:
            if campn == 1:
                try:
                    myF[i, 2] = np.mean(df1['YForces_%d'%(iy+1)]) #Fx, note ix starts with 0
                except KeyError:
                    try:
                        myF[i, 2] = np.mean(df1['YForce_%d'%(iy+1)]) #Fx, note ix starts with 0
                    except KeyError:
                        yexist = 0
            elif campn == 2:
                try:
                    myF[i, 2] = np.mean([float(df1.YForces[ii].split()[iy])
                       for ii in range(len(df1.YForces))])
                except AttributeError:
                    zexist = 0
        if output:
            print('%d, %6.1f %6.1f %8.1f'%(myF[i, 0],myF[i, 1],myF[i, 2],myF[i, 3]))

    if not xexist:
        print('---No XForces---')
    if not yexist:
        print('---No YForces---')
    if not zexist:
        print('---No ZForces---')
    return myF

def assembleFfromEFD_C1C2(df1, campn =1, output=0):
    '''
    df1 is a pandas frame, which is result of a query to table m1m3_logevent_AppliedCylinderForces
    This assumes x/y/z forces from invidual actuators are stored as separate columns

    output:
    col 0: actuator IDs
    col 1: x force
    col 2: y force
    col 3: z force
    '''
    myF = np.zeros((nActuator, 4)) #ID, x, y, z
    myF[:, 0] = actID
    for i in range(nActuator):
        idaa = FATABLE[i][FATABLE_SINDEX]
        orientation = FATABLE[i][FATABLE_ORIENTATION]
        if campn == 1:
            fc1 = np.mean(df1['PrimaryCylinderForces_%d'%(i+1)])/1000.
        else:
            fc1 = np.mean([float(df1.PrimaryCylinderForces[ii].split()[i])
                       for ii in range(len(df1.PrimaryCylinderForces))])/1000
        myF[i, 3] = fc1
        if orientation == 'NA':
            pass
        else:
            if campn == 1:
                fc2 = np.mean(df1['SecondaryCylinderForces_%d'%(idaa+1)])/1000.
            else:
                fc2 = np.mean([float(df1.SecondaryCylinderForces[ii].split()[idaa])
                       for ii in range(len(df1.SecondaryCylinderForces))])/1000
            myF[i, 3] += fc2*0.707 #Fz
            if orientation == '+X':
                myF[i, 1] = fc2*0.707
            elif orientation == '-X':
                myF[i, 1] = -fc2*0.707
            elif orientation == '+Y':
                myF[i, 2] = fc2*0.707
            elif orientation == '-Y':
                myF[i, 2] = -fc2*0.707
            else:
                print('--- UNKNOWN CYLINDER 2 ORIENTATION ---')
        if output:
            print('%d, %6.1f %6.1f %8.1f'%(myF[i, 0],myF[i, 1],myF[i, 2],myF[i, 3]))
    return myF

def assembleFinst(df1, campn, output=0):
    '''
    This function extracts force data from the pandas dataframe (df1),
    assign the force values to a multi-dimensional array (myF).
    There is no time average of the forces. We store all the instantaneous forces.
    '''
    nn = len(df1.private_sndStamp)
    myF = np.zeros((nn, nActuator, 4))
    myF[:,:,0] = actID
    xexist = 1
    yexist = 1
    zexist = 1
    for i in range(nActuator):
        ix = FATABLE[i][FATABLE_XINDEX]
        iy = FATABLE[i][FATABLE_YINDEX]
        if campn == 1:
            try:
                myF[:, i, 3] = df1['ZForces_%d'%(i+1)] #Fz
            except KeyError:
                myF[:, i, 3] = df1['ZForce_%d'%(i+1)] #Fz
        else:
            try:
                myF[:, i, 3] = [float(df1.ZForce[ii].split()[i])
                       for ii in range(len(df1.ZForce))]
            except AttributeError:
                try:
                    myF[:, i, 3] = [float(df1.ZForces[ii].split()[i])
                           for ii in range(len(df1.ZForces))]
                except AttributeError:
                    zexist = 0
        if ix != -1:
            # x forces in campn 2 were NOT changed into strings. Only y and z forces
            try:
                myF[:, i, 1] = df1['XForces_%d'%(ix+1)] #Fx, note ix starts with 0
            except KeyError:
                try:
                    myF[:, i, 1] = df1['XForce_%d'%(ix+1)] #Fx, note ix starts with 0
                except KeyError:
                    xexist = 0
        if iy != -1:
            if campn == 1:
                try:
                    myF[:, i, 2] = df1['YForces_%d'%(iy+1)] #Fx, note ix starts with 0
                except KeyError:
                    try:
                        myF[:, i, 2] = df1['YForce_%d'%(iy+1)] #Fx, note ix starts with 0
                    except KeyError:
                        yexist = 0
            else:
                try:
                    myF[:, i, 2] = [float(df1.YForce[ii].split()[iy])
                       for ii in range(len(df1.YForce))]
                except AttributeError:
                    try:
                        myF[:, i, 2] = [float(df1.YForces[ii].split()[iy])
                           for ii in range(len(df1.YForces))]
                    except AttributeError:
                        yexist = 0

    if not xexist:
        print('---No XForces---')
    if not yexist:
        print('---No YForces---')
    if not zexist:
        print('---No ZForces---')
    return myF

