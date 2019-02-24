# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015     Christophe Lampin
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

from __future__ import unicode_literals

from datetime import datetime
import re
from decimal import Decimal

from weboob.browser.filters.html import Attr, XPathNotFound
from weboob.browser.pages import HTMLPage, RawPage, LoggedPage
from weboob.capabilities.bill import DocumentTypes, Subscription, Detail, Bill
from weboob.browser.filters.standard import CleanText, Regexp
from weboob.exceptions import BrowserUnavailable


# Ugly array to avoid the use of french locale

FRENCH_MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


class AmeliBasePage(HTMLPage):
    @property
    def logged(self):
        if self.doc.xpath('//a[contains(text(), "Déconnexion")]'):
            logged = True
        else:
            logged = False
        self.logger.debug('logged: %s' % (logged))
        return logged

    def is_error(self):
        errors = self.doc.xpath('//*[@id="r_errors"]')
        if errors:
            return errors[0].text_content()

        errors = CleanText('//p[@class="msg_erreur"]', default='')(self.doc)
        if errors:
            return errors

        errors = CleanText('//div[@class="zone-alerte"]/span')(self.doc)
        if errors:
            return errors

        return False


class LoginPage(AmeliBasePage):
    def login(self, login, password):
        form = self.get_form('//form[@name="connexionCompteForm"]')
        form['connexioncompte_2numSecuriteSociale'] = login.encode('utf8')
        form['connexioncompte_2codeConfidentiel'] = password.encode('utf8')
        form.submit()

    def locate_to_cgu_page(self):
        try:
            # they've put a head tag inside body, yes i know...
            url = Regexp(Attr('//div[@id="connexioncompte_2"]//meta', 'content'), r'url=(.*)')(self.doc)
        except XPathNotFound:
            # no cgu to validate
            return
        self.browser.location(url)


class CguPage(AmeliBasePage):
    def get_cgu(self):
        return CleanText('//div[@class="page_nouvelles_cgus"]/p[1]')(self.doc)


class HomePage(AmeliBasePage):
    pass


class AccountPage(AmeliBasePage):
    def iter_subscription_list(self):
        names_list = self.doc.xpath('//span[@class="NomEtPrenomLabel"]')
        fullname = CleanText(newlines=True).filter(names_list[0])
        number = re.sub(r'[^\d]+', '', CleanText('//span[@class="blocNumSecu"]', replace=[(' ', '')])(self.doc))
        sub = Subscription(number)
        sub._id = number
        sub.label = fullname
        firstname = CleanText('//span[@class="prenom-titulaire"]')(self.doc)
        sub.subscriber = firstname
        yield sub


class PaymentsPage(AmeliBasePage):
    def get_last_payments_url(self):
        begin_date = self.doc.xpath('//input[@id="paiements_1dateDebut"]/@data-mindate')[0]
        end_date = self.doc.xpath('//input[@id="paiements_1dateFin"]/@data-maxdate')[0]
        url = ('/PortailAS/paiements.do?actionEvt=afficherPaiementsComplementaires&DateDebut='
               + begin_date + '&DateFin=' + end_date +
               '&Beneficiaire=tout_selectionner&afficherReleves=false&afficherIJ=false&afficherInva=false'
               '&afficherRentes=false&afficherRS=false&indexPaiement=&idNotif=')
        return url


class LastPaymentsPage(LoggedPage, AmeliBasePage):
    def iter_last_payments(self):
        elts = self.doc.xpath('//li[@class="rowitem remboursement"]')
        for elt in elts:
            items = Regexp(CleanText('./@onclick'), r".*ajaxCallRemoteChargerDetailPaiement \('(\w+={0,2})', '(\w+)', '(\d+)', '(\d+)'\).*", '\\1,\\2,\\3,\\4')(elt).split(',')
            yield "/PortailAS/paiements.do?actionEvt=chargerDetailPaiements&idPaiement=" + items[0] + "&naturePaiement=" + items[1] + "&indexGroupe=" + items[2] + "&indexPaiement=" + items[3]

    def iter_documents(self, sub):
        elts = self.doc.xpath('//li[@class="rowdate"]')
        for elt in elts:
            try:
                elt.xpath('.//a[contains(@id,"lienPDFReleve")]')[0]
            except IndexError:
                continue
            date_str = elt.xpath('.//span[contains(@id,"moisEnCours")]')[0].text
            month_str = date_str.split()[0]
            date = datetime.strptime(re.sub(month_str, str(FRENCH_MONTHS.index(month_str) + 1), date_str), "%m %Y").date()
            bil = Bill()
            bil.id = sub._id + "." + date.strftime("%Y%m")
            bil.date = date
            bil.format = 'pdf'
            bil.type = DocumentTypes.BILL
            bil.label = date.strftime("%Y%m%d")
            bil.url = '/PortailAS/PDFServletReleveMensuel.dopdf?PDF.moisRecherche=' + date.strftime("%m%Y")
            yield bil

    def get_document(self, bill):
        self.location(bill.url, params=bill._args)


