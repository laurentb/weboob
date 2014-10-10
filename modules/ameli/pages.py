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
import re
import urllib
from decimal import Decimal
from weboob.deprecated.browser import Page, BrokenPageError
from weboob.capabilities.bill import Subscription, Detail, Bill


# Ugly array to avoid the use of french locale
FRENCH_MONTHS = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']


class AmeliBasePage(Page):
    def is_logged(self):
        try:
            self.parser.select(self.document.getroot(), 'a.logout', 1)
        except BrokenPageError:
            logged = False
        else:
            logged = True
        self.logger.debug('logged: %s' % (logged))
        return logged


class LoginPage(AmeliBasePage):
    def login(self, login, password):
        self.browser.select_form('connexionCompteForm')
        self.browser["connexioncompte_2numSecuriteSociale"] = login.encode('utf8')
        self.browser["connexioncompte_2codeConfidentiel"] = password.encode('utf8')
        self.browser.submit()


class HomePage(AmeliBasePage):
    pass


class AccountPage(AmeliBasePage):
    def iter_subscription_list(self):
        idents = self.document.xpath('//div[contains(@class, "blocfond")]')
        enfants = 0
        for ident in idents:
            if len(ident.xpath('.//h3')) == 0:
                continue

            name = self.parser.tocleanstring(ident.xpath('.//h3')[0])
            lis = ident.xpath('.//li')
            if len(lis) > 3:
                number = re.sub('[^\d]+', '', ident.xpath('.//li')[3].text)
            else:
                enfants = enfants + 1
                number = "AFFILIE" + str(enfants)
            sub = Subscription(number)
            sub._id = number
            sub.label = unicode(name)
            sub.subscriber = unicode(name)
            yield sub


class LastPaymentsPage(AmeliBasePage):
    def iter_last_payments(self):
        list_table = self.document.xpath('//table[@id="tabDerniersPaiements"]')
        if len(list_table) > 0:
            table = list_table[0].xpath('.//tr')
            for tr in table:
                list_a = tr.xpath('.//a')
                if len(list_a) == 0:
                    continue
                yield list_a[0].attrib.get('href')


class PaymentDetailsPage(AmeliBasePage):
    def iter_payment_details(self, sub):
        if sub._id.isdigit():
            idx = 0
        else:
            idx = sub._id.replace('AFFILIE', '')
        if len(self.document.xpath('//div[@class="centrepage"]/h2')) > idx or self.document.xpath('//table[@id="DetailPaiement3"]') > idx:
            id_str = self.document.xpath('//div[@class="centrepage"]/h2')[idx].text.strip()
            m = re.match('.*le (.*) pour un montant de.*', id_str)
            if m:
                id_str = m.group(1)
                id_date = datetime.strptime(id_str, '%d/%m/%Y').date()
                id = sub._id + "." + datetime.strftime(id_date, "%Y%m%d")
                table = self.document.xpath('//table[@class="tableau"]')[idx].xpath('.//tr')
                line = 1
                last_date = None
                for tr in table:
                    tds = tr.xpath('.//td')
                    if len(tds) == 0:
                        continue
                    date_str = tds[0].text
                    det = Detail()
                    det.id = id + "." + str(line)
                    det.label = unicode(tds[1].text.strip())
                    if date_str is None or date_str == '':
                        det.infos = u''
                        det.datetime = last_date
                    else:
                        det.infos = u'Payé ' + unicode(re.sub('[^\d,-]+', '', tds[2].text)) + u'€ / Base ' + unicode(re.sub('[^\d,-]+', '', tds[3].text)) + u'€ / Taux ' + unicode(re.sub('[^\d,-]+', '', tds[4].text)) + '%'
                        det.datetime = datetime.strptime(date_str, '%d/%m/%Y').date()
                        last_date = det.datetime
                    det.price = Decimal(re.sub('[^\d,-]+', '', tds[5].text).replace(',', '.'))
                    line = line + 1
                    yield det


class BillsPage(AmeliBasePage):
    def iter_bills(self, sub):
        table = self.document.xpath('//table[@id="tableauDecompte"]')[0].xpath('.//tr')
        for tr in table:
            list_tds = tr.xpath('.//td')
            if len(list_tds) == 0:
                continue
            date_str = list_tds[0].text
            month_str = date_str.split()[0]
            date = datetime.strptime(re.sub(month_str, str(FRENCH_MONTHS.index(month_str) + 1), date_str), "%m %Y").date()
            amount = list_tds[1].text
            if amount is None:
                continue
            amount = re.sub(' euros', '', amount)
            bil = Bill()
            bil.id = sub._id + "." + date.strftime("%Y%m")
            bil.date = date
            bil.label = u''+amount.strip()
            bil.format = u'pdf'
            filedate = date.strftime("%m%Y")
            bil._url = '/PortailAS/PDFServletReleveMensuel.dopdf'
            bil._args = {'PDF.moisRecherche': filedate}
            yield bil

    def get_bill(self, bill):
        self.location(bill._url, urllib.urlencode(bill._args))
