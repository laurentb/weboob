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
from lxml.etree import XML
from lxml.html import fromstring
from decimal import Decimal, InvalidOperation
import re

from weboob.capabilities.base import empty, NotAvailable, find_object
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Person, ProfileMissing
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.tools.compat import parse_qs, urlparse, parse_qsl, urlunparse, urlencode, unicode
from weboob.tools.date import parse_date as parse_d
from weboob.browser.elements import DictElement, ItemElement, TableElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, RegexpError
from weboob.browser.filters.html import Link, TableCell, Attr
from weboob.browser.pages import HTMLPage, XMLPage, JsonPage, LoggedPage
from weboob.exceptions import NoAccountsException, BrowserUnavailable, ActionNeeded

from .base import BasePage

def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class NotTransferBasePage(BasePage):
    def is_transfer_here(self):
        # check that we aren't on transfer or add recipient page
        return bool(CleanText('//h1[contains(text(), "Effectuer un virement")]')(self.doc)) or \
               bool(CleanText(u'//h3[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
               bool(CleanText(u'//h1[contains(text(), "Ajouter un compte bénéficiaire de virement")]')(self.doc)) or \
               bool(CleanText(u'//h3[contains(text(), "Veuillez vérifier les informations du compte à ajouter")]')(self.doc)) or \
               bool(Link('//a[contains(@href, "per_cptBen_ajouterFrBic")]', default=NotAvailable)(self.doc))


class AccountsList(LoggedPage, BasePage):
    LINKID_REGEXP = re.compile(".*ch4=(\w+).*")

    TYPES = {u'Compte Bancaire':     Account.TYPE_CHECKING,
             u'Compte Epargne':      Account.TYPE_SAVINGS,
             u'Compte Sur Livret':   Account.TYPE_SAVINGS,
             u'Compte Titres':       Account.TYPE_MARKET,
             'Déclic Tempo':         Account.TYPE_MARKET,
             u'Compte Alterna':      Account.TYPE_LOAN,
             u'Crédit':              Account.TYPE_LOAN,
             u'Ldd':                 Account.TYPE_SAVINGS,
             u'Livret':              Account.TYPE_SAVINGS,
             u'PEA':                 Account.TYPE_PEA,
             u'PEL':                 Account.TYPE_SAVINGS,
             u'Plan Epargne':        Account.TYPE_SAVINGS,
             u'Prêt':                Account.TYPE_LOAN,
             'Avance Patrimoniale':  Account.TYPE_LOAN,
            }

    def get_coming_url(self):
        for script in self.doc.xpath('//script'):
            s_content = CleanText('.')(script)
            if "var url_encours" in s_content:
                break
        return re.search(r'url_encours=\"(.+)\"; ', s_content).group(1)

    def get_list(self):
        err = CleanText('//span[@class="error_msg"]', default='')(self.doc)
        if err == 'Vous ne disposez pas de compte consultable.':
            raise NoAccountsException()

        def check_valid_url(url):
            pattern = ['/restitution/cns_detailAVPAT.html',
                       '/restitution/cns_detailAlterna.html',
                      ]

            for p in pattern:
                if url.startswith(p):
                    return False
            return True

        accounts_list = []

        for tr in self.doc.getiterator('tr'):
            if 'LGNTableRow' not in tr.attrib.get('class', '').split():
                continue

            account = Account()
            for td in tr.getiterator('td'):
                if td.attrib.get('headers', '') == 'TypeCompte':
                    a = td.find('a')
                    if a is None:
                        break
                    account.label = CleanText('.')(a)
                    account._link_id = a.get('href', '')
                    for pattern, actype in self.TYPES.items():
                        if account.label.startswith(pattern):
                            account.type = actype
                            break
                    else:
                        if account._link_id.startswith('/asv/asvcns10.html'):
                            account.type = Account.TYPE_LIFE_INSURANCE
                    # Website crashes when going on theses URLs
                    if not check_valid_url(account._link_id):
                        account._link_id = None

                elif td.attrib.get('headers', '') == 'NumeroCompte':
                    account.id = CleanText(u'.', replace=[(' ', '')])(td)

                elif td.attrib.get('headers', '') == 'Libelle':
                    text = CleanText('.')(td)
                    if text != '':
                        account.label = text

                elif td.attrib.get('headers', '') == 'Solde':
                    div = td.xpath('./div[@class="Solde"]')
                    if len(div) > 0:
                        balance = CleanText('.')(div[0])
                        if len(balance) > 0 and balance not in ('ANNULEE', 'OPPOSITION'):
                            try:
                                account.balance = Decimal(FrenchTransaction.clean_amount(balance))
                            except InvalidOperation:
                                self.logger.error('Unable to parse balance %r' % balance)
                                continue
                            account.currency = account.get_currency(balance)
                        else:
                            account.balance = NotAvailable
            if not account.label or empty(account.balance):
                continue

            if account._link_id and 'CARTE_' in account._link_id:
                account.type = account.TYPE_CARD
                page = self.browser.open(account._link_id).page

                # Layout with several cards
                line = CleanText('//table//div[contains(text(), "Liste des cartes")]', replace=[(' ', '')])(page.doc)
                m = re.search(r'(\d+)', line)
                if m:
                    parent_id = m.group()
                else:
                    parent_id = CleanText('//div[contains(text(), "Numéro de compte débité")]/following::div[1]', replace=[(' ', '')])(page.doc)
                account.parent = find_object(accounts_list, id=parent_id)

            if account.type == Account.TYPE_UNKNOWN:
                self.logger.debug('Unknown account type: %s', account.label)

            accounts_list.append(account)

        return accounts_list


class ComingPage(LoggedPage, XMLPage):
    def set_coming(self, accounts_list):
        for a in accounts_list:
            a.coming = CleanDecimal('//EnCours[contains(@id, "%s")]' % a.id, replace_dots=True, default=NotAvailable)(self.doc)


class IbanPage(LoggedPage, NotTransferBasePage):
    def is_here(self):
        if self.is_transfer_here():
            return False
        return 'Imprimer ce RIB' in Attr('.//img', 'alt')(self.doc) or \
               CleanText('//span[@class="error_msg"]')(self.doc)


    def get_iban(self):
        if not CleanText('//span[@class="error_msg"]')(self.doc):
            return CleanText().filter(self.doc.xpath("//font[contains(text(),'IBAN')]/b[1]")[0]).replace(' ', '')


class CardsList(LoggedPage, BasePage):
    def iter_cards(self):
        for tr in self.doc.getiterator('tr'):
            tds = tr.findall('td')
            if len(tds) < 4 or tds[0].attrib.get('class', '') != 'tableauIFrameEcriture1':
                continue

            yield tr.xpath('.//a')[0].attrib['href']


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^CARTE \w+ RETRAIT DAB.*? (?P<dd>\d{2})/(?P<mm>\d{2})( (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? RETRAIT DAB (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CARTE \w+ REMBT (?P<dd>\d{2})/(?P<mm>\d{2})( A (?P<HH>\d+)H(?P<MM>\d+))? (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<category>CARTE) \w+ (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<dd>\d{2})(?P<mm>\d{2})/(?P<text>.*?)/?(-[\d,]+)?$'),
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


class AccountHistory(LoggedPage, NotTransferBasePage):
    def is_here(self):
        return not self.is_transfer_here()

    def on_load(self):
        super(AccountHistory, self).on_load()

        msg = CleanText('//span[@class="error_msg"]', default='')(self.doc)
        if 'Le service est momentanément indisponible' in msg:
            raise BrowserUnavailable(msg)

    debit_date = None

    def get_part_url(self):
        for script in self.doc.getiterator('script'):
            if script.text is None:
                continue

            m = re.search('var listeEcrCavXmlUrl="(.*)";', script.text)
            if m:
                return m.group(1)

        return None

    def iter_transactions(self):
        url = self.get_part_url()
        if url is None:
            # There are no transactions in this kind of account
            return

        is_deferred_card = bool(self.doc.xpath(u'//div[contains(text(), "Différé")]'))
        has_summary = False

        if is_deferred_card:
            coming_debit_date = None
            # get coming debit date for deferred_card
            date_string = Regexp(CleanText(u'//option[contains(text(), "détail des factures à débiter le")]'),
                                r'(\d{2}/\d{2}/\d{4})',
                                default=NotAvailable)(self.doc)
            if date_string:
                coming_debit_date = parse_d(date_string)

        while True:
            d = XML(self.browser.open(url).content)
            el = d.xpath('//dataBody')
            if not el:
                return

            el = el[0]
            s = unicode(el.text).encode('iso-8859-1')
            doc = fromstring(s)

            for tr in self._iter_transactions(doc):
                if tr.type == Transaction.TYPE_CARD_SUMMARY:
                    has_summary = True
                if is_deferred_card and tr.type is Transaction.TYPE_CARD:
                    tr.type = Transaction.TYPE_DEFERRED_CARD
                    if not has_summary:
                        if coming_debit_date:
                            tr.date = coming_debit_date
                        tr._coming = True
                yield tr

            el = d.xpath('//dataHeader')[0]
            if int(el.find('suite').text) != 1:
                return

            url = urlparse(url)
            p = parse_qs(url.query)

            args = {}
            args['n10_nrowcolor'] = 0
            args['operationNumberPG'] = el.find('operationNumber').text
            args['operationTypePG'] = el.find('operationType').text
            args['pageNumberPG'] = el.find('pageNumber').text
            args['idecrit'] = el.find('idecrit').text or ''
            args['sign'] = p['sign'][0]
            args['src'] = p['src'][0]

            url = '%s?%s' % (url.path, urlencode(args))

    def _iter_transactions(self, doc):
        t = None
        for i, tr in enumerate(doc.xpath('//tr')):
            try:
                raw = tr.attrib['title'].strip()
            except KeyError:
                raw = CleanText('./td[@headers="Libelle"]//text()')(tr)

            date = CleanText('./td[@headers="Date"]')(tr)
            if date == '':
                m = re.search(r'(\d+)/(\d+)', raw)
                if not m:
                    continue

                old_debit_date = self.debit_date
                self.debit_date = t.date if t else datetime.date.today()
                self.debit_date = self.debit_date.replace(day=int(m.group(1)), month=int(m.group(2)))

                # Need to do it when years/date overlap, causing the previous `.replace()` to
                # set the date at the end of the next year instead of the current year
                if old_debit_date is None and self.debit_date > datetime.date.today():
                    old_debit_date = self.debit_date

                if old_debit_date is not None:
                    while self.debit_date > old_debit_date:
                        self.debit_date = self.debit_date.replace(year=self.debit_date.year - 1)
                        self.logger.error('adjusting debit date to %s', self.debit_date)

                if not t:
                    continue

            t = Transaction()

            if 'EnTraitement' in tr.get('class', ''):
                t._coming = True
            else:
                t._coming = False

            t.set_amount(*reversed([el.text for el in tr.xpath('./td[@class="right"]')]))
            if date == '':
                # Credit from main account.
                t.amount = -t.amount
                date = self.debit_date
            t.rdate = t.parse_date(date)
            t.parse(raw=raw, date=(self.debit_date or date), vdate=(date or None))

            yield t

    def get_liquidities(self):
        return CleanDecimal('//td[contains(@headers, "solde")]', replace_dots=True)(self.doc)


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


class ListRibPage(LoggedPage, BasePage):
    def get_rib_url(self, account):
        for div in self.doc.xpath('//table//td[@class="fond_cellule"]//div[@class="tableauBodyEcriture1"]//table//tr'):
            if account.id == CleanText().filter(div.xpath('./td[2]//div/div')).replace(' ', ''):
                href = CleanText().filter(div.xpath('./td[4]//a/@href'))
                m = re.search("javascript:windowOpenerRib\('(.*?)'(.*)\)", href)
                if m:
                    return m.group(1)


class AdvisorPage(LoggedPage, BasePage):
    def get_advisor(self):
        fax = CleanText('//div[contains(text(), "Fax")]/following-sibling::div[1]', replace=[(' ', '')])(self.doc)
        agency = CleanText('//div[contains(@class, "agence")]/div[last()]')(self.doc)
        address = CleanText('//div[contains(text(), "Adresse")]/following-sibling::div[1]')(self.doc)
        for div in self.doc.xpath('//div[div[text()="Contacter mon conseiller"]]'):
            a = Advisor()
            a.name = CleanText('./div[2]')(div)
            a.phone = Regexp(CleanText(u'./following-sibling::div[div[contains(text(), "Téléphone")]][1]/div[last()]', replace=[(' ', '')]), '([+\d]+)')(div)
            a.fax = fax
            a.agency = agency
            a.address = address
            a.mobile = a.email = NotAvailable
            a.role = u"wealth" if "patrimoine" in CleanText('./div[1]')(div) else u"bank"
            yield a


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


class LoansPage(LoggedPage, JsonPage):
    def on_load(self):
        if 'action' in self.doc['commun'] and self.doc['commun']['action'] == 'BLOCAGE':
            raise ActionNeeded()
        assert self.doc['commun']['statut'] != 'nok'

    @method
    class iter_accounts(DictElement):
        item_xpath = 'donnees/tabPrestations'

        class item(ItemElement):
            klass = Account

            obj_id = Dict('idPrestation')
            obj_type = Account.TYPE_LOAN
            obj_label = Dict('libelle')
            obj_currency = Dict('capitalRestantDu/devise', default=NotAvailable)
            obj__link_id = None

            def obj_balance(self):
                val = Dict('capitalRestantDu/valeur', default=NotAvailable)(self)
                if val is NotAvailable:
                    return val

                val = Decimal(val)
                point = Decimal(Dict('capitalRestantDu/posDecimale')(self))
                assert point >= 0
                return val.scaleb(-point)

            def validate(self, obj):
                assert obj.id
                assert obj.label
                if obj.balance is NotAvailable:
                    # ... but the account may be in the main AccountsList anyway
                    self.logger.debug('skipping account %r %r due to missing balance', obj.id, obj.label)
                    return False
                return True


class UnavailableServicePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//div[contains(@class, "erreur_404_content")]'):
            raise BrowserUnavailable()


class NewLandingPage(LoggedPage, HTMLPage):
    pass
