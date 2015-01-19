# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import dateutil.parser
from datetime import date as real_date, datetime as real_datetime, timedelta
import time
import re
try:
    from dateutil import tz
except ImportError:
    raise ImportError('Please install python-dateutil')


__all__ = ['local2utc', 'utc2local', 'LinearDateGuesser', 'date', 'datetime', 'new_date', 'new_datetime', 'closest_date']


def local2utc(dateobj):
    dateobj = dateobj.replace(tzinfo=tz.tzlocal())
    dateobj = dateobj.astimezone(tz.tzutc())
    return dateobj


def utc2local(dateobj):
    dateobj = dateobj.replace(tzinfo=tz.tzutc())
    dateobj = dateobj.astimezone(tz.tzlocal())
    return dateobj


class date(real_date):
    def strftime(self, fmt):
        return strftime(self, fmt)

    @classmethod
    def from_date(cls, d):
        return cls(d.year, d.month, d.day)


class datetime(real_datetime):
    def strftime(self, fmt):
        return strftime(self, fmt)

    def combine(self, date, time):
        return datetime(date.year, date.month, date.day, time.hour, time.minute, time.microsecond, time.tzinfo)

    def date(self):
        return date(self.year, self.month, self.day)

    @classmethod
    def from_datetime(cls, dt):
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)


def new_date(d):
    """ Generate a safe date from a datetime.date object """
    return date(d.year, d.month, d.day)


def new_datetime(d):
    """
    Generate a safe datetime from a datetime.date or datetime.datetime object
    """
    kw = [d.year, d.month, d.day]
    if isinstance(d, real_datetime):
        kw.extend([d.hour, d.minute, d.second, d.microsecond, d.tzinfo])
    return datetime(*kw)


# No support for strftime's "%s" or "%y".
# Allowed if there's an even number of "%"s because they are escaped.
_illegal_formatting = re.compile(r"((^|[^%])(%%)*%[sy])")


def _findall(text, substr):
    # Also finds overlaps
    sites = []
    i = 0
    while True:
        j = text.find(substr, i)
        if j == -1:
            break
        sites.append(j)
        i = j+1
    return sites


