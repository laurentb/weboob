# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, Filter, Env, Format, Decode, Time, Type
from weboob.browser.filters.html import CleanHTML, XPath
from weboob.browser.filters.json import Dict

from weboob.capabilities.calendar import CATEGORIES
from .calendar import AgendaculturelEvent
from datetime import datetime, time


class AgendaculturelCategory(Filter):
    def filter(self, text):
        if text == u'MusicEvent':
            return CATEGORIES.CONCERT
        elif text == u'TheaterEvent':
            return CATEGORIES.THEATRE
        elif text == u'VisuelArtsEvent':
            return CATEGORIES.EXPO
        elif text == u'Festival':
            return CATEGORIES.FEST
        else:
            return CATEGORIES.AUTRE


class AgendaculturelDate(Filter):
    def filter(self, text):
        return datetime.strptime(text, "%Y-%m-%d")


class BasePage(HTMLPage):
    def search_events(self, query_date_from):
        form = self.get_form(nr=0)
        form['search_month'] = query_date_from
        form.submit()

    @method
    class get_event(ItemElement):
        klass = AgendaculturelEvent

        def parse(self, el):
            _json = CleanText('.')(XPath('//script[@type="application/ld+json"][1]')(el)[0])

            try:
                from weboob.tools.json import json
                self.env['_json'] = json.loads(_json)
            except ValueError:
                self.env['_json'] = {}

        def validate(self, obj):
            return self.env['_json']

        obj_id = Format('%s.%s',
                        Env('region'),
                        Decode(Env('_id')))

        obj_summary = CleanText('//h1')

        def obj_description(self):
            desc = CleanHTML('//div[@class="description"]')(self)
            if not desc:
                desc = CleanText('//meta[@name="description"]/@content')(self)
            return desc

        def obj_start_date(self):
            if not self.env['_json']:
                return

            _time = Time(CleanText('//div[@class="hours"]'), default=None)(self)
            if not _time:
                _time = time.min
            date = AgendaculturelDate(Dict('startDate'))(self.env['_json'])
            return datetime.combine(date, _time)

        def obj_end_date(self):
            if not self.env['_json']:
                return

            date = AgendaculturelDate(Dict('endDate'))(self.env['_json'])
            return datetime.combine(date, time.max)

        def obj_url(self):
            if not self.env['_json']:
                return

            return Dict('url')(self.env['_json'])

        def obj_city(self):
            if not self.env['_json']:
                return

            return Dict('location/address/addressLocality')(self.env['_json'])

        def obj_category(self):
            if not self.env['_json']:
                return

            return AgendaculturelCategory(Dict('@type'))(self.env['_json'])

        def obj_location(self):
            if not self.env['_json']:
                return

            return Format('%s, %s',
                          Dict('location/name'),
                          Dict('location/address/streetAddress'))(self.env['_json'])

        def obj_price(self):
            if not self.env['_json']:
                return

            return Type(CleanText(Dict('offers/price', default="0")),
                        type=float,
                        default=0)(self.env['_json'])

    @method
    class list_events(ListElement):
        item_xpath = '//ul[has-class("list-event")]/li'

        class item(ItemElement):
            klass = AgendaculturelEvent

            def validate(self, obj):
                return self.check_date(obj) and self.check_category(obj)

            def check_date(self, obj):
                if self.env['date_from'] and obj.start_date >= self.env['date_from']:
                    if not self.env['date_to']:
                        return True
                    elif obj.end_date and obj.end_date <= self.env['date_to']:
                        return True
                    elif self.env['date_to'] >= obj.start_date:
                        return True
                return False

            def check_category(self, obj):
                return (not self.env['categories'] or obj.category in self.env['categories'])

            obj_id = Format('%s.%s',
                            Env('region'),
                            Regexp(CleanText('./div/a[@itemprop="url"]/@href'),
                                   '/(.*).html'))
            obj_summary = CleanText('./div/a[@itemprop="url"]')

            def obj_start_date(self):
                _date = Date(CleanText('./meta[@itemprop="startDate"]/@content'))(self)
                return datetime.combine(_date, time.min)

            obj_category = AgendaculturelCategory(Regexp(CleanText('./@itemtype'), 'http://schema.org/(.*)'))
