# DarkMoonCalendar

A quick script to loop through the days of a given year and output a list of nights which are good for observing in the evening based on a set of criteria.  These criteria are:

1. If the moon is down at sunset and won't rise until a specified number of hours after astronomical twilight ends (providing at least that many hours of dark time), then the night is good for observing.
2. If the moon is up at sunset but sets within a specified number of hours after astronomical twilight ends, then the night is good for observing.

The output is a CSV file which is formatted for Google Calendar import.  Each calendar event will have a title indicating which criteria were satisfied.  For example "Dark until 01:23 AM when 42% moon rises" or "Dark after 09:02 PM when 11% moon sets".