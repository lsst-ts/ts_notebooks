"""A quick script to demonstrate the issue of acknowledgement queueing,
DM-19581.

To run, one need to have ATPtg and ATMCS simulator running.
"""

import sys
import time
import asyncio
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import AltAz, ICRS, EarthLocation

from lsst.ts.salobj import Remote, State

import SALPY_ATMCS
import SALPY_ATPtg


async def main():
    atmcs = Remote(SALPY_ATMCS)
    atptg = Remote(SALPY_ATPtg)

    start = time.time()
    print(await atmcs.cmd_start.start())
    end = time.time()
    print(f'start atmcs took: {end-start:.2f}s')

    start = time.time()
    await atptg.cmd_start.start()
    end = time.time()
    print(f'start atptg took: {end-start:.2f}s')

    start = time.time()
    await atmcs.cmd_enable.start()
    end = time.time()
    print(f'enable atmcs took: {end-start:.2f}s')

    start = time.time()
    await atptg.cmd_enable.start()
    end = time.time()
    print(f'enable atptg took: {end-start:.2f}s')

    location = EarthLocation.from_geodetic(lon=-70.747698 * u.deg,
                                           lat=-30.244728 * u.deg,
                                           height=2663.0 * u.m)

    time_data = await atptg.tel_timeAndDate.next(flush=False, timeout=2)
    curr_time_atptg = Time(time_data.tai, format="mjd", scale="tai")

    el = 45. * u.deg
    az = 45. * u.deg

    cmd_elaz = AltAz(alt=el, az=az, obstime=curr_time_atptg.tai, location=location)
    cmd_radec = cmd_elaz.transform_to(ICRS)

    atptg.cmd_raDecTarget.set(
        targetName="atptg_atmcs_integration",
        targetInstance=SALPY_ATPtg.ATPtg_shared_TargetInstances_current,
        frame=SALPY_ATPtg.ATPtg_shared_CoordFrame_icrs,
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
        rotPA=0,
        rotFrame=SALPY_ATPtg.ATPtg_shared_RotFrame_target,
        rotMode=SALPY_ATPtg.ATPtg_shared_RotMode_field)

    start = time.time()
    await atptg.cmd_raDecTarget.start()
    end = time.time()
    print(f'raDecTarget atptg took: {end-start:.2f}s')

    waittime = 20.
    print(f"Waiting {waittime}s...")
    sleep_time = waittime / 10.
    for i in range(10):
        print(".", end=" ")
        sys.stdout.flush()
        await asyncio.sleep(sleep_time)
    print("")
    print(f"stop tracking...")

    start = time.time()
    await atptg.cmd_stopTracking.start()
    end = time.time()
    print(f'stop tracking atptg took: {end-start:.2f}s')

    print(f"Waiting {waittime}s again...")
    for i in range(10):
        print(".", end=" ")
        sys.stdout.flush()
        await asyncio.sleep(sleep_time)
    print("")
    print(f"disabling atmcs...")

    start = time.time()
    coro = atmcs.evt_summaryState.next(flush=True)
    await atmcs.cmd_disable.start()
    end = time.time()
    print(f'disable atmcs took: {end-start:.2f}s')
    ss = await coro
    print(State(ss.summaryState))

    start = time.time()
    coro = atmcs.evt_summaryState.next(flush=True)
    await atmcs.cmd_enable.start()
    end = time.time()
    print(f'enable atmcs took: {end-start:.2f}s')
    ss = await coro
    print(State(ss.summaryState))

    start = time.time()
    print(await atmcs.cmd_disable.start())
    end = time.time()
    print(f'disable atmcs took: {end-start:.2f}s')

    start = time.time()
    await atptg.cmd_disable.start()
    end = time.time()
    print(f'disable atptg took: {end-start:.2f}s')

    start = time.time()
    await atmcs.cmd_standby.start()
    end = time.time()
    print(f'standby atmcs took: {end-start:.2f}s')

    start = time.time()
    await atptg.cmd_standby.start()
    end = time.time()
    print(f'standby atptg took: {end-start:.2f}s')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
