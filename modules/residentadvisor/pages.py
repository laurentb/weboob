# -*- coding: utf-8 -*-

# Copyright(C) 2014      Alexandre Morignot
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


from weboob.capabilities.calendar import CATEGORIES, STATUS, TICKET
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.html import Attr, CleanHTML, Link
from weboob.browser.filters.standard import CleanDecimal, CleanText, Date, CombineDate, DateTime, Regexp, Time, Type
from weboob.browser.pages import HTMLPage
from weboob.capabilities.calendar import BaseCalendarEvent

from datetime import timedelta


class BasePage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath('//li[@id="profile"]/span[contains(text(), "Welcome")]'))


class LoginPage(BasePage):
    def login(self, username, password):
        form = self.get_form()
        form['UsernameOrEmailAddress'] = username
        form['Password'] = password
        form.submit()


class ListPage(BasePage):
    @method
    class get_events(ListElement):
        item_xpath = '//ul[@id="items"]/li/article'

        class item(ItemElement):
            klass = BaseCalendarEvent

            obj_url = Link('./div[@class="bbox"]/h1/a')
            obj_id = Regexp(Link('./div[@class="bbox"]/h1/a'), r'aspx\?(.+)')
            obj_location = CleanText('./div[@class="bbox"]/span/a')
            obj_start_date = DateTime(Attr('.//time', 'datetime'))
            obj_summary = Regexp(Attr('./div[@class="bbox"]/h1/a', 'title'), r'details of (.+)')
            obj_category = CATEGORIES.CONCERT
            obj_status = STATUS.CONFIRMED

    def get_country_id(self, country):
        return Regexp(Link('//li[@id="liCountry"]/ul/li/a[./text()="%s"]' % country, default=''), r'ai=([^&]+)&?', default=None)(self.doc)

    def get_city_id(self, city):
        return Regexp(Link('//li[@id="liArea"]/ul/li/a[./text()="%s"]' % city, default=''), r'ai=([^&]+)&?', default=None)(self.doc)

    def get_country_id_next_to(self, country_id):
        return Regexp(Link('//li[@id="liCountry"]/ul/li[./a[contains(@href, "ai=%s&")]]/following-sibling::li/a' % country_id, default=''), r'ai=([^&]+)&?', default=None)(self.doc)


class EventPage(BasePage):
    @method
    class get_event(ItemElement):
        klass = BaseCalendarEvent

        obj_summary = CleanText('//div[@id="sectionHead"]/h1')
        obj_description = CleanHTML('//div[@id="event-item"]/div[3]/p[2]')
        obj_price = CleanDecimal(Regexp(CleanText('//aside[@id="detail"]/ul/li[3]'), r'Cost /[^\d]*([\d ,.]+).', default=''), default=None)
        obj_location = Regexp(CleanText('//aside[@id="detail"]/ul/li[2]'), r'Venue / (.+)')
        obj_booked_entries = Type(CleanText('//h1[@id="MembersFavouriteCount"]'), type=int)
        obj_status = STATUS.CONFIRMED
        obj_category = CATEGORIES.CONCERT

        _date = Date(CleanText('//aside[@id="detail"]/ul/li[1]/a[1]'))

        def obj_start_date(self):
            start_time = Time(Regexp(CleanText('//aside[@id="detail"]/ul/li[1]'), r'(\d{2}:\d{2}) -'))(self)
            return CombineDate(self._date, start_time)(self)

        def obj_end_date(self):
            end_time = Time(Regexp(CleanText('//aside[@id="detail"]/ul/li[1]'), r'- (\d{2}:\d{2})'))(self)

            end_date = CombineDate(self._date, end_time)(self)
            if end_date > self.obj_start_date():
                end_date += timedelta(days = 1)

            return end_date

        def obj_ticket(self):
            li_class = Attr('//li[@id="tickets"]//li[1]', 'class', default=None)(self)

            if li_class:
                if li_class == 'closed':
                    return TICKET.CLOSED
                else:
                    return TICKET.AVAILABLE

            return TICKET.NOTAVAILABLE


class SearchPage(BasePage):
    @method
    class get_events(ListElement):
        item_xpath = '//main/ul/li/section/div/div/ul/li'

        class item(ItemElement):
            klass = BaseCalendarEvent

            obj_url = Link('./a[1]')
            obj_id = Regexp(Link('./a[1]'), r'\?(\d+)')
            obj_summary = CleanText('./a[1]')
            obj_start_date = Date(CleanText('./span[1]'))
            obj_category = CATEGORIES.CONCERT
            obj_status = STATUS.CONFIRMED