class PaymentDetailsPage(AmeliBasePage):
    def iter_payment_details(self, sub):
        id_str = self.doc.xpath('//div[@class="entete container"]/h2')[0].text.strip()
        m = re.match(r'.*le (.*) pour un montant de.*', id_str)
        if m:
            blocs_benes = self.doc.xpath('//span[contains(@id,"nomBeneficiaire")]')
            blocs_prestas = self.doc.xpath('//table[@id="tableauPrestation"]')
            i = 0
            last_bloc = len(blocs_benes)
            for i in range(0, last_bloc):
                bene = blocs_benes[i].text
                id_str = m.group(1)
                id_date = datetime.strptime(id_str, '%d/%m/%Y').date()
                id = sub._id + "." + datetime.strftime(id_date, "%Y%m%d")
                table = blocs_prestas[i].xpath('.//tr')
                line = 1
                last_date = None
                for tr in table:
                    tds = tr.xpath('.//td')
                    if len(tds) == 0:
                        continue

                    det = Detail()

                    # TO TEST : Indemnités journalières : Pas pu tester de cas de figure similaire dans la nouvelle mouture du site
                    if len(tds) == 4:
                        date_str = Regexp(pattern=r'.*<br/>(\d+/\d+/\d+)\).*').filter(tds[0].text)
                        det.id = id + "." + str(line)
                        det.label = tds[0].xpath('.//span')[0].text.strip()

                        jours = tds[1].text
                        if jours is None:
                            jours = '0'

                        montant = tds[2].text
                        if montant is None:
                            montant = '0'

                        price = tds[3].text
                        if price is None:
                            price = '0'

                        if date_str is None or date_str == '':
                            det.infos = ''
                            det.datetime = last_date
                        else:
                            det.infos = date_str + ' (' + re.sub(r'[^\d,-]+', '', jours) + 'j) * ' + re.sub(r'[^\d,-]+', '', montant) + '€'
                            det.datetime = datetime.strptime(date_str.split(' ')[3], '%d/%m/%Y').date()
                            last_date = det.datetime
                        det.price = Decimal(re.sub(r'[^\d,-]+', '', price).replace(',', '.'))

                    if len(tds) == 5:
                        date_str = Regexp(pattern=r'\w*(\d{2})/(\d{2})/(\d{4}).*', template='\\1/\\2/\\3', default="").filter("".join(tds[0].itertext()))
                        det.id = id + "." + str(line)
                        det.label = bene + ' - ' + tds[0].xpath('.//span')[0].text.strip()

                        paye = tds[1].text
                        if paye is None:
                            paye = '0'

                        base = tds[2].text
                        if base is None:
                            base = '0'

                        tdtaux = tds[3].xpath('.//span')[0].text
                        if tdtaux is None:
                            taux = '0'
                        else:
                            taux = tdtaux.strip()

                        tdprice = tds[4].xpath('.//span')[0].text
                        if tdprice is None:
                            price = '0'
                        else:
                            price = tdprice.strip()

                        if date_str is None or date_str == '':
                            det.infos = ''
                            det.datetime = last_date
                        else:
                            det.infos = ' Payé ' + re.sub(r'[^\d,-]+', '', paye) + '€ / Base ' + re.sub(r'[^\d,-]+', '', base) + '€ / Taux ' + re.sub(r'[^\d,-]+', '', taux) + '%'
                            det.datetime = datetime.strptime(date_str, '%d/%m/%Y').date()
                            last_date = det.datetime
                        det.price = Decimal(re.sub(r'[^\d,-]+', '', price).replace(',', '.'))
                    line = line + 1
                    yield det


class Raw(LoggedPage, RawPage):
    pass


class UnavailablePage(HTMLPage):
    def on_load(self):
        raise BrowserUnavailable(CleanText('//span[@class="texte-indispo"]')(self.doc))
