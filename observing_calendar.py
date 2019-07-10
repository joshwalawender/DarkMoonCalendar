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
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, FK5

from astroplan import FixedTarget, Observer, moon, moon_illumination

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
        print(f'  --> Observable: {title}')
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
## Analyze Day
##-------------------------------------------------------------------------
def analyze_day(search_around, obs, FO, localtz, args, verbose=True):
    sunset = obs.sun_set_time(search_around, which='nearest')
    delta = (search_around.to_datetime() - sunset.to_datetime()).total_seconds()
    if abs(delta) > 12*60*60:
        sunset = obs.sun_set_time(search_around+TimeDelta(1800, format='sec'), which='nearest')
        delta = (search_around.to_datetime() - sunset.to_datetime()).total_seconds()
    if abs(delta) > 12*60*60:
        print(f'WARNING Delta = {delta:.0f} seconds')
        sys.exit(0)
    local_sunset = sunset.to_datetime(localtz)
    dusk = obs.twilight_evening_astronomical(sunset, which='next')
    local_dusk = dusk.to_datetime(localtz)
    description = [f"Sunset @ {local_sunset.strftime('%I:%M %p')}",
                   f"18 deg Twilight @ {local_dusk.strftime('%I:%M %p')}"]

    # Moon from astroplan
    illum = moon_illumination(sunset)
    mooncoord = moon.get_moon(sunset).transform_to(FK5())
    mooncoord.location = obs.location
    moonalt = mooncoord.transform_to(AltAz()).alt
    moon_down = moonalt.value < 0.
    ttup = local_sunset.timetuple()
    endtime = dt(ttup.tm_year, ttup.tm_mon, ttup.tm_mday, 23, 59, 00, 0, localtz)

    preamble = f"Sunset at {local_sunset.strftime('%Y/%m/%d %H:%M')}"

    if illum > 0.7:
        title = f"Moon is bright ({illum*100:.0f}%)."
        print(f"{preamble}: {title}")
    elif illum < 0.1:
        title = f"Moon is dark ({illum*100:.0f}%)."
        print(f"{preamble}: {title}")
        description.append(f"Moon is dark ({illum*100:.0f}%)")
        ics_entry(FO, title, local_sunset-2*tdelta(seconds=60.*60.*1.), endtime,
                  description, verbose=verbose)
    elif moon_down is True:
        title = f"Moon is gray ({illum*100:.0f}%)."
        moon_rise = obs.moon_rise_time(sunset)
        local_moon_rise = moon_rise.to_datetime(localtz)
        time_to_rise = moon_rise - dusk
        if time_to_rise.sec < 0:
            title += ' Moon rises during twilight'
        if time_to_rise.sec*u.second > args.dark_time*u.hour:
            title += f" Dark until {local_moon_rise.strftime('%I:%M %p')} ({time_to_rise.sec/3600:.1f} hr)"
            description.append(f"{illum*100:.0f}% Moon Rises @ {local_moon_rise.strftime('%I:%M %p')}")
            ics_entry(FO, title, local_sunset-2*tdelta(seconds=60.*60.*1.), endtime,
                      description, verbose=verbose)
        elif time_to_rise.sec > 0:
            title += f" Moon rises at {local_moon_rise.strftime('%Y/%m/%d %H:%M')},"\
                     f" only {time_to_rise.sec/3600:.1f} hours after dusk."
        print(f"{preamble}: {title}")
    elif moon_down is False:
        title = f"Moon is gray ({illum*100:.0f}%)."
        if illum < 0.3:
            moon_set = obs.moon_set_time(sunset)
            local_moon_set = moon_set.to_datetime(localtz)
            title += f" Dark after {local_moon_set.strftime('%I:%M %p')}"
            print(f"{preamble}: {title}")
            description.append(f"{illum*100:.0f}% Moon Sets @ {local_moon_set.strftime('%I:%M %p')}")
            ics_entry(FO, title, local_sunset-2*tdelta(seconds=60.*60.*1.), endtime,
                      description, verbose=verbose)
    else:
        print('Weird!')
        sys.exit(1)

    return sunset


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
    parser.add_argument("-v", "--verbose", dest="verbose",
        default=False, action="store_true",
        help="Be verbose! (default = False)")
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
        default=2.5,
        help='Maximum time after dusk to wait for moon set (hours)')

    args = parser.parse_args()

    if args.year == -1:
        args.year = dt.now().year

    ##-------------------------------------------------------------------------
    ## 
    ##-------------------------------------------------------------------------
    obs = Observer.at_site(args.site)
    utc = pytz.timezone('UTC')
    localtz = pytz.timezone(args.timezone)

    oneday = TimeDelta(60.*60.*24., format='sec')
    date_iso_string = f'{args.year:4d}-01-01T00:00:00'
    start_date = Time(date_iso_string, format='isot', scale='utc', location=obs.location)
    sunset = obs.sun_set_time(start_date, which='next')

    ical_file = 'DarkMoonCalendar_{:4d}.ics'.format(args.year)
    if os.path.exists(ical_file): os.remove(ical_file)
    with open(ical_file, 'w') as FO:
        FO.write('BEGIN:VCALENDAR\n'.format())
        FO.write('PRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'.format())

        while sunset < start_date + 365*oneday:
            search_around = sunset + oneday
            sunset = analyze_day(search_around, obs, FO, localtz, args,
                                 verbose=args.verbose)
        FO.write('END:VCALENDAR\n')


if __name__ == '__main__':
#     from astroplan import download_IERS_A
#     download_IERS_A()
    main()
