# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

from __future__ import unicode_literals

import datetime
import re

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Investment, Loan
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Person, ProfileMissing
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.tools.compat import urlparse, parse_qsl, urlunparse, urlencode, unicode
from weboob.browser.elements import DictElement, ItemElement, TableElement, method, ListElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Regexp, RegexpError, Currency, Eval, Field, Format, Date,
)
from weboob.browser.filters.html import Link, TableCell
from weboob.browser.pages import HTMLPage, XMLPage, JsonPage, LoggedPage, pagination
from weboob.exceptions import BrowserUnavailable, ActionNeeded

from .base import BasePage


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class AccountsMainPage(LoggedPage, HTMLPage):
    def is_old_website(self):
        return Link('//a[contains(text(), "Afficher la nouvelle consultation")]', default=None)(self.doc)


class AccountDetailsPage(LoggedPage, HTMLPage):
    pass


class AccountsPage(LoggedPage, JsonPage):
    @method
    class iter_accounts(DictElement):
        item_xpath = 'donnees'

        class item(ItemElement):
            klass = Account

            # There are more account type to find
            TYPES = {
                'COMPTE_COURANT': Account.TYPE_CHECKING,
                'PEL': Account.TYPE_SAVINGS,
                'LDD': Account.TYPE_SAVINGS,
                'LIVRETA': Account.TYPE_SAVINGS,
                'LIVRET_JEUNE': Account.TYPE_SAVINGS,
                'COMPTE_SUR_LIVRET': Account.TYPE_SAVINGS,
                'BANQUE_FRANCAISE_MUTUALISEE': Account.TYPE_SAVINGS,
                'PRET_GENERAL': Account.TYPE_LOAN,
                'PRET_PERSONNEL_MUTUALISE': Account.TYPE_LOAN,
                'COMPTE_TITRE_GENERAL': Account.TYPE_MARKET,
                'PEA_ESPECES': Account.TYPE_PEA,
                'PEA_PME_ESPECES': Account.TYPE_PEA,
                'COMPTE_TITRE_PEA': Account.TYPE_PEA,
                'COMPTE_TITRE_PEA_PME': Account.TYPE_PEA,
                'VIE_FEDER': Account.TYPE_LIFE_INSURANCE,
                'ASSURANCE_VIE_GENERALE': Account.TYPE_LIFE_INSURANCE,
                'AVANCE_PATRIMOINE': Account.TYPE_REVOLVING_CREDIT,
            }

            obj_id = obj_number = CleanText(Dict('numeroCompteFormate'), replace=[(' ', '')])
            obj_label = Dict('labelToDisplay')
            obj_balance = CleanDecimal(Dict('soldes/soldeTotal'))
            obj_coming = CleanDecimal(Dict('soldes/soldeEnCours'))
            obj_currency = Currency(Dict('soldes/devise'))
            obj__cards = Dict('cartes', default=[])

            def obj_type(self):
                return self.TYPES.get(Dict('produit')(self), Account.TYPE_UNKNOWN)

            # Useful for navigation
            obj__internal_id = Dict('idTechnique')
            obj__prestation_id = Dict('id')

            def obj__loan_type(self):
                if Field('type')(self) == Account.TYPE_LOAN:
                    return Dict('codeFamille')(self)
                return None


