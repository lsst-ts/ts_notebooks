import sys, time, os, asyncio, argparse
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient
from lsst.daf.persistence import Butler

# Bring in Lupton's unpacking code
def merge_packed_time_series(packed_dataframe, base_field, stride=1, 
                             ref_timestamp_col="cRIO_timestamp", internal_time_scale="tai"):
    """Select fields that are time samples and unpack them into a dataframe.
            Parameters
            ----------
            packedDF : `pandas.DataFrame`
                packed data frame containing the desired data
            base_field : `str`
                Base field name that will be expanded to query all
                vector entries.
            stride : `int`, optional
                Only use every stride value when unpacking.  Must be a factor
                of the number of packed values.
                (1 by default)
            ref_timestamp_col : `str`, optional
                Name of the field name to use to assign timestamps to unpacked
                vector fields (default is 'cRIO_timestamp').
            internal_time_scale : `str`, optional
                Time scale to use when converting times to internal formats
                ('tai' by default). Equivalent to EfdClient.internal_scale
        Returns
            -------
            result : `pandas.DataFrame`
                A `pandas.DataFrame` containing the results of the query.
            """
    
    packed_fields = [k for k in packed_dataframe.keys() if k.startswith(base_field)]
    packed_fields = sorted(packed_fields, key=lambda k: int(k[len(base_field):]))  # sort by pack ID
    npack = len(packed_fields)
    if npack%stride != 0:
        raise RuntimeError(f"Stride must be a factor of the number of packed fields: {stride} v. {npack}")
    packed_len = len(packed_dataframe)
    n_used = npack//stride   # number of raw fields being used
    output = np.empty(n_used*packed_len)
    times = np.empty_like(output, dtype=packed_dataframe[ref_timestamp_col][0])
    
    if packed_len == 1:
        dt = 0
    else:
        dt = (packed_dataframe[ref_timestamp_col][1] - packed_dataframe[ref_timestamp_col][0])/npack
    for i in range(0, npack, stride):
        i0 = i//stride
        output[i0::n_used] = packed_dataframe[f"{base_field}{i}"]
        times[i0::n_used] = packed_dataframe[ref_timestamp_col] + i*dt
     
    timestamps = Time(times, format='unix', scale=internal_time_scale).datetime64
    return pd.DataFrame({base_field:output, "times":times}, index=timestamps)

