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

from .calendar import SensCritiquenCalendarEvent

from datetime import date, datetime, timedelta
from weboob.capabilities.base import empty
from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Filter, CleanText, Regexp, Join, Format, BrowserURL, Env
from weboob.browser.filters.html import Link


class Description(Filter):
    def filter(self, el):
        header = "//div[@class='pvi-hero-product']"
        section = "//section[@class='pvi-productDetails']"
        return Format(u'\n%s\n\n%s%s\n',
                      CleanText("(%s/div[@class='d-rubric-inner']/h1)[1]" % header),
                      Join(u'- ', "%s/ul/li" % section, newline=True, addBefore='- '),
                      Join(u'- Avec ', "%s/div[@class='pvi-productDetails-workers']/a" % section,
                           newline=True, addBefore='- Avec '))(el[0])


class FormatDate(Filter):
    def __init__(self, pattern, selector):
        super(FormatDate, self).__init__(selector)
        self.pattern = pattern

    def filter(self, _date):
        return _date.strftime(self.pattern)


class Date(Filter):
    def filter(self, el):
        spans_date = el[0].xpath("span[@class='d-date']")
        _date = date.today()
        if len(spans_date) == 2:
            day_number = int(spans_date[1].text)
            month = _date.month
            year = _date.year
            if day_number < _date.day:
                month = _date.month % 12 + 1
                if _date.month == 12:
                    year = _date.year + 1
            _date = date(day=day_number, month=month, year=year)
        elif spans_date[0].attrib['data-sc-day'] == 'Demain':
            _date += timedelta(days=1)
        str_time = el[0].xpath("time")[0].attrib['datetime'][:-6]
        _time = datetime.strptime(str_time, '%H:%M:%S')
        return datetime.combine(_date, _time.time())


class JsonResumePage(JsonPage):
    def get_resume(self):
        if self.doc['json']['success']:
            return self.doc['json']['data']


class EventPage(HTMLPage):
    @method
    class get_event(ItemElement):
        klass = SensCritiquenCalendarEvent

        obj_url = BrowserURL('event_page', _id=Env('_id'))
        obj_description = Description('.')


class FilmsPage(HTMLPage):
    @method
    class iter_films(ListElement):
        item_xpath = '//li[@class="elgr-mosaic "]/a'

        class item(ItemElement):
            klass = SensCritiquenCalendarEvent

            def condition(self):
                if '_id' in self.env and self.env['_id']:
                    return Format(u'%s#%s#%s',
                                  Regexp(Link('.'), '/film/(.*)'),
                                  FormatDate("%Y%m%d%H%M",
                                             Date('div/div[@class="elgr-data-diffusion"]')),
                                  CleanText('./div/span[@class="d-offset"]',
                                            replace=[(' ', '-')]))(self) == self.env['_id']
                return True

            def validate(self, obj):
                if 'date_from' in self.env and self.env['date_from'] and obj.start_date > self.env['date_from']:
                    if not self.env['date_to']:
                        return True
                    else:
                        if empty(obj.end_date):
                            if obj.start_date < self.env['date_to']:
                                return True
                        elif obj.end_date <= self.env['date_to']:
                            return True

                if '_id' in self.env:
                    return True

                return False

            obj_id = Format(u'%s#%s#%s',
                            Regexp(Link('.'), '/film/(.*)'),
                            FormatDate("%Y%m%d%H%M", Date('div/div[@class="elgr-data-diffusion"]')),
                            CleanText('./div/span[@class="d-offset"]', replace=[(' ', '-')]))
            obj_start_date = Date('div/div[@class="elgr-data-diffusion"]')
            obj_summary = Format('%s - %s',
                                 Regexp(CleanText('./div/img/@alt'), '^Affiche(.*)'),
                                 CleanText('./div/span[@class="d-offset"]'))
