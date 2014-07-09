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

from weboob.tools.html import html2text
from .calendar import SensCritiquenCalendarEvent

from datetime import date, datetime, time, timedelta

from weboob.tools.browser2.page import HTMLPage, method, JsonPage
from weboob.tools.browser2.elements import ItemElement, ListElement
from weboob.tools.browser2.filters import Filter, Link, CleanText, Regexp, Attr, Join, Format


__all__ = ['AjaxPage', 'EventPage', 'JsonResumePage']


class Channel(Filter):

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

    def filter(self, el):
        channel_info = el[0].xpath('div/div[@class="elgr-data-channel"]')
        if channel_info:
            channel = CleanText('.')(channel_info[0])
        else:
            channel_info = Attr('div[@class="elgr-product-data"]/span', 'class')(el[0])
            channel = self.CHANNELS_PARAM.get(channel_info)
        return channel


class Date(Filter):
    def filter(self, el):
        spans_date = el[0].xpath("span[@class='d-date']")
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
        elif spans_date[0].attrib['data-sc-day'] == 'Demain':
            _date += timedelta(days=1)
        str_time = el[0].xpath("time")[0].attrib['datetime'][:-6]
        _time = datetime.strptime(str_time, '%H:%M:%S')
        return datetime.combine(_date, _time.time())


class FormatDate(Filter):
    def __init__(self, pattern, selector):
        super(FormatDate, self).__init__(selector)
        self.pattern = pattern

    def filter(self, date):
        return date.strftime(self.pattern)


class AjaxPage(HTMLPage):

    def count_events(self):
        return len(self.doc.xpath("//a"))

    @method
    class list_events(ListElement):
        item_xpath = '//a'
        ignore_duplicate = True

        class item(ItemElement):
            klass = SensCritiquenCalendarEvent

            def condition(self):
                if '_id' in self.env and self.env['_id']:
                    return Format(u'%s#%s#%s',
                                  Regexp(Link('.'), '/film/(.*)'),
                                  FormatDate("%Y%m%d%H%M", Date('div/div[@class="elgr-data-diffusion"]')),
                                  CleanText(Channel('.'), replace=[(' ', '-')]))(self) == self.env['_id']
                return True

            def validate(self, obj):
                if 'date_from' in self.env and self.env['date_from'] and obj.start_date > self.env['date_from']:
                    if not self.env['date_to']:
                        return True
                    else:
                        if obj.end_date <= self.env['date_to']:
                            return True

                if '_id' in self.env:
                    return True

                return False

            class CombineDate(Filter):
                def filter(self, _date):
                    return datetime.combine(_date, time.max)

            class Summary(Filter):
                def filter(self, el):
                    title = Regexp(Attr('div/img', 'alt'), '^Affiche(.*)')(el[0])
                    channel = Channel('.')(el[0])
                    return u'%s - %s' % (title, channel)

            obj_id = Format(u'%s#%s#%s',
                            Regexp(Link('.'), '/film/(.*)'),
                            FormatDate("%Y%m%d%H%M", Date('div/div[@class="elgr-data-diffusion"]')),
                            CleanText(Channel('.'), replace=[(' ', '-')]))
            obj_start_date = Date('div/div[@class="elgr-data-diffusion"]')
            obj_end_date = CombineDate(obj_start_date)
            obj_summary = CleanText(Summary('.'))


class Description(Filter):
    def filter(self, el):
        header = "//div[@class='pvi-hero-product']"
        section = "//section[@class='pvi-productDetails']"
        return Format(u'%s %s\n\n%s%s\n\n',
                      CleanText("%s/div[@class='d-rubric-inner']/h1" % header),
                      CleanText("%s/div[@class='d-rubric-inner']/small" % header),
                      Join(u'- %s\n', "%s/ul[@class='pvi-product-specs']/li" % header),
                      Join(u'- %s\n', "%s/ul/li" % section))(el[0])


class Resume(Filter):
    def filter(self, el):
        _resume = el[0].xpath("p[@data-rel='full-resume']")
        if not _resume:
            _resume = el[0].xpath("p[@data-rel='small-resume']")
            if _resume:
                resume = html2text(CleanText(_resume[0])(self))[6:]
                return resume


class EventPage(HTMLPage):
    @method
    class get_event(ItemElement):
        klass = SensCritiquenCalendarEvent

        def parse(self, el):
            event = self.obj
            event.url = self.page.url
            resume = Resume('//section[@class="pvi-productDetails"]')(self)
            if not resume:
                resume = self.obj._resume
            description = Description('.')(self)
            event.description = u'%s%s' % (description, resume)
            return event


class JsonResumePage(JsonPage):
    def get_resume(self):
        if self.doc['json']['success']:
            return self.doc['json']['data']
