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
## Print Night
##-------------------------------------------------------------------------
def schedule_night(FO, local_sunset, local_dusk, title):
    twohours = tdelta(seconds=60.*60.*2.)
    descr = 'Sunset: {} | Twilight End: {}'.format(
            local_sunset.strftime('%I:%M %p'),
            local_dusk.strftime('%I:%M %p'),
            )
    line = '{}, {}, {}, {}, {}, {}\n'.format(
            title,
            (local_sunset-twohours).strftime('%m/%d/%Y'),
            (local_sunset-twohours).strftime('%I:%M %p'),
            (local_sunset-twohours).strftime('%m/%d/%Y'),
            '11:59 PM',
            descr)
    print('{}, {}, {}'.format(
          local_sunset.strftime('%Y-%m-%d %H:%M:%S'),
          local_dusk.strftime('%H:%M:%S'), title))
    FO.write(line)

def print_night(sunset, dusk, string=''):
    print('{}, {}, {}'.format(sunset_string.strftime('%Y-%m-%d %H:%M:%S'),\
                              dusk_string.strftime('%H:%M:%S'), string))


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

    pyephem_site = ephem.Observer()
    pyephem_site.lat = str(loc.latitude.to(u.degree).value)
    pyephem_site.lon = str(loc.longitude.to(u.deg).value)
    pyephem_site.elevation = loc.height.to(u.m).value
    pyephem_moon = ephem.Moon()

    oneday = TimeDelta(60.*60.*24., format='sec')
    date_iso_string = '{:4d}-01-01T00:00:00'.format(args.year)
    start_date = Time(date_iso_string, format='isot', scale='utc', location=loc)
    sunset = obs.sun_set_time(start_date, which='nearest')

    filename = 'DarkMoonCalendar_{:4d}.csv'.format(args.year)
    if os.path.exists(filename): os.remove(filename)
    with open(filename, 'w') as FO:
        hdr = 'Subject, Start date, Start time, End date, End time, Description'
        FO.write(hdr+'\n')

        while sunset < start_date + 365*oneday:
            sunset = obs.sun_set_time(sunset+oneday, which='nearest')
            local_sunset = sunset.to_datetime(localtz)

            dusk = obs.twilight_evening_astronomical(sunset, which='next')
            local_dusk = dusk.to_datetime(localtz)

            m = moon.get_moon(sunset, loc)
            illum = moon.moon_illumination(sunset, loc)

            pyephem_site.date = sunset.to_datetime().strftime('%Y/%m/%d %H:%M')
            pyephem_moon.compute(pyephem_site)

            if m.alt < 0*u.degree:
    #             est_moon_rise = obs.target_rise_time(sunset, m, which='next')
    #             m2 = moon.get_moon(est_moon_rise, loc)
    #             moon_rise = obs.target_rise_time(est_moon_rise, m2, which='nearest')
                pyephem_moon_rise = Time(pyephem_site.next_rising(ephem.Moon()).datetime())
                moon_rise = pyephem_moon_rise
                local_moon_rise = moon_rise.to_datetime(localtz)
                time_to_rise = moon_rise - dusk
                if time_to_rise.sec*u.second > args.dark_time*u.hour:
                    title = 'Dark until {} when {:.0f}% moon rises'.format(
                            local_moon_rise.strftime('%I:%M %p'), illum*100.)
                    schedule_night(FO, local_sunset, local_dusk, title)
            else:
    #             est_moon_set = obs.target_set_time(sunset, m, which='next')
    #             m2 = moon.get_moon(est_moon_set, loc)
    #             moon_set = obs.target_set_time(sunset, m2, which='nearest')
                pyephem_moon_set = Time(pyephem_site.next_setting(ephem.Moon()).datetime())
                moon_set = pyephem_moon_set
                local_moon_set = moon_set.to_datetime(localtz)
                time_to_set = moon_set - dusk
                if moon_set < dusk:
                    title = 'Dark ({:.0f}% moon)'.format(illum*100.)
                    schedule_night(FO, local_sunset, local_dusk, title)
                elif time_to_set.sec*u.second < args.wait_time*u.hour:
                    title = 'Dark after {} when {:.0f}% moon sets'.format(
                            local_moon_set.strftime('%I:%M %p'), illum*100.)
                    schedule_night(FO, local_sunset, local_dusk, title)

if __name__ == '__main__':
    main()
