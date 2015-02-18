# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015     Christophe Lampin
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
from weboob.browser.pages import HTMLPage
from weboob.capabilities.bill import Subscription, Detail, Bill
from weboob.browser.filters.standard import CleanText

# Ugly array to avoid the use of french locale
FRENCH_MONTHS = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']

class AmeliBasePage(HTMLPage):
    def is_logged(self):
        if self.doc.xpath('//a[@id="id_lien_deco"]'):
            logged = True
        else:
            logged = False
        self.logger.debug('logged: %s' % (logged))
        return logged

class LoginPage(AmeliBasePage):
    def login(self, login, password):
        form = self.get_form('//form[@name="connexionCompteForm"]')
        form['connexioncompte_2numSecuriteSociale'] = login.encode('utf8')
        form['connexioncompte_2codeConfidentiel'] = password.encode('utf8')
        form.submit()

class HomePage(AmeliBasePage):
    pass

class AccountPage(AmeliBasePage):
    def iter_subscription_list(self):
        name = CleanText('//div[@id="bloc_contenu_masituation"]/h3', replace=[('Titulaire du compte : ', '')])(self.doc)
        number = re.sub('[^\d]+', '', self.doc.xpath('//div[@id="bloc_contenu_masituation"]/ul/li')[2].text)
        sub = Subscription(number)
        sub._id = number
        sub.label = unicode(name)
        sub.subscriber = unicode(name)
        yield sub

        nb_childs = 0
        childs = self.doc.xpath('//div[@class="bloc_infos"]')
        for child in childs:
            name = CleanText('.//h3[1]')(child)
            nb_childs = nb_childs + 1
            number = "AFFILIE" + str(nb_childs)
            sub = Subscription(number)
            sub._id = number
            sub.label = unicode(name)
            sub.subscriber = unicode(name)
            yield sub


class LastPaymentsPage(AmeliBasePage):
    def iter_last_payments(self):
        list_table = self.doc.xpath('//table[@id="tabDerniersPaiements"]')
        if len(list_table) > 0:
            table = list_table[0].xpath('.//tr')
            for tr in table:
                list_a = tr.xpath('.//a')
                if len(list_a) == 0:
                    continue
                yield list_a[0].attrib.get('href').replace(':443','')


class PaymentDetailsPage(AmeliBasePage):
    def iter_payment_details(self, sub):
        if sub._id.isdigit():
            idx = 0
        else:
            idx = sub._id.replace('AFFILIE', '')
        if len(self.doc.xpath('//div[@class="centrepage"]/h2')) > idx or self.doc.xpath('//table[@id="DetailPaiement3"]') > idx:
            id_str = self.doc.xpath('//div[@class="centrepage"]/h2')[idx].text.strip()
            m = re.match('.*le (.*) pour un montant de.*', id_str)
            if m:
                id_str = m.group(1)
                id_date = datetime.strptime(id_str, '%d/%m/%Y').date()
                id = sub._id + "." + datetime.strftime(id_date, "%Y%m%d")
                table = self.doc.xpath('//table[@class="tableau"]')[idx].xpath('.//tr')
                line = 1
                last_date = None
                for tr in table:
                    tds = tr.xpath('.//td')
                    if len(tds) == 0:
                        continue

                    det = Detail()

                    if len(tds) == 5:
                        date_str = tds[0].text
                        det.id = id + "." + str(line)
                        det.label = unicode(tds[1].text.strip())

                        jours = tds[2].text
                        if jours is None:
                            jours = '0'

                        montant = tds[3].text
                        if montant is None:
                            montant = '0'

                        price = tds[4].text
                        if price is None:
                            price = '0'

                        if date_str is None or date_str == '':
                            det.infos = u''
                            det.datetime = last_date
                        else:
                            det.infos = date_str + u' (' + unicode(re.sub('[^\d,-]+', '', jours)) + u'j) * ' + unicode(re.sub('[^\d,-]+', '', montant)) + u'€'
                            det.datetime = datetime.strptime(date_str.split(' ')[3], '%d/%m/%Y').date()
                            last_date = det.datetime
                        det.price = Decimal(re.sub('[^\d,-]+', '', price).replace(',', '.'))

                    if len(tds) == 6:
                        date_str = tds[0].text
                        det.id = id + "." + str(line)
                        det.label = unicode(tds[1].text.strip())

                        paye = tds[2].text
                        if paye is None:
                            paye = '0'

                        base = tds[3].text
                        if base is None:
                            base = '0'

                        taux = tds[4].text
                        if taux is None:
                            taux = '0'

                        price = tds[5].text
                        if price is None:
                            price = '0'


                        if date_str is None or date_str == '':
                            det.infos = u''
                            det.datetime = last_date
                        else:
                            det.infos = u'Payé ' + unicode(re.sub('[^\d,-]+', '', paye)) + u'€ / Base ' + unicode(re.sub('[^\d,-]+', '', base)) + u'€ / Taux ' + unicode(re.sub('[^\d,-]+', '', taux)) + '%'
                            det.datetime = datetime.strptime(date_str, '%d/%m/%Y').date()
                            last_date = det.datetime
                        det.price = Decimal(re.sub('[^\d,-]+', '', price).replace(',', '.'))
                    line = line + 1
                    yield det


class BillsPage(AmeliBasePage):
    def iter_bills(self, sub):
        table = self.doc.xpath('//table[@id="relevesMensuels"]')[0].xpath('.//tr')
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
            amount = re.sub('[^\d,-]+', '', amount)
            bil = Bill()
            bil.id = sub._id + "." + date.strftime("%Y%m")
            bil.date = date
            bil.price = Decimal('-'+amount.strip().replace(',','.'))
            bil.format = u'pdf'
            bil.label = date.strftime("%Y%m%d")
            bil._url = '/PortailAS/PDFServletReleveMensuel.dopdf?PDF.moisRecherche='+date.strftime("%m%Y")
            yield bil

    def get_bill(self, bill):
        self.location(bill._url, urllib.urlencode(bill._args))
