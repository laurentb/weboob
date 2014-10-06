# -*- coding: utf-8 -*-

# Copyright(C) 2013      Christophe Lampin
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


from datetime import datetime
from decimal import Decimal
import re
import urllib
from weboob.deprecated.browser import Page
from weboob.capabilities.bill import Subscription, Detail, Bill


# Ugly array to avoid the use of french locale
FRENCH_MONTHS = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']


class LoginPage(Page):
    def login(self, login, password):
        self.browser.select_form('connexionCompteForm')
        self.browser["vp_connexion_portlet_1numPS"] = login.encode('utf8')
        self.browser["vp_connexion_portlet_1password"] = password.encode('utf8')
        self.browser.submit()


class HomePage(Page):

    def on_loaded(self):
        pass


class AccountPage(Page):

    def get_subscription_list(self):
        ident = self.document.xpath('//div[@id="identification"]')[0]
        prof = self.document.xpath('//div[@id="profession"]')[0]
        name = ident.xpath('//p/b')[0].text.replace('&nbsp;', ' ').strip()
        number = ident.xpath('//p')[1].text.replace('Cabinet', '').strip()
        label = prof.xpath('//div[@class="zoneTexte"]')[0].text.strip()
        sub = Subscription(number)
        sub._id = number
        sub.label = unicode(name) + ' ' + unicode(label)
        sub.subscriber = unicode(name)
        return sub


class HistoryPage(Page):

    def iter_history(self):
        table = self.document.xpath('//table[contains(concat(" ", @class, " "), " cTableauTriable ")]')[0].xpath('.//tr')
        for tr in table:
            list_a = tr.xpath('.//a')
            if len(list_a) == 0:
                continue
            date = tr.xpath('.//td')[0].text.strip()
            lot = list_a[0].text
            factures = tr.xpath('.//div[@class="cAlignGauche"]/a')
            factures_lbl = ''
            for a in factures:
                factures_lbl = factures_lbl + a.text + ' '
            montant = tr.xpath('.//div[@class="cAlignDroite"]')[0].text.strip()
            det = Detail()
            det.id = lot
            det.label = lot
            det.infos = factures_lbl
            det.datetime = datetime.strptime(date, "%d/%m/%Y").date()
            det.price = Decimal(montant.replace(',', '.'))
            yield det


class BillsPage(Page):

    def iter_bills(self):
        table = self.document.xpath('//table[@id="releveCompteMensuel"]')[0].xpath('.//tr')
        for tr in table:
            list_tds = tr.xpath('.//td')
            if len(list_tds) == 0:
                continue

            date_str = tr.xpath('.//td[@class="cAlignGauche"]')[0].text
            month_str = date_str.split()[0]
            date = datetime.strptime(re.sub(month_str, str(FRENCH_MONTHS.index(month_str) + 1), date_str), "%m %Y").date()
            amount = tr.xpath('.//td[@class="cAlignDroite"]')[0].text
            for format in ('CSV', 'PDF'):
                bil = Bill()
                bil.id = date.strftime("%Y%m") + format
                bil.date = date
                bil.label = u''+amount.strip()
                bil.format = u''+format
                filedate = date.strftime("%m%Y")
                bil._url = '/PortailPS/fichier.do'
                bil._args = {'FICHIER.type': format.lower() + '.releveCompteMensuel',
                             'dateReleve': filedate,
                             'FICHIER.titre': '',
                }
                yield bil

    def get_bill(self, bill):
        self.location(bill._url, urllib.urlencode(bill._args))