# This routine does the tracking and creates the graph
async def MountTracking(expId, fail_limit=0.5, makeGraph=True):
    start = time.time()
    """Queries the EFD for a given exposure and checks if there were tracking errors
            Parameters
            ----------
            expId : `int`
                The expId of the exposure being tested
            fail_limit : `float`, optional
                Will fail if RMS error of any of the three axes is greater
                than this value in arcseconds
            makeGraph : `bool`, optional
                Whether or not to make the graphs
        Returns
            -------
            result : `bool`
               True if tracking errors are all less than fail_limit
            """

    # Find the time of exposure
    REPO_DIR = '/readonly/lsstdata/auxtel/base/auxtel/oods/butler/repo'
    butler = Butler(REPO_DIR)
    mData = butler.get('raw', dataId={'detector':0, 'expId':expId}).getMetadata()
    imgType = mData['IMGTYPE']
    expTime = mData['EXPTIME']
    if (imgType not in ['OBJECT', 'SKYEXP', 'ENGTEST']) or (expTime < 1.0):
        return True
    tStart = mData['DATE-BEG']
    tEnd = mData['DATE-END']
    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for butler query = {elapsed}")
    start = time.time()

    # Get the data
    client = EfdClient('summit_efd')
    t_start = Time(tStart, scale='tai')
    t_end = Time(tEnd, scale='tai')
    mount_position = await client.select_time_series("lsst.sal.ATMCS.mount_AzEl_Encoders", ['*'],
                                              t_start, t_end)
    nasmyth_position = await client.select_time_series("lsst.sal.ATMCS.mount_Nasmyth_Encoders", ['*'],
                                              t_start, t_end)
    time.sleep(5.0)
    az = merge_packed_time_series(mount_position, 'azimuthCalculatedAngle', stride=1)
    el = merge_packed_time_series(mount_position, 'elevationCalculatedAngle', stride=1)
    rot = merge_packed_time_series(nasmyth_position, 'nasmyth2CalculatedAngle', stride=1)  

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time to get the data = {elapsed}")
    start = time.time()

    # Calculate the tracking errors
    az_vals = np.array(az.values.tolist())[:,0]
    el_vals = np.array(el.values.tolist())[:,0]
    rot_vals = np.array(rot.values.tolist())[:,0]
    times = np.array(az.values.tolist())[:,1]
    times = times - times [0]

    # Fit with a quadratic
    az_fit = np.polyfit(times, az_vals, 2)
    el_fit = np.polyfit(times, el_vals, 2)
    rot_fit = np.polyfit(times, rot_vals, 2)
    az_model = az_fit[0] * times * times + az_fit[1] * times + az_fit[2]
    el_model = el_fit[0] * times * times + el_fit[1] * times + el_fit[2]
    rot_model = rot_fit[0] * times * times + rot_fit[1] * times + rot_fit[2]

    # Errors in arcseconds
    az_error = (az_vals - az_model) * 3600
    el_error = (el_vals - el_model) * 3600
    rot_error = (rot_vals - rot_model) * 3600

    # Calculate RMS
    az_rms = np.sqrt(np.mean(az_error * az_error))
    el_rms = np.sqrt(np.mean(el_error * el_error))
    rot_rms = np.sqrt(np.mean(rot_error * rot_error))

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for error calculations = {elapsed}")
    start = time.time()

    # Plot it
    if makeGraph:
        fig = plt.figure(figsize = (16,8))
        plt.suptitle(f"Mount Tracking {expId}", fontsize = 18)
        plt.subplot(3,2,1)
        ax1 = az['azimuthCalculatedAngle'].plot(legend=True, color='red')
        ax1.axvline(tStart, color="red", linestyle="--")
        ax1.set_xticks([])
        ax1.set_ylabel("Degrees")
        plt.subplot(3,2,3)
        ax3 = el['elevationCalculatedAngle'].plot(legend=True, color='green')
        ax3.axvline(tStart, color="red", linestyle="--")
        ax3.set_xticks([])
        ax3.set_ylabel("Degrees")
        plt.subplot(3,2,5)
        ax5 = rot['nasmyth2CalculatedAngle'].plot(legend=True, color='blue')
        ax5.axvline(tStart, color="red", linestyle="--")
        ax5.set_ylabel("Degrees")

        plt.subplot(3,2,2)
        plt.plot(times, az_error, color='red')
        plt.title(f"Azimuth RMS error = {az_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.xticks([])
        plt.ylabel("ArcSeconds")
        plt.subplot(3,2,4)
        plt.plot(times, el_error, color='green')
        plt.title(f"Elevation RMS error = {el_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.xticks([])
        plt.ylabel("ArcSeconds")
        plt.subplot(3,2,6)
        plt.plot(times, rot_error, color='blue')
        plt.title(f"Nasmyth RMS error = {rot_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.ylabel("ArcSeconds")
        plt.savefig(f"/home/craiglagegit/DATA/mount_graphs/Mount_Errors_{expId}_20Feb21.pdf")

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for plots = {elapsed}")
    start = time.time()

    if (az_rms > fail_limit) or (el_rms > fail_limit) or (rot_rms > fail_limit):
        return False
    else:
        return True

### MAIN FUNCTION ###
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expId', help='expId: Format 2021021800736')
    args = parser.parse_args()
    expId = int(args.expId)
    result = await MountTracking(expId)
    print(result)
    return 0

asyncio.run(main())