def strftime(dt, fmt):
    if dt.year >= 1900:
        return super(type(dt), dt).strftime(fmt)
    illegal_formatting = _illegal_formatting.search(fmt)
    if illegal_formatting:
        raise TypeError("strftime of dates before 1900 does not handle" + illegal_formatting.group(0))

    year = dt.year
    # For every non-leap year century, advance by
    # 6 years to get into the 28-year repeat cycle
    delta = 2000 - year
    off = 6*(delta // 100 + delta // 400)
    year = year + off

    # Move to around the year 2000
    year = year + ((2000 - year)//28)*28
    timetuple = dt.timetuple()
    s1 = time.strftime(fmt, (year,) + timetuple[1:])
    sites1 = _findall(s1, str(year))

    s2 = time.strftime(fmt, (year+28,) + timetuple[1:])
    sites2 = _findall(s2, str(year+28))

    sites = []
    for site in sites1:
        if site in sites2:
            sites.append(site)

    s = s1
    syear = "%4d" % (dt.year,)
    for site in sites:
        s = s[:site] + syear + s[site+4:]
    return s


class LinearDateGuesser(object):
    """
    The aim of this class is to guess the exact date object from
    a day and a month, but not a year.

    It works with a start date (default is today), and all dates must be
    sorted from recent to older.
    """

    def __init__(self, current_date=None, date_max_bump=timedelta(31)):
        self.date_max_bump = date_max_bump
        if current_date is None:
            current_date = date.today()
        self.current_date = current_date

    def try_assigning_year(self, day, month, start_year, max_year):
        """
        Tries to create a date object with day, month and start_year and returns
        it.
        If it fails due to the year not matching the day+month combination
        (i.e. due to a ValueError -- TypeError and OverflowError are not
        handled), the previous or next years are tried until max_year is
        reached.
        In case initialization still fails with max_year, this function raises
        a ValueError.
        """
        while True:
            try:
                return date(start_year, month, day)
            except ValueError as e:
                if start_year == max_year:
                    raise e
                start_year += cmp(max_year, start_year)

    def set_current_date(self, current_date):
        self.current_date = current_date

    def guess_date(self, day, month, change_current_date=True):
        """ Returns a date object built from a given day/month pair. """

        today = self.current_date
        # The website only provides dates using the 'DD/MM' string, so we have to
        # determine the most possible year by ourselves. This implies tracking
        # the current date.
        # However, we may also encounter "bumps" in the dates, e.g. "12/11,
        # 10/11, 10/11, 12/11, 09/11", so we have to be, well, quite tolerant,
        # by accepting dates in the near future (say, 7 days) of the current
        # date. (Please, kill me...)
        # We first try to keep the current year
        naively_parsed_date = self.try_assigning_year(day, month, today.year, today.year - 5)
        if (naively_parsed_date.year != today.year):
            # we most likely hit a 29/02 leading to a change of year
            if change_current_date:
                self.set_current_date(naively_parsed_date)
            return naively_parsed_date

        if (naively_parsed_date > today + self.date_max_bump):
            # if the date ends up too far in the future, consider it actually
            # belongs to the previous year
            parsed_date = date(today.year - 1, month, day)
            if change_current_date:
                self.set_current_date(parsed_date)
        elif (naively_parsed_date > today and naively_parsed_date <= today + self.date_max_bump):
            # if the date is in the near future, consider it is a bump
            parsed_date = naively_parsed_date
            # do not keep it as current date though
        else:
            # if the date is in the past, as expected, simply keep it
            parsed_date = naively_parsed_date
            # and make it the new current date
            if change_current_date:
                self.set_current_date(parsed_date)
        return parsed_date


class ChaoticDateGuesser(LinearDateGuesser):
    """
    This class aim to find the guess the date when you know the
    day and month and the minimum year
    """

    def __init__(self, min_date, current_date=None, date_max_bump=timedelta(31)):
        if min_date is None:
            raise ValueError("min_date is not set")
        self.min_date = min_date
        super(ChaoticDateGuesser, self).__init__(current_date, date_max_bump)

    def guess_date(self, day, month):
        """Returns a possible date between min_date and current_date"""
        parsed_date = super(ChaoticDateGuesser, self).guess_date(day, month, False)
        if parsed_date >= self.min_date:
            return parsed_date
        else:
            raise ValueError("%s is inferior to min_date %s" % (parsed_date, self.min_date))


DATE_TRANSLATE_FR = [(re.compile(ur'janvier', re.I),   ur'january'),
                     (re.compile(ur'février', re.I),   ur'february'),
                     (re.compile(ur'mars', re.I),      ur'march'),
                     (re.compile(ur'avril', re.I),     ur'april'),
                     (re.compile(ur'mai', re.I),       ur'may'),
                     (re.compile(ur'juin', re.I),      ur'june'),
                     (re.compile(ur'juillet', re.I),   ur'july'),
                     (re.compile(ur'août?', re.I),      ur'august'),
                     (re.compile(ur'septembre', re.I), ur'september'),
                     (re.compile(ur'octobre', re.I),   ur'october'),
                     (re.compile(ur'novembre', re.I),  ur'november'),
                     (re.compile(ur'décembre', re.I),  ur'december'),
                     (re.compile(ur'jan\.', re.I),   ur'january'),
                     (re.compile(ur'janv\.', re.I),   ur'january'),
                     (re.compile(ur'\bjan\b', re.I),   ur'january'),
                     (re.compile(ur'fév\.', re.I),   ur'february'),
                     (re.compile(ur'\bfév\b', re.I),   ur'february'),
                     (re.compile(ur'avr\.', re.I),     ur'april'),
                     (re.compile(ur'\bavr\b', re.I),     ur'april'),
                     (re.compile(ur'juil\.', re.I),   ur'july'),
                     (re.compile(ur'juill\.', re.I),   ur'july'),
                     (re.compile(ur'\bjuil\b', re.I),   ur'july'),
                     (re.compile(ur'sep\.', re.I), ur'september'),
                     (re.compile(ur'sept\.', re.I), ur'september'),
                     (re.compile(ur'\bsep\b', re.I), ur'september'),
                     (re.compile(ur'oct\.', re.I),   ur'october'),
                     (re.compile(ur'\boct\b', re.I),   ur'october'),
                     (re.compile(ur'nov\.', re.I),  ur'november'),
                     (re.compile(ur'\bnov\b', re.I),  ur'november'),
                     (re.compile(ur'déc\.', re.I),  ur'december'),
                     (re.compile(ur'\bdéc\b', re.I),  ur'december'),
                     (re.compile(ur'lundi', re.I),     ur'monday'),
                     (re.compile(ur'mardi', re.I),     ur'tuesday'),
                     (re.compile(ur'mercredi', re.I),  ur'wednesday'),
                     (re.compile(ur'jeudi', re.I),     ur'thursday'),
                     (re.compile(ur'vendredi', re.I),  ur'friday'),
                     (re.compile(ur'samedi', re.I),    ur'saturday'),
                     (re.compile(ur'dimanche', re.I),  ur'sunday')]


def parse_french_date(date):
    for fr, en in DATE_TRANSLATE_FR:
        date = fr.sub(en, date)

    return dateutil.parser.parse(date)


WEEK   = {'MONDAY': 0,
          'TUESDAY': 1,
          'WEDNESDAY': 2,
          'THURSDAY': 3,
          'FRIDAY': 4,
          'SATURDAY': 5,
          'SUNDAY': 6,
          'LUNDI': 0,
          'MARDI': 1,
          'MERCREDI': 2,
          'JEUDI': 3,
          'VENDREDI': 4,
          'SAMEDI': 5,
          'DIMANCHE': 6,
          }


def get_date_from_day(day):
    today = date.today()
    today_day_number = today.weekday()

    requested_day_number = WEEK[day.upper()]

    if today_day_number < requested_day_number:
        day_to_go = requested_day_number - today_day_number
    else:
        day_to_go = 7 - today_day_number + requested_day_number

    requested_date = today + timedelta(day_to_go)
    return date(requested_date.year, requested_date.month, requested_date.day)


def parse_date(string):
    matches = re.search('\s*([012]?[0-9]|3[01])\s*/\s*(0?[1-9]|1[012])\s*/?(\d{2}|\d{4})?$', string)
    if matches:
        year = matches.group(3)
        if not year:
            year = date.today().year
        elif len(year) == 2:
            year = 2000 + int(year)
        return date(int(year), int(matches.group(2)), int(matches.group(1)))

    elif string.upper() in WEEK.keys():
        return get_date_from_day(string)

    elif string.upper() == "TODAY":
        return date.today()


def closest_date(date, date_from, date_to):
    """
    Adjusts year so that the date is closest to the given range.
    Transactions dates in a statement usually contain only day and month.
    Statement dates range have a year though.
    Merge them all together to get a full transaction date.
    """
    # If the date is within given range, we're done.
    if date_from <= date <= date_to:
        return date

    dates = [real_datetime(year, date.month, date.day)
             for year in xrange(date_from.year, date_to.year+1)]

    # Ideally, pick the date within given range.
    for d in dates:
        if date_from <= d <= date_to:
            return d

    # Otherwise, return the most recent date in the past.
    return min(dates, key=lambda d: abs(d-date_from))


def test():
    dt = real_datetime
    range1 = [dt(2012,12,20), dt(2013,1,10)]

    assert closest_date(dt(2012,12,15), *range1) == dt(2012,12,15)
    assert closest_date(dt(2000,12,15), *range1) == dt(2012,12,15)
    assert closest_date(dt(2020,12,15), *range1) == dt(2012,12,15)

    assert closest_date(dt(2013,1,15), *range1) == dt(2013,1,15)
    assert closest_date(dt(2000,1,15), *range1) == dt(2013,1,15)
    assert closest_date(dt(2020,1,15), *range1) == dt(2013,1,15)

    assert closest_date(dt(2013,1,1), *range1) == dt(2013,1,1)
    assert closest_date(dt(2000,1,1), *range1) == dt(2013,1,1)
    assert closest_date(dt(2020,1,1), *range1) == dt(2013,1,1)

    range2 = [dt(2012,12,20), dt(2014,1,10)]
    assert closest_date(dt(2012,12,15), *range2) == dt(2013,12,15)
    assert closest_date(dt(2014,1,15), *range2) == dt(2013,1,15)
