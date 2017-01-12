#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse

from datetime import datetime as dt
from datetime import timedelta as tdelta
import pytz

import numpy as np
from astropy import units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, EarthLocation, AltAz

from astroplan import FixedTarget, Observer, moon

import ephem

##-------------------------------------------------------------------------
## Generate ICS Entry
##-------------------------------------------------------------------------
def ics_entry(FO, title, starttime, endtime, description, verbose=False):
    assert type(title) is str
    assert type(starttime) in [dt, str]
    assert type(endtime) in [dt, str]
    assert type(description) in [list, str]
    now = dt.utcnow()
    try:
        starttime = starttime.strftime('%Y%m%dT%H%M%S')
    except:
        pass
    try:
        endtime = endtime.strftime('%Y%m%dT%H%M%S')
    except:
        pass
    if verbose:
        print('{} {}'.format(starttime[0:8], title))
    if type(description) is list:
        description = '\\n'.join(description)
    FO.write('BEGIN:VEVENT\n')
    FO.write('UID:{}@mycalendar.com\n'.format(now.strftime('%Y%m%dT%H%M%S.%fZ')))
    FO.write('DTSTAMP:{}\n'.format(now.strftime('%Y%m%dT%H%M%SZ')))
    FO.write('DTSTART;TZID=Pacific/Honolulu:{}\n'.format(starttime))
    FO.write('DTEND;TZID=Pacific/Honolulu:{}\n'.format(endtime))
    FO.write('SUMMARY:{}\n'.format(title))
    FO.write('DESCRIPTION: {}\n'.format(description))
    FO.write('END:VEVENT\n')
    FO.write('\n')


##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():

    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    ## add arguments
    parser.add_argument("-y", "--year",
        type=int, dest="year",
        default=-1,
        help="The calendar year to analyze")
    parser.add_argument("-s", "--site",
        type=str, dest="site",
        default='Keck Observatory',
        help="Site name to use")
    parser.add_argument("-z", "--timezone",
        type=str, dest="timezone",
        default='US/Hawaii',
        help='pytz timezone name')
    parser.add_argument("-d", "--dark_time",
        type=float, dest="dark_time",
        default=2,
        help='Minimum dark time required (hours)')
    parser.add_argument("-w", "--wait_time",
        type=float, dest="wait_time",
        default=2,
        help='Maximum time after dusk to wait for moon set (hours)')

    args = parser.parse_args()

    if args.year == -1:
        args.year = dt.now().year

    ##-------------------------------------------------------------------------
    ## 
    ##-------------------------------------------------------------------------
    loc = EarthLocation.of_site(args.site)
    obs = Observer.at_site(args.site)
    utc = pytz.timezone('UTC')
    localtz = pytz.timezone(args.timezone)
    hour = tdelta(seconds=60.*60.*1.)

    pyephem_site = ephem.Observer()
    pyephem_site.lat = str(loc.latitude.to(u.degree).value)
    pyephem_site.lon = str(loc.longitude.to(u.deg).value)
    pyephem_site.elevation = loc.height.to(u.m).value
    pyephem_moon = ephem.Moon()

    oneday = TimeDelta(60.*60.*24., format='sec')
    date_iso_string = '{:4d}-01-01T00:00:00'.format(args.year)
    start_date = Time(date_iso_string, format='isot', scale='utc', location=loc)
    sunset = obs.sun_set_time(start_date, which='nearest')

    ical_file = 'DarkMoonCalendar_{:4d}.ics'.format(args.year)
    if os.path.exists(ical_file): os.remove(ical_file)
    with open(ical_file, 'w') as FO:
        FO.write('BEGIN:VCALENDAR\n'.format())
        FO.write('PRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'.format())

        while sunset < start_date + 365*oneday:
            sunset = obs.sun_set_time(sunset+oneday, which='nearest')
            local_sunset = sunset.to_datetime(localtz)
            dusk = obs.twilight_evening_astronomical(sunset, which='next')
            local_dusk = dusk.to_datetime(localtz)
            description = ['Sunset @ {}'.format(local_sunset.strftime('%I:%M %p') ),
                           '12 deg Twilight @ {}'.format(local_dusk.strftime('%I:%M %p') )]

            # Using astroplan
#             m = moon.get_moon(sunset, loc)
#             illum = moon.moon_illumination(sunset, loc)
#             moon_down = m.alt < 0*u.degree
#             if moon_down:
#                 est_moon_rise = obs.target_rise_time(sunset, m, which='next')
#                 m2 = moon.get_moon(est_moon_rise, loc)
#                 moon_rise = obs.target_rise_time(est_moon_rise, m2, which='nearest')
#             else:
#                 est_moon_set = obs.target_set_time(sunset, m, which='next')
#                 m2 = moon.get_moon(est_moon_set, loc)
#                 moon_set = obs.target_set_time(sunset, m2, which='nearest')

            # Using pyephem
            pyephem_site.date = sunset.to_datetime().strftime('%Y/%m/%d %H:%M')
            pyephem_moon.compute(pyephem_site)
            illum = pyephem_moon.moon_phase
            moon_down = pyephem_moon.alt < 0.
            if moon_down:
                moon_rise = Time(pyephem_site.next_rising(ephem.Moon()).datetime())
            else:
                moon_set = Time(pyephem_site.next_setting(ephem.Moon()).datetime())


            if moon_down:
                local_moon_rise = moon_rise.to_datetime(localtz)
                time_to_rise = moon_rise - dusk
                if time_to_rise.sec*u.second > args.dark_time*u.hour:
                    title = 'Dark until {}'.format(
                            local_moon_rise.strftime('%I:%M %p'))
                    description.append('{:.0f}% Moon Rises @ {}'.format(
                            illum*100., local_moon_rise.strftime('%I:%M %p')))
                    ics_entry(FO, title, local_sunset-2*hour, local_dusk+4*hour,
                              description, verbose=True)
            else:
                local_moon_set = moon_set.to_datetime(localtz)
                time_to_set = moon_set - dusk
                if moon_set < dusk:
                    title = 'Dark ({:.0f}% moon)'.format(illum*100.)
                    ics_entry(FO, title, local_sunset-2*hour, local_dusk+4*hour,
                              description, verbose=True)
                elif time_to_set.sec*u.second < args.wait_time*u.hour:
                    title = 'Dark after {}'.format(
                            local_moon_set.strftime('%I:%M %p'))
                    description.append('{:.0f}% Moon Sets @ {}'.format(
                            illum*100., local_moon_set.strftime('%I:%M %p')))
                    ics_entry(FO, title, local_sunset-2*hour, local_dusk+4*hour,
                              description, verbose=True)

        FO.write('END:VCALENDAR\n')


if __name__ == '__main__':
    from astroplan import download_IERS_A
    download_IERS_A()
    main()
