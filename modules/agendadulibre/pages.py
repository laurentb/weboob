# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from datetime import time, datetime, date

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Regexp, CleanText, DateTime, Env, Format, BrowserURL
from weboob.browser.filters.html import Link, XPath, CleanHTML
from weboob.tools.date import parse_french_date

from .calendar import AgendaDuLibreCalendarEvent


class EventPage(HTMLPage):
    @method
    class get_event(ItemElement):
        klass = AgendaDuLibreCalendarEvent

        obj_id = Env('_id')
        obj_url = BrowserURL('event_page', _id=Env('_id'))
        obj_summary = Format('%s %s',
                             CleanText('//meta[@name="geo:placename"]/@content'),
                             CleanText('//meta[@name="DC:title"]/@content'))
        obj_description = CleanHTML('//div[@class="description"]')
        obj_location = CleanText('//p[@class="full_address"]/span[1]')
        obj_city = CleanText('//meta[@name="geo:placename"]/@content')

        def obj_start_date(self):
            m = re.findall(r'\w* \w* \d?\d \w* \d{4} \w* \d{2}h\d{2}', CleanText('(//p)[1]')(self), re.UNICODE)
            if m:
                return DateTime(Regexp(CleanText('(//p)[1]'),
                                       '\w* \w* (\d?\d \w* \d{4}) \w* (\d{2}h\d{2}).*',
                                       '\\1 \\2',
                                       flags=re.UNICODE),
                                parse_func=parse_french_date)(self)

        def obj_end_date(self):
            m = re.findall(r'\w* \w* \d?\d \w* \d{4} \w* \d{2}h\d{2}', CleanText('(//p)[1]')(self), re.UNICODE)
            if m:
                if len(m) == 1:
                    return DateTime(Regexp(CleanText('(//p)[1]'),
                                           r'\w* \w* (\d?\d \w* \d{4}) \w* \d{2}h\d{2} \w* (\d{2}h\d{2})',
                                           '\\1 \\2',
                                           flags=re.UNICODE),
                                    parse_func=parse_french_date)(self)
                else:
                    return DateTime(Regexp(CleanText('(//p)[1]'),
                                           r'\w* \w* (\d?\d \w* \d{4}) \w* (\d{2}h\d{2})',
                                           '\\1 \\2',
                                           nth=-1,
                                           flags=re.UNICODE),
                                    parse_func=parse_french_date)(self)


class EventListPage(HTMLPage):
    @pagination
    @method
    class list_events(ListElement):
        item_xpath = '//td[starts-with(@class, "day")]/ul/li'

        def next_page(self):
            m = re.match('.*/events\?start_date=(\d{4})-(\d{2})-(\d{2})(&region=.*)?', self.page.url)
            if m:
                start = date(year=int(m.group(1)), month=int(m.group(2)), day=1)
                region = m.group(4) if m.group(4) else ''
                try:
                    next_month = start.replace(month=start.month + 1)
                except ValueError:
                    if start.month == 12:
                        next_month = start.replace(year=start.year + 1, month=1)
                    else:
                        raise
                if (self.env['date_to'] is None and
                    start < self.env['max_date']) or\
                   (self.env['date_to'] is not None and
                   datetime.combine(next_month, time.min) < self.env['date_to']):
                    return '/events?start_date=%s%s' % (next_month.strftime("%Y-%m-%d"), region)

        class item(ItemElement):
            klass = AgendaDuLibreCalendarEvent

            def condition(self):
                return len(XPath('.')(self.el)) > 0 and \
                    ('current-month' in XPath('./ancestor::td/@class')(self.el)[0])
            obj_id = Format('%s#%s',
                            CleanText('./ancestor::td/div[@class="day_number"]'),
                            Regexp(Link('./a'), '/events/(.*)'))
            obj_city = CleanText('./a/strong[@class="city"]')
            obj_summary = CleanText('./a')

            def obj_start_date(self):
                m = re.findall(r'\w* \w* \d?\d \w* \d{4} \w* \d{2}h\d{2}', CleanText('./@title')(self), re.UNICODE)
                if m:
                    return DateTime(Regexp(CleanText('./@title'),
                                           '\w* \w* (\d?\d \w* \d{4}) \w* (\d{2}h\d{2}).*',
                                           '\\1 \\2',
                                           flags=re.UNICODE),
                                    parse_func=parse_french_date)(self)

            def obj_end_date(self):
                m = re.findall(r'\w* \w* \d?\d \w* \d{4} \w* \d{2}h\d{2}', CleanText('./@title')(self), re.UNICODE)
                if m:
                    if len(m) == 1:
                        return DateTime(Regexp(CleanText('./@title'),
                                               r'\w* \w* (\d?\d \w* \d{4}) \w* \d{2}h\d{2} \w* (\d{2}h\d{2})',
                                               '\\1 \\2',
                                               flags=re.UNICODE),
                                        parse_func=parse_french_date)(self)
                    else:
                        return DateTime(Regexp(CleanText('./@title'),
                                               r'\w* \w* (\d?\d \w* \d{4}) \w* (\d{2}h\d{2})',
                                               '\\1 \\2',
                                               nth=-1,
                                               flags=re.UNICODE),
                                        parse_func=parse_french_date)(self)

            def validate(self, obj):
                return (self.is_valid_event(obj, self.env['city'], self.env['categories']) and
                        self.is_event_in_valid_period(obj.start_date, self.env['date_from'], self.env['date_to']))

            def is_valid_event(self, event, city, categories):
                if city and city != '' and city.upper() != event.city.upper():
                    return False
                if categories and len(categories) > 0 and event.category not in categories:
                    return False
                return True

            def is_event_in_valid_period(self, event_date, date_from, date_to):
                if event_date >= datetime.combine(date_from, time.min):
                    if not date_to:
                        return True
                    else:
                        if event_date <= date_to:
                            return True
                return False
