# -*- coding: utf-8 -*-

# Copyright(C) 2013 Bezleputh
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

import re
import sys
from datetime import date, timedelta, time, datetime

from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter
from weboob.capabilities.base import empty
from weboob.capabilities.calendar import ICapCalendarEvent
from weboob.tools.application.repl import ReplApplication, defaultcount

__all__ = ['Boobcoming']


class ICalFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'start_date', 'end_date', 'summary')

    def start_format(self, **kwargs):
        self.output(u'BEGIN:VCALENDAR')
        self.output(u'VERSION:2.0')
        self.output(u'PRODID:-//hacksw/handcal//NONSGML v1.0//EN')

    def format_obj(self, obj, alias):
        result = u'BEGIN:VEVENT\n'
        result += u'DTSTART:%s\n' % obj.start_date.strftime("%Y%m%dT%H%M%SZ")
        result += u'DTEND:%s\n' % obj.end_date.strftime("%Y%m%dT%H%M%SZ")
        result += u'SUMMARY:%s\n' % obj.summary
        if hasattr(obj, 'location') and not empty(obj.location):
            result += u'LOCATION:%s\n' % obj.location

        if hasattr(obj, 'categories') and not empty(obj.categories):
            result += u'CATEGORIES:%s\n' % obj.categories

        if hasattr(obj, 'status') and not empty(obj.status):
            result += u'STATUS:%s\n' % obj.status

        if hasattr(obj, 'description') and not empty(obj.description):
            result += u'DESCRIPTION:%s\n' % obj.description.replace('\r\n', '\\n')

        if hasattr(obj, 'transp') and not empty(obj.transp):
            result += u'TRANSP:%s\n' % obj.transp

        if hasattr(obj, 'sequence') and not empty(obj.sequence):
            result += u'SEQUENCE:%s\n' % obj.sequence

        if hasattr(obj, 'url') and not empty(obj.url):
            result += u'URL:%s\n' % obj.url

        result += u'END:VEVENT'
        return result

    def flush(self, **kwargs):
        self.output(u'END:VCALENDAR')


class UpcomingListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'start_date', 'end_date', 'summary', 'category')

    def get_title(self, obj):
        return ' %s - %s ' % (obj.category, obj.summary)

    def get_description(self, obj):
        result = u''
        result += u'\tDate: %s\n' % obj.start_date.strftime('%A %d %B %Y')
        result += u'\tHour: %s - %s \n' % (obj.start_date.strftime('%H:%M'), obj.end_date.strftime('%H:%M'))
        return result.strip('\n\t')


class UpcomingFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'start_date', 'end_date', 'summary', 'category')

    def format_obj(self, obj, alias):
        result = u'%s%s - %s%s\n' % (self.BOLD, obj.category, obj.summary, self.NC)
        result += u'Date: %s\n' % obj.start_date.strftime('%A %d %B %Y')
        result += u'Hour: %s - %s\n' % (obj.start_date.strftime('%H:%M'), obj.end_date.strftime('%H:%M'))

        if hasattr(obj, 'location') and not empty(obj.location):
            result += u'Location: %s\n' % obj.location

        if hasattr(obj, 'event_planner') and not empty(obj.event_planner):
            result += u'Event planner: %s/%s \n' % (obj.event_planner)

        if hasattr(obj, 'entry') and not empty(obj.entry) and \
           hasattr(obj, 'max_entry') and not empty(obj.max_entry):
            result += u'Entry: %s/%s \n' % (obj.entry, obj.max_entry)
        elif hasattr(obj, 'entry') and not empty(obj.entry):
            result += u'Entry: %s \n' % (obj.entry)
        elif hasattr(obj, 'max_entry') and not empty(obj.max_entry):
            result += u'Max entries: %s \n' % (obj.max_entry)

        if hasattr(obj, 'description') and not empty(obj.description):
            result += u'Description:\n %s\n\n' % obj.description

        if hasattr(obj, 'price') and not empty(obj.price):
            result += u'Price: %i\n' % obj.price

        if hasattr(obj, 'url') and not empty(obj.url):
            result += u'url: %s\n' % obj.url

        return result


