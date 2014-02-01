# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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
from datetime import datetime, time

import weboob.tools.date as date_util
from weboob.tools.browser import BasePage
from .calendar import BiplanCalendarEventConcert, BiplanCalendarEventTheatre

__all__ = ['ProgramPage', 'EventPage']


def parse_b(b):
    to_return = []
    for item in b.replace('\n', '\t').replace(' ', '\t').split('\t'):
        if not (item is None or item == ''):
            to_return.append(u'%s' % item)
    return to_return


class ProgramPage(BasePage):
    def list_events(self, date_from, date_to=None, city=None, categories=None, is_concert=True):
        divs = self.document.getroot().xpath("//div[@class='ligne']")
        for i in range(2, len(divs)):
            event = self.create_event(divs[i], date_from, date_to, city, categories, is_concert=is_concert)
            if event:
                yield event

    def create_event(self, div, date_from, date_to, city=None, categories=None, is_concert=True):
        re_id = re.compile('/(.*?).html', re.DOTALL)
        a_id = self.parser.select(div, "div/a", 1, method='xpath')
        b = self.parser.select(div, "div/div/b", 2, method='xpath')

        _id = re_id.search(a_id.attrib['href']).group(1)
        date = self.parse_date(b[0].text_content())

        re_time = re.compile('(\d{1,2}h[\d{1,2}]?)', re.DOTALL)
        start_end_date = re_time.findall(b[1].text_content().split('-')[0].strip())

        if start_end_date:
            time_price = parse_b(b[1].text_content())

            start_time = self.parse_start_time(start_end_date[0])
            start_date = datetime.combine(date, start_time)

            if len(start_end_date) > 1:
                end_time = self.parse_start_time(start_end_date[1])
                end_date = datetime.combine(start_date, end_time)
            else:
                end_date = datetime.combine(start_date, time.max)

        if _id and self.is_event_in_valid_period(start_date, date_from, date_to):
            if is_concert:
                event = BiplanCalendarEventConcert(_id)
            else:
                event = BiplanCalendarEventTheatre(_id)

            event.start_date = start_date
            event.end_date = end_date

            price = time_price[time_price.index('-') + 1:]
            parsed_price = re.findall(r"\d*\,\d+|\d+", " ".join(price))

            if parsed_price and len(parsed_price) > 0:
                event.price = float(parsed_price[0].replace(',', '.'))
            else:
                event.price = float(0)

            event.summary = u'%s' % self.parser.select(div, "div/div/div/a/strong", 1, method='xpath').text

            if self.is_valid_event(event, city, categories):
                return event

    def is_valid_event(self, event, city, categories):
        if city and city != '' and city.upper() != event.city.upper():
            return False

        if categories and len(categories) > 0 and event.category not in categories:
            return False

        return True

    def is_event_in_valid_period(self, event_date, date_from, date_to):
        if event_date >= date_from:
            if not date_to:
                return True
            else:
                if event_date <= date_to:
                    return True
        return False

    def parse_start_time(self, _time):
        start_time = _time.split('h')
        time_hour = start_time[0]
        time_minutes = 0
        if len(start_time) > 1 and start_time[1]:
            time_minutes = start_time[1]
        return time(int(time_hour), int(time_minutes))

    def parse_date(self, b):
        content = parse_b(b)
        a_date = content[1:content.index('-')]

        for fr, en in date_util.DATE_TRANSLATE_FR:
            a_date[1] = fr.sub(en, a_date[1])

        if (datetime.now().month > datetime.strptime(a_date[1], "%B").month):
            a_date.append(u'%i' % (datetime.now().year + 1))
        else:
            a_date.append(u'%i' % (datetime.now().year))

        return date_util.parse_french_date(" ".join(a_date))


class EventPage(BasePage):
    def get_event(self, url, event=None):
        div = self.document.getroot().xpath("//div[@id='popup']")[0]
        if not event:
            re_id = re.compile('http://www.lebiplan.org/(.*?).html', re.DOTALL)
            _id = re_id.search(url).group(1)
            if div.attrib['class'] == 'theatre-popup':
                event = BiplanCalendarEventTheatre(_id)
            else:
                event = BiplanCalendarEventConcert(_id)

        b = self.parser.select(div, "div/b", 1, method='xpath').text_content()
        splitted_b = b.split('-')

        parsed_price = re.findall(r"\d*\,\d+|\d+", " ".join(parse_b(splitted_b[-1])))

        if parsed_price and len(parsed_price) > 0:
            event.price = float(parsed_price[0].replace(',', '.'))
        else:
            event.price = float(0)

        _date = date_util.parse_french_date(" ".join(parse_b(splitted_b[0])))

        re_time = re.compile('(\d{1,2}h[\d{1,2}]?)', re.DOTALL)
        start_end_date = re_time.findall(splitted_b[2])

        if start_end_date:
            start_time = self.parse_start_time(start_end_date[0])

            if len(start_end_date) > 1:
                end_time = self.parse_start_time(start_end_date[1])
            else:
                end_time = time.max

        event.start_date = datetime.combine(_date, start_time)
        event.end_date = datetime.combine(_date, end_time)

        event.url = url

        event.summary = u'%s' % self.parser.select(div, "div/div/span", 1, method='xpath').text_content()
        event.description = u'%s' % self.parser.select(div,
                                                       "div/div[@class='presentation-popup']",
                                                       1,
                                                       method='xpath').text_content().strip()
        return event

    def parse_start_time(self, _time):
        start_time = _time.split('h')
        time_hour = start_time[0]
        time_minutes = 0
        if len(start_time) > 1 and start_time[1]:
            time_minutes = start_time[1]
        return time(int(time_hour), int(time_minutes))
