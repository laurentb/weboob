# -*- coding: utf-8 -*-

# Copyright(C) 2016      Phyks
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


import itertools

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import CentQuatrePage, LoginPage, TicketsPage, TicketsDetailsPage


__all__ = ['CentQuatreBrowser']


class CentQuatreBrowser(LoginBrowser):
    BASEURL = 'https://billetterie.104.fr'
    login = URL(r'/account/login$', LoginPage)
    tickets = URL(r'/account/tickets', TicketsPage)
    ticketDetails = URL(r'/account/file\?(.*)?fileId=(?P<fileId>)', TicketsDetailsPage)
    unknown = URL(r'*', CentQuatrePage)

    def do_login(self):
        self.session.cookies.clear()
        self.login.go().login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

    @need_login
    def list_events(self, date_from, date_to):
        self.tickets.stay_or_go()
        tickets = self.page.list_tickets(date_from, date_to)
        events = iter([])
        for ticket in tickets:
            self.ticketDetails.stay_or_go(fileId=ticket)
            events = itertools.chain(events, self.page.get_event_details())
        return events

    @need_login
    def get_event(self, id):
        return self.ticketDetails.stay_or_go(fileId=id).get_event_details()

    @need_login
    def search_events(self, query):
        events = self.list_events(query.start_date, query.end_date)
        matching_events = []
        for event in events:
            if query.city and event.city != query.city:
                continue
            if query.ticket and event.ticket != query.ticket:
                continue
            if query.summary and event.summary != query.summary:
                continue
            matching_events.append(event)
