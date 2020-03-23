#!/usr/bin/env python
# coding: utf-8

""" This script is a cutout of a notebook to drive a quick test of the main
telescope pointing component, rotator and mount controller. It was developed
as part of the Camera Cable Wrap + Rotator integration test.
"""

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation, Angle
import asyncio
from lsst.ts import salobj
# Using enums from ATPtg because MTPtg is not defined yet.
from lsst.ts.idl.enums import ATPtg

from astropy.utils import iers
iers.conf.auto_download = False


async def amain():

    d = salobj.Domain()

    mtptg = salobj.Remote(d, "MTPtg")

    await mtptg.start_task

    await salobj.set_summary_state(mtptg, salobj.State.ENABLED)

    # This should probably eventually come from the pointing component.
    location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                           lat=-30.244728*u.deg,
                                           height=2663.0*u.m)

    n_values = 10

    # Here is a small trick to get the ra before transit.
    # Get `timeAndDate` from the pointing component, then
    # use `RA = lst - delta`.

    await asyncio.sleep(5.)

    for i in range(n_values):
        print(f"Run {i+1} of {n_values}")
        time_data = await mtptg.tel_timeAndDate.next(flush=True, timeout=5.)
        
        lst = Angle(time_data.lst, unit=u.hourangle)
        delta = Angle(7, unit=u.arcmin)
        ra = lst - delta
        print("=======================")
        print(f"LST: {lst}")
        print(f"delta: {delta}")
        print(f"RA: {ra}")
        
        dec = location.lat - Angle(6., unit=u.deg)
        print(f"Dec: {dec}")

        target_name="Rotator test"
        radec = ICRS(ra, dec)

        curr_time_mtptg = Time(time_data.tai, format="mjd", scale="tai")
        coord_frame_altaz = AltAz(location=location, obstime=curr_time_mtptg)
        alt_az = radec.transform_to(coord_frame_altaz)

        print(180.-alt_az.alt.deg)
        print("=======================")
    
        ack = await mtptg.cmd_raDecTarget.set_start(
            targetName=target_name,
            targetInstance=ATPtg.TargetInstances.CURRENT,
            frame=ATPtg.CoordFrame.ICRS,
            epoch=2000,  # should be ignored: no parallax or proper motion
            equinox=2000,  # should be ignored for ICRS
            ra=radec.ra.hour,
            declination=radec.dec.deg,
            parallax=0,
            pmRA=0,
            pmDec=0,
            rv=0,
            dRA=0,
            dDec=0,
            rotPA=180.,
            rotFrame=ATPtg.RotFrame.TARGET,
            rotMode=ATPtg.RotMode.FIELD,
            timeout=10
        )
        print(ack)
        await asyncio.sleep(35.)

    await mtptg.cmd_stopTracking.start(timeout=30)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(amain())
