#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import pytz
import numpy as np
from astropy import units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, EarthLocation, AltAz

from astroplan import FixedTarget, Observer, moon

##-------------------------------------------------------------------------
## Schedule Night
##-------------------------------------------------------------------------
def schedule_night(sunset, dusk, string=''):
#     print('{} {} {}'.format(sunset.iso, dusk.iso.split()[1], string))
    print('{} {} {}'.format(sunset.iso, dusk.iso, string))


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
        default=2016,
        help="The calendar year to analyze")
    parser.add_argument("-s", "--site",
        type=str, dest="site",
        default='Keck Observatory',
        help="Site name to use")
    parser.add_argument("-i", "--illumination_threshold",
        type=float, dest="illumination_threshold",
        default=0.05,
        help='Maximum moon illumination to be "dark"')
    parser.add_argument("-d", "--dark_time",
        type=float, dest="dark_time",
        default=2,
        help='Minimum dark time required (hours)')
    parser.add_argument("-w", "--wait_time",
        type=float, dest="wait_time",
        default=2,
        help='Maximum time after dusk to wait for moon set (hours)')

    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## 
    ##-------------------------------------------------------------------------
    loc = EarthLocation.of_site(args.site)
    obs = Observer.at_site(args.site)
    obs.timezone = pytz.timezone('US/Hawaii')
    
    oneday = TimeDelta(60.*60.*24., format='sec')
    date_iso_string = '{:4d}-01-01T00:00:00'.format(args.year)
    start_date = Time(date_iso_string, format='isot', scale='utc', location=loc)
    sunset = obs.sun_set_time(start_date, which='nearest')

    while int(np.floor(sunset.decimalyear)) == args.year:
        sunset = obs.sun_set_time(sunset+oneday, which='nearest')
        dusk = obs.twilight_evening_astronomical(sunset, which='next')
        m = moon.get_moon(sunset, obs)
        illum = moon.moon_illumination(sunset, obs)
        ##
        if illum < args.illumination_threshold:
            schedule_night(sunset, dusk, 'dark ({:.0f}%)'.format(illum*100.))
        elif m.alt < 0*u.degree:
            moon_rise = obs.target_rise_time(sunset, m, which='next')
            time_to_rise = moon_rise - dusk
            if time_to_rise.sec*u.second > args.dark_time*u.hour:
                schedule_night(sunset, dusk, 'dark until {:.0f}% moon rise at {}'.format(illum*100., moon_rise.iso))
        elif m.alt >= 0*u.degree:
            moon_set = obs.target_set_time(sunset, m, which='next')
            time_to_set = moon_set - dusk
            if time_to_set.sec*u.second < args.wait_time*u.hour:
                schedule_night(sunset, dusk, 'dark after {:.0f}% moon sets at {}'.format(illum*100., moon_set.iso))


if __name__ == '__main__':
#     main()

    loc = EarthLocation.of_site('Keck Observatory')
    obs = Observer(loc)
    
    oneday = TimeDelta(60.*60.*24., format='sec')
    start_date = Time('2016-06-24T00:00:00', format='isot', scale='utc', location=loc)
    sunset = obs.sun_set_time(start_date, which='nearest')

    for i in range(0,20):
        sunset = obs.sun_set_time(sunset+oneday, which='nearest')
        dusk = obs.twilight_evening_astronomical(sunset, which='next')
        m = moon.get_moon(sunset, loc)
        illum = moon.moon_illumination(sunset, loc)
        
        if m.alt < 0*u.degree:
            est_moon_rise = obs.target_rise_time(sunset, FixedTarget(m), which='next')
            m = moon.get_moon(est_moon_rise, loc)
            moon_rise = obs.target_rise_time(est_moon_rise, FixedTarget(m), which='nearest')
            print('sunset: {}, dusk: {}, {:.0f}% moon rise: {}'.format(sunset.iso,
                  dusk.iso, illum*100., moon_rise.iso))
        else:
            est_moon_set = obs.target_set_time(sunset, FixedTarget(m), which='next')
            m = moon.get_moon(est_moon_set, loc)
            moon_set = obs.target_set_time(est_moon_set, FixedTarget(m), which='nearest')
            print('sunset: {}, dusk: {}, {:.0f}% moon set: {}'.format(sunset.iso,
                  dusk.iso, illum*100., moon_set.iso))
