import sys, time, os, asyncio, argparse
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from astropy.time import Time, TimeDelta
from lsst_efd_client import EfdClient
from lsst.daf.butler import Butler

# This routine does the tracking and creates the graph
async def MountTracking(expId, pdf, butler, client, fail_limit=0.5, makeGraph=True):
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
    mData = butler.get('raw.metadata', detector=0, exposure=expId)
    imgType = mData['IMGTYPE']
    tStart = mData['DATE-BEG']
    tEnd = mData['DATE-END']
    elevation = mData['ELSTART']
    azimuth = mData['AZSTART']
    print(f"expId = {expId}, imgType = {imgType}, Times = {tStart}, {tEnd}")
    if (imgType not in ['OBJECT', 'SKYEXP', 'ENGTEST', 'DARK']):
        return True
    end = time.time()
    elapsed = end-start
    print(f"Elapsed time for butler query = {elapsed}")
    start = time.time()

    # Get the data
    t_start = Time(tStart, scale='tai').utc
    t_end = Time(tEnd, scale='tai').utc

    #time.sleep(5.0)
    az = await client.select_packed_time_series("lsst.sal.ATMCS.mount_AzEl_Encoders", 'azimuthCalculatedAngle', t_start, t_end)
    el = await client.select_packed_time_series("lsst.sal.ATMCS.mount_AzEl_Encoders", 'elevationCalculatedAngle', t_start, t_end)
    rot = await client.select_packed_time_series("lsst.sal.ATMCS.mount_Nasmyth_Encoders", 'nasmyth2CalculatedAngle', t_start, t_end)  
    az_torque_1 =  await client.select_packed_time_series("lsst.sal.ATMCS.measuredTorque", 'azimuthMotor1Torque', t_start, t_end)
    az_torque_2 =  await client.select_packed_time_series("lsst.sal.ATMCS.measuredTorque", 'azimuthMotor2Torque', t_start, t_end)
    el_torque =  await client.select_packed_time_series("lsst.sal.ATMCS.measuredTorque", 'elevationMotorTorque', t_start, t_end)
    rot_torque =  await client.select_packed_time_series("lsst.sal.ATMCS.measuredTorque", 'nasmyth2MotorTorque', t_start, t_end)

    end = time.time()
    elapsed = end-start
    print(f"Elapsed time to get the data = {elapsed}")
    start = time.time()

    # Calculate the tracking errors
    az_vals = np.array(az.values.tolist())[:,0]
    el_vals = np.array(el.values.tolist())[:,0]
    rot_vals = np.array(rot.values.tolist())[:,0]
    times = np.array(az.values.tolist())[:,1]
    times = times - times[0]
    print("LengthAz", len(az_vals))
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

        tStart = t_start.to_datetime()
        fig = plt.figure(figsize = (16,16))
        plt.suptitle(f"Mount Tracking {expId}, Azimuth = {azimuth:.1f}, Elevation = {elevation:.1f}", fontsize = 18)
        # Azimuth axis
        plt.subplot(3,3,1)
        ax1 = az['azimuthCalculatedAngle'].plot(legend=True, color='red')
        ax1.set_title("Azimuth axis", fontsize=16)
        ax1.axvline(tStart, color="red", linestyle="--")
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
        ax7.axvline(tStart, color="red", linestyle="--")

        # Elevation axis
        plt.subplot(3,3,2)
        ax2 = el['elevationCalculatedAngle'].plot(legend=True, color='green')
        ax2.set_title("Elevation axis", fontsize=16)
        ax2.axvline(tStart, color="red", linestyle="--")
        ax2.set_xticks([])
        plt.subplot(3,3,5)
        plt.plot(times, el_error, color='green')
        plt.title(f"Elevation RMS error = {el_rms:.2f} arcseconds")
        plt.ylim(-10.0,10.0)
        plt.xticks([])
        plt.subplot(3,3,8)
        ax8 = el_torque['elevationMotorTorque'].plot(legend=True, color='blue')
        ax8.axvline(tStart, color="red", linestyle="--")

        # Nasmyth2 rotator axis
        plt.subplot(3,3,3)
        ax3 = rot['nasmyth2CalculatedAngle'].plot(legend=True, color='blue')
        ax3.set_title("Nasmyth2 axis", fontsize=16)
        ax3.axvline(tStart, color="red", linestyle="--")
        ax3.set_xticks([])
        plt.subplot(3,3,6)
        plt.plot(times, rot_error, color='blue')
        plt.title(f"Nasmyth RMS error = {rot_rms:.2f} arcseconds")
        plt.ylim(-10000.0,10000.0)
        plt.subplot(3,3,9)
        ax9 = rot_torque['nasmyth2MotorTorque'].plot(legend=True, color='blue')
        ax9.axvline(tStart, color="red", linestyle="--")
        pdf.savefig(fig)
        plt.close()
        #plt.savefig(f"/home/craiglagegit/DATA/mount_graphs/Mount_Errors_{expId}_03Mar21.pdf")

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
    parser.add_argument('--expId', help='firstExpId: Format 2021021800736')
    args = parser.parse_args()
    expId = int(args.expId)

    client = EfdClient('summit_efd')
    butler = Butler('/repo/LATISS', collections="LATISS/raw/all")
    pdf = PdfPages('/home/craiglagegit/DATA/mount_graphs/Tracking_%d.pdf'%expId)
    result = await MountTracking(expId, pdf, butler, client)
    pdf.close()
    return 0

asyncio.run(main())


