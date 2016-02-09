# -*- coding: utf-8 -*-

# Copyright(C) 2012  Fourcot Florent
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

import time
import StringIO

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from .pages import HomePage, LoginPage, HistoryPage, PdfPage
from weboob.capabilities.bill import Detail
from weboob.capabilities.base import NotAvailable


__all__ = ['Leclercmobile']


class Leclercmobile(Browser):
    DOMAIN = 'www.securelmobile.fr'
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    PAGES = {'.*pgeWERL008_Login.aspx.*':       LoginPage,
             '.*EspaceClient/pgeWERL013_Accueil.aspx':     HomePage,
             '.*pgeWERL009_ReleveConso.aspx.*': HistoryPage,
             '.*ReleveConso.ashx.*': PdfPage
             }
    accueil = "/EspaceClient/pgeWERL013_Accueil.aspx"
    login = "/EspaceClient/pgeWERL008_Login.aspx"
    conso = "/EspaceClient/pgeWERL009_ReleveConso.aspx"
    bills = '/EspaceClient/pgeWERL015_RecupReleveConso.aspx?m=-'

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location(self.accueil)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.username.isdigit()

        if not self.is_on_page(LoginPage):
            self.location(self.login)

        form = self.page.login(self.username, self.password)

        # Site display a javascript popup to wait
        while self.page.iswait():
            # In this popup can be an error displayed
            if self.page.iserror():
                raise BrowserIncorrectPassword()
            time.sleep(1)
            self.page.next(self.username, form)

        # The last document contain a redirect url in the javascript
        self.location(self.page.getredirect())

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def viewing_html(self):
        # To prevent unknown mimetypes sent by server, we assume we
        # are always on a HTML document.
        return True

    def get_subscription_list(self):
        if not self.is_on_page(HomePage):
            self.location(self.acceuil)

        return self.page.get_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(HomePage):
            self.location(self.accueil)

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self):
        if not self.is_on_page(HistoryPage):
            self.location(self.conso)
        maxid = self.page.getmaxid()

        for i in range(maxid + 1):
            response = self.openurl(self.bills + str(i))
            mimetype = response.info().get('Content-Type', '').split(';')[0]
            if mimetype == "application/pdf":
                pdf = PdfPage(StringIO.StringIO(response.read()))
                for call in pdf.get_calls():
                    call.label = call.label.strip()
                    yield call

    def get_details(self):
        if not self.is_on_page(HistoryPage):
            self.location(self.conso)
        response = self.openurl(self.bills + "0")
        mimetype = response.info().get('Content-Type', '').split(';')[0]
        if mimetype == "application/pdf":
            pdf = PdfPage(StringIO.StringIO(response.read()))
            for detail in pdf.get_details():
                yield detail

    def iter_documents(self, parentid):
        if not self.is_on_page(HistoryPage):
            self.location(self.conso)
        return self.page.date_bills(parentid)

    def get_document(self, id):
        assert isinstance(id, basestring)
        if not self.is_on_page(HistoryPage):
            self.location(self.conso)
        parentid = id[0:10]
        l = self.page.date_bills(parentid)
        for a in l:
            if a.id == id:
                return a

    def get_balance(self):
        if not self.is_on_page(HistoryPage):
            self.location(self.conso)
        detail = Detail()
        detail.label = u"Balance"
        for calls in self.get_history():
            if "Votre solde" in calls.label:
                detail.price = calls.price
                return detail
        detail.price = NotAvailable
        return detail
