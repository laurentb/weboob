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


from datetime import date, timedelta
try:
    from dateutil import tz
except ImportError:
    raise ImportError('Please install python-dateutil')


__all__ = ['local2utc', 'utc2local', 'LinearDateGuesser']


def local2utc(date):
    date = date.replace(tzinfo=tz.tzlocal())
    date = date.astimezone(tz.tzutc())
    return date


def utc2local(date):
    date = date.replace(tzinfo=tz.tzutc())
    date = date.astimezone(tz.tzlocal())
    return date

class LinearDateGuesser(object):
    """
    The aim of this class is to guess the exact date object from
    a day and a month, but not a year.

    It works with a start date (default is today), and all dates must be
    sorted from recent to older.
    """

    def __init__(self, current_date=None, date_max_bump=timedelta(7)):
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
        while 1:
            try:
                return date(start_year, month, day)
            except ValueError, e:
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