class Boobcoming(ReplApplication):
    APPNAME = 'boobcoming'
    VERSION = '0.h'
    COPYRIGHT = 'Copyright(C) 2012 Bezleputh'
    DESCRIPTION = "Console application to see upcoming events."
    SHORT_DESCRIPTION = "see upcoming events"
    CAPS = ICapCalendarEvent
    EXTRA_FORMATTERS = {'upcoming_list': UpcomingListFormatter,
                        'upcoming': UpcomingFormatter,
                        #'ical_formatter': ICalFormatter,
                        }
    COMMANDS_FORMATTERS = {'list': 'upcoming_list',
                           'info': 'upcoming',
                           #'export': 'ical_formatter',
                           }

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

    @defaultcount(10)
    def do_list(self, line):
        """
        list [PATTERN]
        List upcoming events, pattern can be an english or french  week day, 'today' or a date
        """

        self.change_path([u'events'])
        if line:
            _date = self.parse_date(line)
            if not _date:
                print >>sys.stderr, 'Invalid argument: %s' % self.get_command_help('list', short=True)
                return 2

            date_from = datetime.combine(_date, time.min)
            date_to = datetime.combine(_date, time.max)
        else:
            date_from = datetime.now()
            date_to = None

        for backend, event in self.do('list_events', date_from, date_to):
            self.cached_format(event)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        """
        info ID

        Get information about an event.
        """

        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        event = self.get_object(_id, 'get_event')

        if not event:
            print >>sys.stderr, 'Upcoming event not found: %s' % _id
            return 3

        self.start_format()
        self.format(event)

    def start_format(self, **kwargs):
        result = u'BEGIN:VCALENDAR\n'
        result += u'VERSION:2.0\n'
        result += u'PRODID:-//hacksw/handcal//NONSGML v1.0//EN\n'
        return result

    def format_event(self, obj):
        result = u'BEGIN:VEVENT\n'
        result += u'DTSTART:%s\n' % obj.start_date.strftime("%Y%m%dT%H%M%SZ")
        result += u'DTEND:%s\n' % obj.end_date.strftime("%Y%m%dT%H%M%SZ")
        result += u'SUMMARY:%s\n' % obj.summary
        if hasattr(obj, 'location') and not empty(obj.location):
            result += u'LOCATION:%s\n' % obj.location

        if hasattr(obj, 'categories') and not empty(obj.categories):
            result += u'CATEGORIES:%s\n' % obj.categories

        if hasattr(obj, 'status') and not empty(obj.status):
            result += u'STATUS:%s\n' % obj.status

        if hasattr(obj, 'description') and not empty(obj.description):
            result += u'DESCRIPTION:%s\n' % obj.description.replace('\r\n', '\\n')

        if hasattr(obj, 'transp') and not empty(obj.transp):
            result += u'TRANSP:%s\n' % obj.transp

        if hasattr(obj, 'sequence') and not empty(obj.sequence):
            result += u'SEQUENCE:%s\n' % obj.sequence

        if hasattr(obj, 'url') and not empty(obj.url):
            result += u'URL:%s\n' % obj.url

        result += u'END:VEVENT\n'
        return result

    def end_format(self):
        return u'END:VCALENDAR'

    def do_export(self, line):
        """
        export FILENAME [ID1 ID2 ID3 ...]

        ID is the identifier of the event. If no ID every events are exported

        FILENAME is where to write the file. If FILENAME is '-', the file is written to stdout.

        Export event in ICALENDAR format
        """
        if not line:
            print >>sys.stderr, 'This command takes at leat one argument: %s' % self.get_command_help('export')
            return 2

        _file, args = self.parse_command_args(line, 2, req_n=1)

        l = self.retrieve_events(args)
        buff = self.create_buffer(l)

        if _file == "-":
            print buff
        else:
            try:
                dest = self.check_file_ext(_file)
                with open(dest, 'w') as f:
                    f.write(buff.encode('ascii', 'ignore'))
            except IOError as e:
                print >>sys.stderr, 'Unable to write bill in "%s": %s' % (dest, e)
                return 1

    def create_buffer(self, l):
        buff = self.start_format()

        for item in l:
            buff += self.format_event(item)

        buff += self.end_format()

        return buff

    def retrieve_events(self, args):
        l = []

        if not args:
            _ids = []
            for backend, event in self.do('list_events', datetime.now(), None):
                _ids.append(event.id)
        else:
            _ids = args.strip().split(' ')

        for _id in _ids:
            event = self.get_object(_id, 'get_event')

            if not event:
                print >>sys.stderr, 'Upcoming event not found: %s' % _id
                return 3

            l.append(event)

        return l

    def check_file_ext(self, _file):
        splitted_file = _file.split('.')
        if splitted_file[-1] != 'ics':
            return "%s.ics" % _file
        else:
            return _file

    def get_date_from_day(self, day):
        today = date.today()
        today_day_number = today.weekday()

        requested_day_number = self.WEEK[day.upper()]

        if today_day_number < requested_day_number:
            day_to_go = requested_day_number - today_day_number
        else:
            day_to_go = 7 - today_day_number + requested_day_number

        requested_date = today + timedelta(day_to_go)
        return date(requested_date.year, requested_date.month, requested_date.day)

    def parse_date(self, string):
        matches = re.search('\s*([012]?[0-9]|3[01])\s*/\s*(0?[1-9]|1[012])\s*/?(\d{2}|\d{4})?$', string)
        if matches:
            year = matches.group(3)
            if not year:
                year = date.today().year
            elif len(year) == 2:
                year = 2000 + int(year)
            return date(int(year), int(matches.group(2)), int(matches.group(1)))

        elif string.upper() in self.WEEK.keys():
            return self.get_date_from_day(string)

        elif string.upper() == "TODAY":
            return date.today()

    def do_attends(self, line):
        """
        attend IS_ATTENDING [ID1 ID2 ID3 ...]

        ID is the identifier of the event. If no ID every events are exported

        IS_ATTENDING is a booleanizable value that indicate if attending or not

        Export event in ICALENDAR format
        """
        if not line:
            print >>sys.stderr, 'This command takes at leat one argument: %s' % self.get_command_help('export')
            return 2

        attending, args = self.parse_command_args(line, 2, req_n=1)

        l = self.retrieve_events(args)
        is_attending = self.booleanize(attending)

        if not is_attending:
            print >> sys.stderr, "Cannot booleanize ambiguous value '%s'" % attending
            return 2

        for event in l:
            self.do('attends_event', event, is_attending)

    def booleanize(self, value):
        """Return value as a boolean."""

        true_values = ("yes", "true")
        false_values = ("no", "false")

        if isinstance(value, bool):
            return value

        if value.lower() in true_values:
            return True

        elif value.lower() in false_values:
            return False
