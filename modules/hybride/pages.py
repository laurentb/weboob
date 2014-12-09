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

from .calendar import HybrideCalendarEvent

import weboob.tools.date as date_util

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Filter, CleanText, Env, Format, BrowserURL, Regexp
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.html import Link


class Date(Filter):
    def filter(self, text):
        return date_util.parse_french_date(text)


class ProgramPage(HTMLPage):

    @method
    class list_events(ListElement):
        item_xpath = '//div[@class="itemContainer itemContainerLast"]'

        class item(ItemElement):
            klass = HybrideCalendarEvent

            def validate(self, obj):
                return self.check_date(obj) and self.check_city(obj) and self.check_category(obj)

            def check_date(self, obj):
                if self.env['date_from'] and obj.start_date >= self.env['date_from']:
                    if not self.env['date_to']:
                        return True
                    else:
                        if obj.end_date <= self.env['date_to']:
                            return True
                return False

            def check_city(self, obj):
                return (not self.env['city'] or self.env['city'].upper() == obj.city.upper())

            def check_category(self, obj):
                return (not self.env['categories'] or obj.category in self.env['categories'])

            obj_id = Regexp(Link('div/div[@class="catItemHeader"]/h3[@class="catItemTitle"]/a'), '/programme/item/(.*?).html')
            obj_start_date = Date(CleanText('div/div[@class="catItemHeader"]/span[@class="catItemDateCreated"]'))
            obj_summary = CleanText('div/div[@class="catItemHeader"]/h3[@class="catItemTitle"]/a')


class EventPage(HTMLPage):

    @method
    class get_event(ItemElement):
        klass = HybrideCalendarEvent

        obj_id = Env('_id')
        obj_start_date = Date(CleanText('//span[@class="itemDateCreated"]'))
        obj_summary = CleanText('//h2[@class="itemTitle"]')
        obj_description = Format('%s\n%s',
                                 CleanHTML('//div[@class="itemIntroText"]'),
                                 CleanHTML('//div[@class="itemFullText"]'))
        obj_url = BrowserURL('event_page', _id=Env('_id'))