class LoansPage(LoggedPage, JsonPage):
    def on_load(self):
        if 'action' in self.doc['commun'] and self.doc['commun']['action'] == 'BLOCAGE':
            raise ActionNeeded()
        assert self.doc['commun']['statut'] != 'nok'

    def get_loan_account(self, account):
        assert account._prestation_id in Dict('donnees/tabIdAllPrestations')(self.doc), \
            'Loan with prestation id %s should be on this page ...' % account._prestation_id

        for acc in Dict('donnees/tabPrestations')(self.doc):
            if CleanText(Dict('idPrestation'))(acc) == account._prestation_id:
                loan = Loan()
                loan.id = loan.number = account.id
                loan.label = account.label
                loan.type = account.type

                loan.currency = Currency(Dict('capitalRestantDu/devise'))(acc)
                loan.balance = Eval(lambda x: x / 100, CleanDecimal(Dict('capitalRestantDu/valeur')))(acc)
                loan.coming = account.coming

                loan.total_amount = Eval(lambda x: x / 100, CleanDecimal(Dict('montantPret/valeur')))(acc)
                loan.next_payment_amount = Eval(lambda x: x / 100, CleanDecimal(Dict('montantEcheance/valeur')))(acc)

                loan.duration = Dict('dureeNbMois')(acc)
                loan.maturity_date = datetime.datetime.strptime(Dict('dateFin')(acc), '%Y%m%d')

                loan._internal_id = account._internal_id
                loan._prestation_id = account._prestation_id
                return loan


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.*? (?P<dd>\d{2})\/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})\/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})\/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})\/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})\/(?P<text>.*?)\/?(-[\d,]+)?$'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<category>(COTISATION|PRELEVEMENT|TELEREGLEMENT|TIP)) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^(\d+ )?VIR (PERM )?POUR: (.*?) (REF: \d+ )?MOTIF: (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<category>VIR(EMEN)?T? \w+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(CHEQUE) (?P<text>.*)'),     FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^(FRAIS) (?P<text>.*)'),      FrenchTransaction.TYPE_BANK),
                (re.compile(r'^(?P<category>ECHEANCEPRET)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(r'^(?P<category>REMISE CHEQUES)(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^CARTE RETRAIT (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^TOTAL DES FACTURES (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^DEBIT MENSUEL CARTE (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile(r'^CREDIT MENSUEL CARTE (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD_SUMMARY),
               ]


class HistoryPage(LoggedPage, JsonPage):
    @pagination
    @method
    class iter_history(DictElement):
        def next_page(self):
            conditions = (
                not Dict('donnees/listeOperations')(self),
                not Dict('donnees/recapitulatifCompte/chargerPlusOperations')(self)
            )

            if any(conditions):
                return

            if '&an200_operationsSupplementaires=true' in self.page.url:
                return self.page.url
            return self.page.url + '&an200_operationsSupplementaires=true'

        item_xpath = 'donnees/listeOperations'

        class item(ItemElement):
            def condition(self):
                return Dict('statutOperation')(self) == 'COMPTABILISE'

            klass = Transaction

            # not 'idOpe' means that it's a comming transaction
            def obj_id(self):
                if Dict('idOpe')(self):
                    return Regexp(CleanText(Dict('idOpe')), r'(\d+)/')(self)

            def obj_rdate(self):
                if Dict('dateChargement')(self):
                    return Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000),Dict('dateChargement'))(self)

            obj_date = Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000), Dict('dateOpe'))
            obj_amount = CleanDecimal(Dict('mnt'))
            obj_raw = Dict('libOpe')


    @method
    class iter_pea_history(DictElement):
        item_xpath = 'donnees/listeOperations'

        class item(ItemElement):
            klass = Transaction

            obj_date = Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000), Dict('dateOpe'))
            obj_amount = CleanDecimal(Dict('mnt'))
            obj_raw = Dict('libOpe')


    @method
    class iter_coming(DictElement):
        item_xpath = 'donnees/listeOperations'

        class item(ItemElement):
            def condition(self):
                return Dict('statutOperation')(self) != 'COMPTABILISE' and not Dict('idOpe')(self)

            klass = Transaction

            obj_rdate = Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000), Dict('dateOpe'))
            # there is no 'dateChargement' for coming transaction
            obj_date = Eval(lambda t: datetime.date.fromtimestamp(int(t)/1000), Dict('dateOpe'))
            obj_amount = CleanDecimal(Dict('mnt'))
            obj_raw = Dict('libOpe')


class ComingPage(LoggedPage, XMLPage):
    def get_account_comings(self):
        account_comings = {}
        for el in self.doc.xpath('//EnCours'):
            prestation_id = CleanText('./@id')(el).replace('montantEncours', '')
            coming_amount = MyDecimal(Regexp(CleanText('.'), r'(.*)&nbsp;'))(el)
            account_comings[prestation_id] = coming_amount
        return account_comings


class CardListPage(LoggedPage, HTMLPage):
    def get_card_history_link(self, account):
        for el in self.doc.xpath('//a[contains(@href, "detailCARTE")]'):
            if CleanText('.', replace=[(' ', '')])(el) == account.number:
                return Link('.')(el)

    def get_card_transactions_link(self):
        if 'Le détail de cette carte ne vous est pas accessible' in CleanText('//div')(self.doc):
            return NotAvailable
        return CleanText('//div[@id="operationsListView"]//select/option[@selected="selected"]/@value')(self.doc)


class CardHistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_card_history(ListElement):
        item_xpath = '//tr'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText('.//td[@headers="Libelle"]/span')

            def obj_date(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return Date(Regexp(CleanText('.//td[@headers="Date"]'), r'\d{2}\/\d{2}\/\d{4}'))(self)
                else:
                    return NotAvailable

            def obj_amount(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return MyDecimal(CleanText('.//td[contains(@headers, "Debit")]'))(self)
                else:
                    return abs(MyDecimal(CleanText('.//td[contains(@headers, "Debit")]'))(self))

            def obj_raw(self):
                if not 'TOTAL DES FACTURES' in Field('label')(self):
                    return Transaction.Raw(CleanText('.//td[@headers="Libelle"]/span'))(self)
                return NotAvailable


class MarketPage(LoggedPage, HTMLPage):
    # TODO
    pass


class AdvisorPage(LoggedPage, XMLPage):
    ENCODING = 'ISO-8859-15'

    def get_advisor(self):
        advisor = Advisor()
        advisor.name = Format('%s %s', CleanText('//NomConseiller'), CleanText('//PrenomConseiller'))(self.doc)
        advisor.phone = CleanText('//NumeroTelephone')(self.doc)
        advisor.agency = CleanText('//liloes')(self.doc)
        advisor.address = Format('%s %s %s',
                                 CleanText('//ruadre'),
                                 CleanText('//cdpost'),
                                 CleanText('//loadre')
                                 )(self.doc)
        advisor.email = CleanText('//Email')(self.doc)
        advisor.role = "wealth" if "patrimoine" in CleanText('//LibelleNatureConseiller')(self.doc).lower() else "bank"
        yield advisor


class HTMLProfilePage(LoggedPage, HTMLPage):
    def on_load(self):
        msg = CleanText('//div[@id="connecteur_partenaire"]', default='')(self.doc)
        service_unavailable_msg = CleanText('//span[@class="error_msg" and contains(text(), "indisponible")]')(self.doc)

        if 'Erreur' in msg:
            raise BrowserUnavailable(msg)
        if service_unavailable_msg:
            raise ProfileMissing(service_unavailable_msg)

    def get_profile(self):
        profile = Person()
        profile.name = Regexp(CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "PROFIL DE")]'), r'PROFIL DE (.*)')(self.doc)
        profile.address = CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[3]/td[2]')(self.doc)
        profile.address += ' ' + CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[5]/td[2]')(self.doc)
        profile.address += ' ' + CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[6]/td[2]')(self.doc)
        profile.country = CleanText('//div[@id="dcr-conteneur"]//div[contains(text(), "ADRESSE")]/following::table//tr[7]/td[2]')(self.doc)

        return profile


class XMLProfilePage(LoggedPage, XMLPage):
    def get_email(self):
        return CleanText('//AdresseEmailExterne')(self.doc)


# TODO: check if it work
class NotTransferBasePage(BasePage):
    def is_transfer_here(self):
        # check that we aren't on transfer or add recipient page
        return bool(CleanText('//h1[contains(text(), "Effectuer un virement")]')(self.doc)) or \
               bool(CleanText(u'//h3[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
               bool(CleanText(u'//h1[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
               bool(CleanText(u'//h3[contains(text(), "Veuillez vérifier les informations du compte à ajouter")]')(self.doc)) or \
               bool(Link('//a[contains(@href, "per_cptBen_ajouterFrBic")]', default=NotAvailable)(self.doc))


class Invest(object):
    def create_investment(self, cells):
        inv = Investment()
        inv.quantity = MyDecimal('.')(cells[self.COL_QUANTITY])
        inv.unitvalue = MyDecimal('.')(cells[self.COL_UNITVALUE])
        inv.unitprice = NotAvailable
        inv.valuation = MyDecimal('.')(cells[self.COL_VALUATION])
        inv.diff = NotAvailable

        link = cells[self.COL_LABEL].xpath('a[contains(@href, "CDCVAL=")]')[0]
        m = re.search('CDCVAL=([^&]+)', link.attrib['href'])
        if m:
            inv.code = m.group(1)
        else:
            inv.code = NotAvailable
        return inv


class Market(LoggedPage, BasePage, Invest):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITPRICE = 2
    COL_VALUATION = 3
    COL_DIFF = 4

    def get_balance(self, account_type):
        return CleanDecimal('//form[@id="listeCTForm"]/table//tr[td[5]]/td[@class="TabCelRight"][1]', replace_dots=True, default=None)(self.doc)

    def get_not_rounded_valuations(self):
        def prepare_url(url, fields):
            components = urlparse(url)
            query_pairs = [(f, v) for (f, v) in parse_qsl(components.query) if f not in fields]

            for (field, value) in fields.items():
                query_pairs.append((field, value))

            new_query_str = urlencode(query_pairs)

            new_components = (
                components.scheme,
                components.netloc,
                components.path,
                components.params,
                new_query_str,
                components.fragment
            )

            return urlunparse(new_components)

        not_rounded_valuations = {}
        pages = []

        try:
            for i in range(1, CleanDecimal(Regexp(CleanText(u'(//table[form[contains(@name, "detailCompteTitresForm")]]//tr[1])[1]/td[3]/text()'), r'\/(.*)'))(self.doc) + 1):
                pages.append(self.browser.open(prepare_url(self.browser.url, {'action': '11', 'idCptSelect': '1', 'numPage': i})).page)
        except RegexpError: # no multiple page
            pages.append(self)

        for page in pages:
            for inv in page.doc.xpath(u'//table[contains(., "Détail du compte")]//tr[2]//table/tr[position() > 1]'):
                if len(inv.xpath('.//td')) > 2:
                    amt = CleanText('.//td[7]/text()')(inv)
                    if amt == 'Indisponible':
                        continue
                    not_rounded_valuations[CleanText('.//td[1]/a/text()')(inv)] = CleanDecimal('.//td[7]/text()', replace_dots=True)(inv)

        return not_rounded_valuations

    def iter_investment(self):
        not_rounded_valuations = self.get_not_rounded_valuations()

        doc = self.browser.open('/brs/fisc/fisca10a.html').page.doc
        num_page = None

        try:
            num_page = int(CleanText('.')(doc.xpath(u'.//tr[contains(td[1], "Relevé des plus ou moins values latentes")]/td[2]')[0]).split('/')[1])
        except IndexError:
            pass

        docs = [doc]

        if num_page:
            for n in range(2, num_page + 1):
                docs.append(self.browser.open('%s%s' % ('/brs/fisc/fisca10a.html?action=12&numPage=', str(n))).page.doc)

        for doc in docs:
            # There are two different tables possible depending on the market account type.
            is_detailed = bool(doc.xpath(u'//span[contains(text(), "Années d\'acquisition")]'))
            tr_xpath = '//tr[@height and td[@colspan="6"]]' if is_detailed else '//tr[count(td)>5]'
            for tr in doc.xpath(tr_xpath):
                cells = tr.findall('td')

                inv = Investment()

                title_split = cells[self.COL_LABEL].xpath('.//span')[0].attrib['title'].split(' - ')
                inv.label = unicode(title_split[0])

                for code in title_split[1:]:
                    if is_isin_valid(code):
                        inv.code = unicode(code)
                        inv.code_type = Investment.CODE_TYPE_ISIN
                        break
                    else:
                        inv.code = NotAvailable
                        inv.code_type = NotAvailable

                if is_detailed:
                    inv.quantity = MyDecimal('.')(tr.xpath('./following-sibling::tr/td[2]')[0])
                    inv.unitprice = MyDecimal('.', replace_dots=True)(tr.xpath('./following-sibling::tr/td[3]')[1])
                    inv.unitvalue = MyDecimal('.', replace_dots=True)(tr.xpath('./following-sibling::tr/td[3]')[0])

                    try: # try to get not rounded value
                        inv.valuation = not_rounded_valuations[inv.label]
                    except KeyError: # ok.. take it from the page
                        inv.valuation = MyDecimal('.')(tr.xpath('./following-sibling::tr/td[4]')[0])

                    inv.diff = MyDecimal('.')(tr.xpath('./following-sibling::tr/td[5]')[0]) or \
                               MyDecimal('.')(tr.xpath('./following-sibling::tr/td[6]')[0])
                else:
                    inv.quantity = MyDecimal('.')(cells[self.COL_QUANTITY])
                    inv.diff = MyDecimal('.')(cells[self.COL_DIFF])
                    inv.unitprice = MyDecimal('.')(cells[self.COL_UNITPRICE].xpath('.//tr[1]/td[2]')[0])
                    inv.unitvalue = MyDecimal('.')(cells[self.COL_VALUATION].xpath('.//tr[1]/td[2]')[0])
                    inv.valuation = MyDecimal('.')(cells[self.COL_VALUATION].xpath('.//tr[2]/td[2]')[0])

                yield inv


class LifeInsurance(LoggedPage, BasePage):
    def get_error(self):
        try:
            return self.doc.xpath("//div[@class='net2g_asv_error_full_page']")[0].text.strip()
        except IndexError:
            return super(LifeInsurance, self).get_error()

    def has_link(self):
        return Link('//a[@href="asvcns20a.html"]', default=NotAvailable)(self.doc)

    def get_error_msg(self):
        # to check page errors
        return CleanText('//span[@class="error_msg"]')(self.doc)


class LifeInsuranceInvest(LifeInsurance, Invest):
    COL_LABEL = 0
    COL_QUANTITY = 1
    COL_UNITVALUE = 2
    COL_VALUATION = 3

    def iter_investment(self):
        for tr in self.doc.xpath("//table/tbody/tr[starts-with(@class, 'net2g_asv_tableau_ligne_')]"):
            cells = tr.findall('td')
            inv = self.create_investment(cells)
            inv.label = unicode(cells[self.COL_LABEL].xpath('a/span')[0].text.strip())
            inv.description = unicode(cells[self.COL_LABEL].xpath('a//div/b[last()]')[0].tail)

            yield inv

    def get_pages(self):
        # "pages" value is for example "1/5"
        pages = CleanText('//div[@class="net2g_asv_tableau_pager"]')(self.doc)
        return re.search(r'/(.*)', pages).group(1) if pages else None


class LifeInsuranceInvest2(LifeInsuranceInvest):
    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tbody/tr[starts-with(@class, "net2g_asv_tableau_ligne_")]'
        head_xpath = '//table/thead/tr/td'

        col_label = u'Support'
        col_valuation = u'Montant'

        class item(ItemElement):
            klass = Investment
            obj_label = CleanText(TableCell('label'))
            obj_valuation = MyDecimal(TableCell('valuation'))


class LifeInsuranceHistory(LifeInsurance):
    COL_DATE = 0
    COL_LABEL = 1
    COL_AMOUNT = 2
    COL_STATUS = 3

    def iter_transactions(self):
        for tr in self.doc.xpath("//table/tbody/tr[starts-with(@class, 'net2g_asv_tableau_ligne_')]"):
            cells = tr.findall('td')

            link = cells[self.COL_LABEL].xpath('a')[0]
            # javascript:detailOperation('operationForm', '2');
            m = re.search(", '([0-9]+)'", link.attrib['href'])
            if m:
                id_trans = m.group(1)
            else:
                id_trans = ''

            trans = Transaction()
            trans._temp_id = id_trans
            trans.parse(raw=link.attrib['title'], date=cells[self.COL_DATE].text)
            trans.set_amount(cells[self.COL_AMOUNT].text)
            # search for 'Réalisé'
            trans._coming = 'alis' not in cells[self.COL_STATUS].text.strip()

            if not self.set_date(trans):
                continue

            if u'Annulé' in cells[self.COL_STATUS].text.strip():
                continue

            yield trans

    def set_date(self, trans):
        """fetch date and vdate from another page"""
        # go to the page containing the dates
        form = self.get_form(id='operationForm')
        form['a100_asv_action'] = 'detail'
        form['a100_asv_indexOp'] = trans._temp_id
        form.url = '/asv/AVI/asvcns21c.html'

        # but the page sometimes fail
        for i in range(3, -1, -1):
            page = form.submit().page
            doc = page.doc
            if not page.get_error():
                break
            self.logger.warning('Life insurance history error (%s), retrying %d more times', page.get_error(), i)
        else:
            self.logger.warning('Life insurance history error (%s), failed', page.get_error())
            return False

        # process the data
        date_xpath = '//td[@class="net2g_asv_suiviOperation_element1"]/following-sibling::td'
        vdate_xpath = '//td[@class="net2g_asv_tableau_cell_date"]'

        date = CleanText(date_xpath)(doc)
        if u"Rejet d'intégration" in date:
            return False

        trans.date = self.parse_date(doc, trans, date_xpath, 1)
        trans.rdate = trans.date
        trans.vdate = self.parse_date(doc, trans, vdate_xpath, 0)
        return True

    @staticmethod
    def parse_date(doc, trans, xpath, index):
        elem = doc.xpath(xpath)[index]
        if elem.text:
            return trans.parse_date(elem.text.strip())
        else:
            return NotAvailable


class UnavailableServicePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//div[contains(@class, "erreur_404_content")]'):
            raise BrowserUnavailable()
