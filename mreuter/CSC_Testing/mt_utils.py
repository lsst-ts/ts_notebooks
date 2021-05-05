from astropy.coordinates import AltAz, ICRS, EarthLocation, Angle
from astropy.time import Time
import astropy.units as u

from lsst.ts import salobj

def altaz_to_radec(alt, az):
    location = EarthLocation.from_geodetic(
        lon=-70.747698 * u.deg, lat=-30.244728 * u.deg, height=2663.0 * u.m
    )

    current_time = salobj.astropy_time_from_tai_unix(salobj.current_tai())
    current_time.location = location

    coord_frame_radec = ICRS()

    alt_az = AltAz(
        az=Angle(az, unit=u.deg),
        alt=Angle(alt, unit=u.deg),
        location=location,
        obstime=current_time
    )

    return alt_az.transform_to(coord_frame_radec)

async def slew_to_park(mtcs, rotpa=0.0):
    ra_dec = altaz_to_radec(80.0, 0.0)

    mtcs.rem.mtptg.cmd_raDecTarget.set(
        ra=ra_dec.ra.hour,
        declination=ra_dec.dec.deg,
        rotPA=Angle(rotpa, unit=u.deg).deg,
        targetName="Park position",
        frame=2,
        epoch=2000,
        equinox=2000,
        parallax=0,
        pmRA=0,
        pmDec=0,
        rv=0,
        dRA=0,
        dDec=0,
        rotFrame=1,
        rotMode=1,
    )

    await slew(mtcs, True)

async def slew_to_flatfield(mtcs, rotpa=-180.0):
    ra_dec = altaz_to_radec(39.0, 205.7)

    mtcs.rem.mtptg.cmd_raDecTarget.set(
        ra=ra_dec.ra.hour,
        declination=ra_dec.dec.deg,
        rotPA=Angle(rotpa, unit=u.deg).deg,
        targetName="Flatfield position",
        frame=2,
        epoch=2000,
        equinox=2000,
        parallax=0,
        pmRA=0,
        pmDec=0,
        rv=0,
        dRA=0,
        dDec=0,
        rotFrame=1,
        rotMode=1,
    )

    await slew(mtcs, True)

async def slew_to_target(mtcs, target_name, ra, dec, rotpa):
    radec_icrs = ICRS(Angle(ra, unit=u.hourangle), Angle(dec, unit=u.deg))

    mtcs.rem.mtptg.cmd_raDecTarget.set(
        ra=radec_icrs.ra.hour,
        declination=radec_icrs.dec.deg,
        rotPA=Angle(rotpa, unit=u.deg).deg,
        targetName=target_name,
        frame=2,
        epoch=2000,
        equinox=2000,
        parallax=0,
        pmRA=0,
        pmDec=0,
        rv=0,
        dRA=0,
        dDec=0,
        rotFrame=1,
        rotMode=1,
    )

    await slew2(mtcs)

async def stop_mt_tracking(mtcs):
    ack = await mtcs.rem.mtptg.cmd_stopTracking.start(timeout=30.)
    print("Stop Tracking")
    print(f"ack={ack.ack} ack.error={ack.error}, ackcmd.result={ack.result}")

async def slew2(mtcs, stop_tracking=False):
    print("Slewing Telescope")
    ack = await mtcs.rem.mtptg.cmd_raDecTarget.start(timeout=30.)
    print(f"ack={ack.ack} ack.error={ack.error}, ackcmd.result={ack.result}")
    result = await mtcs.wait_in_position(30.)
    print(result)

    if stop_tracking:
        await stop_mt_tracking(mtcs)

async def slew(mtcs, stop_tracking=False):
    print("Slewing Telescope")
    ack = await mtcs.rem.mtptg.cmd_raDecTarget.start(timeout=30.)
    print(f"ack={ack.ack} ack.error={ack.error}, ackcmd.result={ack.result}")
    while True:
        in_position = await mtcs.rem.newmtmount.evt_axesInPosition.next(flush=False, timeout=60.)
        print(f"State: {in_position.elevation}, {in_position.azimuth}")
        if in_position.elevation and in_position.azimuth:
            print("Telescope in position.")
            break

    if stop_tracking:
        await stop_mt_tracking(mtcs)
