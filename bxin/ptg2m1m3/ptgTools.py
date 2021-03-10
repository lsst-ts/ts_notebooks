import asyncio
from astropy.coordinates import AltAz, ICRS, EarthLocation, Angle, FK5
from lsst.ts.idl.enums import ATPtg
import astropy.units as u

from datetime import datetime, timedelta
from astropy.time import Time

async def ptgSlew(ptg, alt, az, rot):
    location = EarthLocation.from_geodetic(lon=-70.747698*u.deg,
                                       lat=-30.244728*u.deg,
                                       height=2663.0*u.m)
    now = datetime.now()
    print("Start to point the telescope", now)

    alt = alt * u.deg
    az = az * u.deg
    rot_tel = Angle(rot, unit= u.deg) 

    target_name="TMA motion test"
    time_data = await ptg.tel_timeAndDate.next(flush=True, timeout=2)
    curr_time_ptg = Time(time_data.mjd, format="mjd", scale="tai")
    time_err = curr_time_ptg - Time.now()
    print(f"Time error={time_err.sec:0.2f} sec")

    print(curr_time_ptg.tai.value)

    cmd_elaz = AltAz(alt=alt, az=az, 
                    obstime=curr_time_ptg.tai, 
                    location=location)
    cmd_radec = cmd_elaz.transform_to(ICRS)
    # Calculating the other parameters     
    rot_pa = rot_tel

    #The pointing component is commanding the mount directly
    await ptg.cmd_raDecTarget.set_start(
        targetName=target_name,
        frame=ATPtg.CoordFrame.ICRS,
        epoch=2000,  # should be ignored: no parallax or proper motion
        equinox=2000,  # should be ignored for ICRS
        ra=cmd_radec.ra.hour,
        declination=cmd_radec.dec.deg,
        parallax=0,
        pmRA=0,
        pmDec=0,
        rv=0,
        dRA=0,
        dDec=0,
        rotPA=rot_pa.deg-180,
        rotFrame=ATPtg.RotFrame.FIXED,
        rotMode=ATPtg.RotMode.FIELD,
        timeout=10
    )

    print("Waiting 30s")
    await asyncio.sleep(30.)
    print("System Ready")

