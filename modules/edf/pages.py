# -*- coding: utf-8 -*-

# Copyright(C) 2013      Christophe Gouiran
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
import re
import urllib
from decimal import Decimal

from weboob.deprecated.browser import Page
from weboob.capabilities.bill import Subscription, Detail, Bill
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

base_url = "http://particuliers.edf.com/"


class EdfBasePage(Page):
    def is_logged(self):
        return (u'Me déconnecter' in self.document.xpath('//a/text()')) \
            or (self.document.xpath('//table[contains(@summary, "Informations sur mon")]'))


class LoginPage(EdfBasePage):
    def login(self, login, password):
        self.browser.select_form("identification")
        self.browser["login"] = str(login)
        self.browser["pswd"] = str(password)
        self.browser.submit()


class HomePage(EdfBasePage):
    def on_loaded(self):
        pass


class FirstRedirectionPage(EdfBasePage):
    def on_loaded(self):
        self.browser.select_form("form1")
        self.browser.submit()


class SecondRedirectionPage(EdfBasePage):
    def on_loaded(self):
        self.browser.select_form("redirectForm")
        self.browser.submit()


class OtherPage(EdfBasePage):
    def on_loaded(self):
        self.browser.open(base_url)


class AccountPage(EdfBasePage):

    def iter_subscription_list(self):
        boxHeader = self.document.xpath('//div[@class="boxHeader"]')[0]
        subscriber = self.parser.tocleanstring(boxHeader.xpath('.//p')[0])
        contract = self.parser.tocleanstring(boxHeader.xpath('.//p[@class="folderNumber"]')[0])
        if not re.search('^Contrat n\xb0\s*', contract):
            return
        contract = re.sub('Contrat n\xb0\s*', '', contract)
        number = re.sub('[^\d]', '', contract)
        sub = Subscription(number)
        sub._id = number
        sub.label = subscriber
        sub.subscriber = subscriber
        yield sub


class BillsPage(EdfBasePage):

    def iter_documents(self, sub):

        #pdb.set_trace()
        years = [None] + self.document.xpath('//ul[@class="years"]/li/a')

        for year in years:
            #pdb.set_trace()
            if year is not None and year.attrib['href']:
                self.browser.location(year.attrib['href'])

            tables = self.browser.page.document.xpath('//table[contains(@summary, "factures")]')
            for table in tables:
                for tr in table.xpath('.//tr'):
                    list_tds = tr.xpath('.//td')
                    if len(list_tds) == 0:
                        continue
                    url = re.sub('[\r\n\t]', '', list_tds[0].xpath('.//a')[0].attrib['href'])
                    date_search = re.search('dateFactureQE=(\d+/\d+/\d+)', url)
                    if not date_search:
                        continue

                    date = datetime.strptime(date_search.group(1), "%d/%m/%Y").date()
                    amount = self.parser.tocleanstring(list_tds[2])
                    if amount is None:
                        continue

                    bill = Bill()
                    bill.id = sub._id + "." + date.strftime("%Y%m%d")
                    bill.price = Decimal(FrenchTransaction.clean_amount(amount))
                    bill.currency = bill.get_currency(amount)
                    bill.date = date
                    bill.label = self.parser.tocleanstring(list_tds[0])
                    bill.format = u'pdf'
                    bill.type = u'bill'
                    bill._url = url
                    yield bill

    def get_document(self, bill):
        self.location(bill._url)


class LastPaymentsPage(EdfBasePage):

    def on_loaded(self):

        # Here we simulate ajax request to following URL:
        # https://monagencepart.edf.fr/ASPFront/appmanager/ASPFront/front/portlet_echeancier_2?_nfpb=true&_portlet.contentOnly=true&_portlet.instanceLabel=portlet_echeancier_2&_portlet.contentMode=FRAGMENT&_portlet.async=true&_portlet.pageLabel=page_mon_paiement&_portlet.lafUniqueId=aspDefinitionLabel&_portlet.portalUrl=%2FASPFront%2Fappmanager%2FASPFront%2Ffront&_portlet.portalId=ASPFront%09front&_portlet.contentType=text%2Fhtml%3B+charset%3DUTF-8&_portlet.asyncMode=compat_9_2&_portlet.title=CalendrierpaiementController&_nfsp=true
        params = {
            '_nfpb': 'true',
            '_portlet.async': 'true',
            '_portlet.portalId': 'ASPFront\tfront',
            '_portlet.contentOnly': 'true',
            '_portlet.title': 'CalendrierpaiementController',
            '_portlet.pageLabel': 'page_mon_paiement',
            '_portlet.asyncMode': 'compat_9_2',
            '_portlet.lafUniqueId': 'aspDefinitionLabel',
            '_portlet.contentMode': 'FRAGMENT',
            '_portlet.instanceLabel': 'portlet_echeancier_2',
            '_portlet.contentType': 'text/html; charset=UTF-8',
            '_portlet.portalUrl': '/ASPFront/appmanager/ASPFront/front',
            '_nfsp': 'true'
        }

        self.browser.location('/ASPFront/appmanager/ASPFront/front/portlet_echeancier_2?%s' % urllib.urlencode(params))


class LastPaymentsPage2(EdfBasePage):
    def iter_payments(self, sub):

        table = self.browser.page.document.xpath('//table[contains(@summary, "Informations sur mon")]')[0]
        for tr in table.xpath('.//tr'):
            list_tds = tr.xpath('.//td')
            if len(list_tds) == 0:
                continue
            date = datetime.strptime(self.parser.tocleanstring(list_tds[0]), "%d/%m/%Y").date()
            amount = self.parser.tocleanstring(list_tds[1])
            if amount is None:
                continue
            det = Detail()
            det.id = sub._id + "." + date.strftime("%Y%m%d")
            det.price = Decimal(re.sub('[^\d,-]+', '', amount).replace(',', '.'))
            det.datetime = date
            det.label = unicode(self.parser.tocleanstring(list_tds[2]))
            yield det
