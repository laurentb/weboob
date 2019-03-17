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

from weboob.browser import LoginBrowser, need_login, URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import new_datetime

from .pages import (
    LoginPage, CalendarPage, HomePage, UsersPage,
    DocumentsPage, SubscriptionPage,
)


class LuccaBrowser(LoginBrowser):
    BASEURL = 'https://www.ilucca.net'

    login = URL('/login', LoginPage)
    home = URL('/home', HomePage)
    calendar = URL('/api/leaveAMPMs', CalendarPage)
    users = URL(r'/api/departments\?fields=id%2Cname%2Ctype%2Clevel%2Cusers.id%2Cusers.displayName%2Cusers.dtContractStart%2Cusers.dtContractEnd%2Cusers.manager.id%2Cusers.manager2.id%2Cusers.legalEntityID%2Cusers.calendar.id&date=since%2C1970-01-01', UsersPage)
    subscriptions = URL(r'/api/v3/users/me\?fields=id,firstName,lastName,allowsElectronicPayslip,culture,login,mail,personalemail', SubscriptionPage)
    payslips = URL(r'/api/v3/payslips\?fields=id,import\[name,endDate\]&orderby=import\.endDate,desc,import\.startDate,desc,import\.creationDate,desc&ownerID=(?P<subid>\d+)', DocumentsPage)

    def __init__(self, subdomain, *args, **kwargs):
        super(LuccaBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = 'https://%s.ilucca.net' % subdomain

    def do_login(self):
        try:
            self.login.go(data={
                'Login': self.username,
                'Password': self.password,
            })
        except ClientError as exc:
            if 'Incorrect credentials' in exc.response.text:
                raise BrowserIncorrectPassword()
            raise

        if not self.home.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def all_events(self, start, end):
        self.users.go()
        users = {u.id: u for u in self.page.iter_users()}

        last = None
        while True:
            if end:
                if end < start:
                    break
            else:
                if last and last + timedelta(days=300) < start:
                    self.logger.info('300 days without event, stopping')
                    break

            window_end = start + timedelta(days=14)

            params = {
                'date': 'between,%s,%s' % (start.strftime('%Y-%m-%d'), window_end.strftime('%Y-%m-%d')),
                'paging': '0,10000',
                'owner.id': ','.join(str(u.id) for u in users.values()),
                'fields': 'u,a,o,ls,mc,r,c,rw',
            }
            self.calendar.go(params=params)
            events = self.page.iter_events(start, users=users)
            for event in sorted(events, key=lambda ev: new_datetime(ev.start_date)):
                if end and event.start_date >= end:
                    continue
                yield event
                last = new_datetime(event.start_date)

            start = window_end

    @need_login
    def get_subscription(self):
        self.subscriptions.go()
        return self.page.get_subscription()

    @need_login
    def iter_documents(self, subid):
        self.payslips.go(subid=subid)
        return self.page.iter_documents(subid)
