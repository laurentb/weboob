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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, EventPage, ListPage, SearchPage

from datetime import datetime


class ResidentadvisorBrowser(LoginBrowser):
    BASEURL = 'http://www.residentadvisor.net'

    # this ID is used by Resident Advisor
    ALBANIA_ID = 223

    login = URL('https://www.residentadvisor.net/login', LoginPage)
    event = URL('/event.aspx\?(?P<id>\d+)', EventPage)
    list_events = URL('/events.aspx\?ai=(?P<city>\d+)&v=(?P<v>.+)&yr=(?P<year>\d{4})&mn=(?P<month>\d\d?)&dy=(?P<day>\d\d?)', ListPage)
    search_page = URL('/search.aspx\?searchstr=(?P<query>.+)&section=events&titles=1', SearchPage)
    attends = URL('/Output/addhandler.ashx')

    def do_login(self):
        self.login.stay_or_go()
        self.page.login(self.username, self.password)

        # in case of successful connection, we are redirected to the home page
        if self.login.is_here():
            raise BrowserIncorrectPassword()

    def get_events(self, city, v = 'week', date = datetime.now()):
        self.list_events.go(v = v, year = date.year, month = date.month, day = date.day, city = city)
        assert self.list_events.is_here()

        for event in self.page.get_events():
            yield event

    def get_event(self, _id):
        self.event.go(id = _id)

        if not self.event.is_here():
            return None

        event = self.page.get_event()
        event.id = _id
        event.url = self.event.build(id = _id)

        return event

    def search_events_by_summary(self, pattern):
        self.search_page.go(query = pattern)
        assert self.search_page.is_here()

        for event in self.page.get_events():
            yield event

    def get_country_city_id(self, country, city):
        now = datetime.now()

        self.list_events.go(v = 'day', year = now.year, month = now.month, day = now.day, city = self.ALBANIA_ID)
        assert self.list_events.is_here()

        country_id = self.page.get_country_id(country)

        if country_id is None:
            return None

        self.list_events.go(v = 'day', year = now.year, month = now.month, day = now.day, city = country_id)
        assert self.list_events.is_here()

        city_id = self.page.get_city_id(city)

        if city_id is None:
            return None

        return city_id

    def get_city_id(self, city):
        now = datetime.now()

        country_id = self.ALBANIA_ID
        city_id = None

        while True:
            self.list_events.go(v = 'day', year = now.year, month = now.month, day = now.day, city = country_id)
            assert self.list_events.is_here()

            city_id = self.page.get_city_id(city)
            country_id = self.page.get_country_id_next_to(country_id)

            # city_id != None => city found
            # country_id = None => no more country, city not found
            if city_id is not None or country_id is None:
                break

        return city_id

    @need_login
    def attends_event(self, id, is_attending):
        data = {'type': 'saveFavourite',
                'action':'attending',
                'id': id}

        if not is_attending:
            data['type'] = 'deleteFavourite'

        self.attends.open(data = data)
