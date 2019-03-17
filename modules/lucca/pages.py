# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import timedelta

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.capabilities.calendar import BaseCalendarEvent, STATUS
from weboob.capabilities.bill import (
    Subscription, Document, DocumentTypes,
)
from weboob.tools.date import new_date, parse_date
from weboob.tools.compat import urljoin


class LoginPage(HTMLPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    pass


class User(object):
    id = None
    name = None
    start = None
    end = None


class UsersPage(LoggedPage, JsonPage):
    def iter_users(self):
        for dpt in self.doc['data']:
            for d in dpt['users']:
                u = User()
                u.id = d['id']
                u.name = d['displayName']

                v = d['dtContractStart']
                if v:
                    u.start = parse_date(v)
                v = d['dtContractEnd']
                if v:
                    u.end = parse_date(v)

                yield u


class CalendarPage(LoggedPage, JsonPage):
    @staticmethod
    def _offset(start_date, offset):
        return start_date + timedelta(days=offset)

    def iter_events(self, start_date, users):
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        for d in self.doc['data']:
            if not d['ls']: # seems to be validation state
                continue
            assert d['ls'] == 2

            user = users[d['u']]

            ev = BaseCalendarEvent()
            ev.timezone = 'Europe/Paris'
            ev.summary = user.name
            ev.status = STATUS.CONFIRMED
            ev.start_date = self._offset(start_date, d['o'])

            if d['a'] == 2:
                ev.end_date = ev.start_date + timedelta(days=1)

                ev.start_date = ev.start_date.date()
                ev.end_date = ev.end_date.date()
            elif d['a'] == 1:
                ev.start_date = ev.start_date + timedelta(hours=12)
                ev.end_date = ev.start_date + timedelta(hours=12)
            else:
                assert d['a'] == 0
                ev.end_date = ev.start_date + timedelta(hours=12)

            if user.end and new_date(user.end) < new_date(ev.start_date):
                continue

            yield ev


class SubscriptionPage(LoggedPage, JsonPage):
    def get_subscription(self):
        sub = Subscription()
        sub.id = str(self.doc['data']['id'])
        sub.subscriber = sub.label = self.doc['header']['principal']
        return sub


class DocumentsPage(LoggedPage, JsonPage):
    def iter_documents(self, subid):
        for d in self.doc['data']['items']:
            doc = Document()
            doc.id = '%s_%s' % (subid, d['id'])
            doc._docid = d['id']
            doc.label = d['import']['name']
            doc.date = parse_date(d['import']['endDate'])
            doc.url = urljoin(self.url, '/pagga/download/%s' % doc._docid)
            doc.type = DocumentTypes.BILL
            doc.format = 'pdf'
            yield doc
