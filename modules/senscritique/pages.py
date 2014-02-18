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

from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage
from .calendar import SensCritiquenCalendarEvent

from datetime import date, datetime, time


__all__ = ['ProgramPage']


class ProgramPage(BasePage):

    CHANNELS_PARAM = {
        'einst-3 elgr-data-logo': u'Action',
        'einst-8 elgr-data-logo': u'Canal+ Décalé',
        'einst-9 elgr-data-logo': u'Canal+ Family',
        'einst-12 elgr-data-logo': u'Ciné FX',
        'einst-13 elgr-data-logo': u'Polar',
        'einst-14 elgr-data-logo': u'Ciné+ Classic',
        'einst-15 elgr-data-logo': u'Ciné+ Club',
        'einst-16 elgr-data-logo': u'Ciné+ Emotion',
        'einst-17 elgr-data-logo': u'Ciné+ Famiz',
        'einst-18 elgr-data-logo': u'Ciné+ Frisson',
        'einst-19 elgr-data-logo': u'Ciné+ Premier',
        'einst-21 elgr-data-logo': u'Comédie+',
        'einst-24 elgr-data-logo': u'Disney Channel',
        'einst-25 elgr-data-logo': u'Disney Cinemagic',
        'einst-34 elgr-data-logo': u'Jimmy',
        'einst-37 elgr-data-logo': u'MCM',
        'einst-41 elgr-data-logo': u'OCS Géants',
        'einst-42 elgr-data-logo': u'OCS Choc',
        'einst-44 elgr-data-logo': u'OCS Max',
        'einst-45 elgr-data-logo': u'OCS City',
        'einst-49 elgr-data-logo': u'RTL 9',
        'einst-52 elgr-data-logo': u'TCM Cinéma',
        'einst-54 elgr-data-logo': u'Teva',
        'einst-59 elgr-data-logo': u'TV Breizh',
        'einst-4055 elgr-data-logo': u'Paramount Channel',
    }

    def find_event(self, _id):
        a = self.document.getroot().xpath("//a[@href='%s']" % _id, method='xpath')
        if a:
            event_date = self.get_event_date(a[0])
            return self.create_event(a[0], event_date)

    def count_events(self):
        return len(self.document.getroot().xpath("//a"))

    def list_events(self, date_from, date_to=None):
        for a in self.document.getroot().xpath("//a"):
            event_date = self.get_event_date(a)
            if self.is_valid_event(date_from, date_to, event_date):
                yield self.create_event(a, event_date)

    def create_event(self, a, event_date):
        event = SensCritiquenCalendarEvent(a.attrib['href'])

        title = self.parser.select(a, "span[@class='elgr-product-title']", 1, method='xpath').text
        channel_info = self.parser.select(a, "div/div[@class='elgr-data-channel']", method='xpath')
        if channel_info:
            channel = channel_info[0].text.strip()
        else:
            channel_info = self.parser.select(a,
                                              'div[@class="elgr-product-data"]/span',
                                              1,
                                              method='xpath').attrib['class']
            channel = self.CHANNELS_PARAM.get(channel_info)
        event.summary = u'%s - %s' % (title, channel)

        event.start_date = event_date
        event.end_date = datetime.combine(event_date.date(), time.max)
        return event

    def is_valid_event(self, date_from, date_to, event_date):
        if event_date >= date_from:
            if not date_to:
                return True
            else:
                if event_date < date_to:
                    return True
        return False

    def get_event_date(self, a):
        div_date = self.parser.select(a, "div/div[@class='elgr-data-diffusion']", 1, method='xpath')
        _date = self.parse_start_date(div_date)

        str_time = self.parser.select(div_date, "time", 1, method='xpath').attrib['datetime'][:-6]
        _time = datetime.strptime(str_time, '%H:%M:%S')

        return datetime.combine(_date, _time.time())

    def parse_start_date(self, div_date):
        spans_date = self.parser.select(div_date, "span[@class='d-date']", method='xpath')

        _date = date.today()
        if len(spans_date) == 2:
            day_number = int(spans_date[1].text)

            month = _date.month
            year = _date.year
            if day_number < _date.day:
                month = _date.month + 1
                if _date.month == 12:
                    year = _date.year + 1

            _date = date(day=day_number, month=month, year=year)

        return _date


class EventPage(BasePage):
    def get_event(self, url, event):

        event.url = url

        header = self.document.getroot().xpath("//div[@class='pvi-hero-product']")[0]

        title = self.parser.select(header, "div[@class='d-rubric-inner']/h1", 1, method='xpath').text.strip()
        year = self.parser.select(header, "div[@class='d-rubric-inner']/small", 1, method='xpath').text.strip()

        _infos = self.parser.select(header, "ul[@class='pvi-product-specs']/li", method='xpath')
        infos = ''
        for li in _infos:
            infos += u'- %s\n' % self.parser.tocleanstring(li)

        section = self.document.getroot().xpath("//section[@class='pvi-productDetails']")[0]
        _infos = self.parser.select(section, "ul/li", method='xpath')
        for li in _infos:
            infos += u'- %s\n' % self.parser.tocleanstring(li)

        _resume = self.parser.select(section, "p[@data-rel='full-resume']", method='xpath')
        if not _resume:
            _resume = self.parser.select(section, "p[@data-rel='small-resume']", method='xpath')
            if _resume:
                resume = html2text(self.parser.tostring(_resume[0]))
            else:
                resume = ""
        else:
            _id = self.parser.select(_resume[0], 'button', 1, method='xpath').attrib['data-sc-product-id']
            resume = self.browser.get_resume(url, _id)

        event.description = u'%s %s\n\n%s\n\n%s' % (title, year, infos, resume)
        return event
