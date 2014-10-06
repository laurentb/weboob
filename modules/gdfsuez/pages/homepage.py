# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mathieu Jourdan
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

from datetime import date

from weboob.deprecated.browser import Page
from weboob.capabilities.bill import Subscription


class LoginPage(Page):

    def login(self, login, password):
        self.browser.select_form('symConnexionForm')
        self.browser["portlet_login_plein_page_3{pageFlow.mForm.login}"] = unicode(login)
        self.browser["portlet_login_plein_page_3{pageFlow.mForm.password}"] = unicode(password)
        self.browser.submit()


class HomePage(Page):

    def on_loaded(self):
        pass


class AccountPage(Page):

    def get_subscription_list(self):
        table = self.document.xpath('//table[@id="ensemble_contrat_N0"]')[0]
        if len(table) > 0:
            # some clients may have subscriptions to gas and electricity,
            # but they receive a single bill
            # to avoid "boobill details" and "boobill bills" returning the same
            # table twice, we could return only one subscription for both.
            # We do not, and "boobill details" will take care of parsing only the
            # relevant section in the bill files.
            for line in table[0].xpath('//tbody/tr'):
                cells = line.xpath('td')
                snumber = cells[2].attrib['id'].replace('Contrat_', '')
                slabel = cells[0].xpath('a')[0].text.replace('offre', '').strip()
                d = unicode(cells[3].xpath('strong')[0].text.strip())
                sdate = date(*reversed([int(x) for x in d.split("/")]))
                sub = Subscription(snumber)
                sub._id = snumber
                sub.label = slabel
                sub.subscriber = unicode(cells[1])
                sub.renewdate = sdate
                yield sub


class TimeoutPage(Page):

    def on_loaded(self):
        pass
