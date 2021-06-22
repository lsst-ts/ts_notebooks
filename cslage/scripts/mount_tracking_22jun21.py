import sys, time, os, asyncio, argparse
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient, merge_packed_time_series
from lsst.daf.butler import Butler

# This routine does the tracking and creates the graph
async def MountTracking(expId, pdf, butler, client):
    start = time.time()
    """Queries the EFD for a given exposure and checks if there were tracking errors
            Parameters
            ----------
            expId : `int`
                The expId of the exposure being tested

        Returns
            -------
            result : None
            """

    # Find the time of exposure
    mData = butler.get('raw.metadata', detector=0, exposure=expId)
    imgType = mData['IMGTYPE']
    tStart = mData['DATE-BEG']
    tEnd = mData['DATE-END']
    elevation = mData['ELSTART']
    azimuth = mData['AZSTART']
    exptime = mData['EXPTIME']
    print(f"expId = {expId}, imgType = {imgType}, Times = {tStart}, {tEnd}")
    if (imgType not in ['OBJECT', 'SKYEXP', 'ENGTEST', 'DARK']) or (exptime < 1.99):
        return 
    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for butler query = {elapsed}")
    start = time.time()

    # Get the data
    # Time base in the EFD is still a big mess.  Although these times are in UTC,
    # it is necessary to tell the code they are in TAI.  Then it is necessary to
    # tell the merge_packed_time_series to use UTC.  After doing all of this, there is
    # still a 2 second offset, which is discussed in JIRA ticket DM-29243, but not understood.

    t_start = Time(tStart, scale='tai')
    t_end = Time(tEnd, scale='tai')
    print(f"Tstart = {t_start.isot}, Tend = {t_end.isot}")
    mount_position = await client.select_time_series("lsst.sal.ATMCS.mount_AzEl_Encoders", ['*'],
                                              t_start, t_end)
    nasmyth_position = await client.select_time_series("lsst.sal.ATMCS.mount_Nasmyth_Encoders", ['*'],
                                              t_start, t_end)
    torques = await client.select_time_series("lsst.sal.ATMCS.measuredTorque", ['*'],
                                          t_start, t_end)
    print("Length of time series", len(mount_position))

    az = merge_packed_time_series(mount_position, 'azimuthCalculatedAngle', stride=1, internal_time_scale="utc")
    el = merge_packed_time_series(mount_position, 'elevationCalculatedAngle', stride=1, internal_time_scale="utc")
    rot = merge_packed_time_series(nasmyth_position, 'nasmyth2CalculatedAngle', stride=1, internal_time_scale="utc")  
    az_torque_1 =  merge_packed_time_series(torques, 'azimuthMotor1Torque', stride=1, internal_time_scale="utc")
    az_torque_2 =  merge_packed_time_series(torques, 'azimuthMotor2Torque', stride=1, internal_time_scale="utc")
    el_torque =  merge_packed_time_series(torques, 'elevationMotorTorque', stride=1, internal_time_scale="utc")
    rot_torque =  merge_packed_time_series(torques, 'nasmyth2MotorTorque', stride=1, internal_time_scale="utc")

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time to get the data = {elapsed}")
    start = time.time()

    # Calculate the tracking errors
    az_vals = np.array(az.values.tolist())[:,0]
    el_vals = np.array(el.values.tolist())[:,0]
    rot_vals = np.array(rot.values.tolist())[:,0]
    times = np.array(az.values.tolist())[:,1]
    print("Length of packed time series", len(az_vals))
    """
    # Fit with a quadratic
    # Quadratic fit is often poorly conditioned, so we'll stick with a linear fit.
    az_fit = np.polyfit(times, az_vals, 2)
    el_fit = np.polyfit(times, el_vals, 2)
    rot_fit = np.polyfit(times, rot_vals, 2)
    az_model = az_fit[0] * times * times + az_fit[1] * times + az_fit[2]
    el_model = el_fit[0] * times * times + el_fit[1] * times + el_fit[2]
    rot_model = rot_fit[0] * times * times + rot_fit[1] * times + rot_fit[2]
    """

    # Fit with a linear
    az_fit = np.polyfit(times, az_vals, 1)
    el_fit = np.polyfit(times, el_vals, 1)
    rot_fit = np.polyfit(times, rot_vals, 1)
    az_model = az_fit[0] * times + az_fit[1]
    el_model = el_fit[0] * times + el_fit[1]
    rot_model = rot_fit[0] * times + rot_fit[1]

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

        fig = plt.figure(figsize = (16,16))
        plt.suptitle(f"Mount Tracking {expId}, Azimuth = {azimuth:.1f}, Elevation = {elevation:.1f}", fontsize = 18)
        # Azimuth axis
        plt.subplot(3,3,1)
        ax1 = az['azimuthCalculatedAngle'].plot(legend=True, color='red')
        ax1.set_title("Azimuth axis", fontsize=16)
        ax1.axvline(az.index[0], color="red", linestyle="--")
        ax1.set_xticks([])
        ax1.set_ylabel("Degrees")
        plt.subplot(3,3,4)
        plt.plot(times, az_error, color='red')
        plt.title(f"Azimuth RMS error = {az_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.xticks([])
        plt.ylabel("ArcSeconds")
        plt.subplot(3,3,7)
        ax7 = az_torque_1['azimuthMotor1Torque'].plot(legend=True, color='blue')
        ax7 = az_torque_2['azimuthMotor2Torque'].plot(legend=True, color='green')
        ax7.axvline(az.index[0], color="red", linestyle="--")
        ax7.set_ylabel("Torque(amps)")

        # Elevation axis
        plt.subplot(3,3,2)
        ax2 = el['elevationCalculatedAngle'].plot(legend=True, color='green')
        ax2.set_title("Elevation axis", fontsize=16)
        ax2.axvline(az.index[0], color="red", linestyle="--")
        ax2.set_xticks([])
        plt.subplot(3,3,5)
        plt.plot(times, el_error, color='green')
        plt.title(f"Elevation RMS error = {el_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.xticks([])
        plt.subplot(3,3,8)
        ax8 = el_torque['elevationMotorTorque'].plot(legend=True, color='blue')
        ax8.axvline(az.index[0], color="red", linestyle="--")
        ax8.set_ylabel("Torque(amps)")

        # Nasmyth2 rotator axis
        plt.subplot(3,3,3)
        ax3 = rot['nasmyth2CalculatedAngle'].plot(legend=True, color='blue')
        ax3.set_title("Nasmyth2 axis", fontsize=16)
        ax3.axvline(az.index[0], color="red", linestyle="--")
        ax3.set_xticks([])
        plt.subplot(3,3,6)
        plt.plot(times, rot_error, color='blue')
        plt.title(f"Nasmyth RMS error = {rot_rms:.2f} arcseconds")
        plt.ylim(-10000.0,10000.0)
        plt.subplot(3,3,9)
        ax9 = rot_torque['nasmyth2MotorTorque'].plot(legend=True, color='blue')
        ax9.axvline(az.index[0], color="red", linestyle="--")
        ax9.set_ylabel("Torque(amps)")
        pdf.savefig(fig)
        plt.close()

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for plots = {elapsed}")
    start = time.time()
    return

### MAIN FUNCTION ###
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expId', help='firstExpId: Format 2021021800736')
    args = parser.parse_args()
    expId = int(args.expId)
    #client = EfdClient('summit_efd')
    client = EfdClient('ldf_stable_efd')
    butler = Butler('/repo/main', collections="LATISS/raw/all")
    pdf = PdfPages('/project/cslage/AuxTel/scripts/mount_graphs/Tracking_%d.pdf'%expId)
    await MountTracking(expId, pdf, butler, client)
    pdf.close()
    return 0

asyncio.run(main())


