# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

from decimal import Decimal, InvalidOperation
import re
from dateutil.relativedelta import relativedelta

from weboob.browser.pages import HTMLPage, FormNotFound, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, SkipItem, method, TableElement
from weboob.browser.filters.standard import Filter, Env, CleanText, CleanDecimal, Field, TableCell, Regexp, Async, AsyncLoad, Date, ColumnNotFound
from weboob.browser.filters.html import Link, Attr
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class RedirectPage(LoggedPage, HTMLPage):
    def on_load(self):
        link = self.doc.xpath('//a[@id="P:F_1.R2:link"]')
        if link:
            self.browser.location(link[0].attrib['href'])


class NewHomePage(LoggedPage, HTMLPage):
    def on_load(self):
        self.browser.is_new_website = True


class LoginPage(HTMLPage):
    REFRESH_MAX = 10.0

    def login(self, login, passwd):
        form = self.get_form(xpath='//form[contains(@name, "ident")]')
        form['_cm_user'] = login
        form['_cm_pwd'] = passwd
        form.submit()

    @property
    def logged(self):
        return self.doc.xpath('//div[@id="e_identification_ok"]')


class LoginErrorPage(HTMLPage):
    pass


class EmptyPage(LoggedPage, HTMLPage):
    REFRESH_MAX = 10.0


class UserSpacePage(LoggedPage, HTMLPage):
    pass


class ChangePasswordPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Please change your password')


class VerifCodePage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Unable to login: website asks a code from a card')


class TransfertPage(LoggedPage, HTMLPage):
    def get_account_index(self, direction, account):
        for div in self.doc.getroot().cssselect(".dw_dli_contents"):
            inp = div.cssselect("input")[0]
            if inp.name != direction:
                continue
            acct = div.cssselect("span.doux")[0].text.replace(" ", "")
            if account.endswith(acct):
                return inp.attrib['value']
        else:
            raise ValueError("account %s not found" % account)

    def get_from_account_index(self, account):
        return self.get_account_index('data_input_indiceCompteADebiter', account)

    def get_to_account_index(self, account):
        return self.get_account_index('data_input_indiceCompteACrediter', account)

    def get_unicode_content(self):
        return self.content.decode(self.detect_encoding())


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {u'C/C':               Account.TYPE_CHECKING,
             u'Livret':            Account.TYPE_SAVINGS,
             u'Nouveau Prêt':      Account.TYPE_LOAN,
             u'Pret':              Account.TYPE_LOAN,
             u'Cic Immo':          Account.TYPE_LOAN,
             u'Passeport Credit':  Account.TYPE_LOAN,
             u'Credit En Reserve': Account.TYPE_LOAN,
             u'Compte Courant':    Account.TYPE_CHECKING,
             u'Cpte Courant':      Account.TYPE_CHECKING,
             u'Compte Cheque':     Account.TYPE_CHECKING,
             u'Start':             Account.TYPE_CHECKING,
             u'Compte Epargne':    Account.TYPE_SAVINGS,
             u'Plan D\'Epargne':   Account.TYPE_SAVINGS,
             u'P.E.A':             Account.TYPE_SAVINGS,
             u'Tonic Croissance':  Account.TYPE_SAVINGS,
             u'Ldd':               Account.TYPE_SAVINGS,
             u'Etalis':            Account.TYPE_SAVINGS,
            }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//tr'
        flush_at_end = True

        class item(ItemElement):
            klass = Account

            def condition(self):
                if len(self.el.xpath('./td')) < 2:
                    return False

                first_td = self.el.xpath('./td')[0]
                return (("i" in first_td.attrib.get('class', '') or "p" in first_td.attrib.get('class', ''))
                        and first_td.find('a') is not None)

            class Label(Filter):
                def filter(self, text):
                    return text.lstrip(' 0123456789').title()

            class Type(Filter):
                def filter(self, label):
                    for pattern, actype in AccountsPage.TYPES.iteritems():
                        if label.startswith(pattern):
                            return actype
                    return Account.TYPE_UNKNOWN

            obj_id = Env('id')
            obj_label = Label(CleanText('./td[1]/a/text() | ./td[1]/a/span[@class and not(contains(@class, "doux"))]'))
            obj_coming = Env('coming')
            obj_balance = Env('balance')
            obj_currency = FrenchTransaction.Currency('./td[2] | ./td[3]')
            obj__link_id = Link('./td[1]/a')
            obj__card_links = []
            obj_type = Type(Field('label'))
            obj__is_inv = False
            obj__is_webid = Env('_is_webid')

            def parse(self, el):
                link = el.xpath('./td[1]/a')[0].get('href', '')
                if 'POR_SyntheseLst' in link:
                    raise SkipItem()

                url = urlparse(link)
                p = parse_qs(url.query)
                if 'rib' not in p and 'webid' not in p:
                    raise SkipItem()

                for td in el.xpath('./td[2] | ./td[3]'):
                    try:
                        balance = CleanDecimal('.', replace_dots=True)(td)
                    except InvalidOperation:
                        continue
                    else:
                        break
                else:
                    raise ParseError('Unable to find balance for account %s' % CleanText('./td[1]/a')(el))

                self.env['_is_webid'] = False
                if self.page.browser.is_new_website:
                    id = CleanText('./td[1]/a/node()[contains(@class, "doux")]', replace=[(' ', '')])(el)
                else:
                    if 'rib' in p:
                        id = p['rib'][0]
                    else:
                        id = p['webid'][0]
                        self.env['_is_webid'] = True

                # Handle cards
                if id in self.parent.objects:
                    account = self.parent.objects[id]
                    if not account.coming:
                        account.coming = Decimal('0.0')
                    account.coming += balance
                    account._card_links.append(link)
                    raise SkipItem()

                self.env['id'] = id

                # Handle real balances
                page = self.page.browser.open(link).page
                coming = page.find_amount(u"Opérations à venir") if page else None
                accounting = page.find_amount(u"Solde comptable") if page else None

                if accounting is not None and accounting + (coming or Decimal('0')) != balance:
                    self.page.logger.warning('%s + %s != %s' % (accounting, coming, balance))

                if accounting is not None:
                    balance = accounting

                self.env['balance'] = balance
                self.env['coming'] = coming or NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^PAIEMENT PSC\s+(?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE \d+ ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE( (?P<text>.*))?$'),  FrenchTransaction.TYPE_CHECK),
                (re.compile('^(F )?COTIS\.? (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(REMISE|REM CHQ) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]

    _is_coming = False


class Pagination(object):
    def next_page(self):
        try:
            form = self.page.get_form('//form[@id="paginationForm"]')
        except FormNotFound:
            return

        text = CleanText.clean(form.el)
        m = re.search(u'(\d+) / (\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return

        form['page'] = str(cur + 1)
        return form.request


class OperationsPage(LoggedPage, HTMLPage):
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[@class="liste"]//thead//tr/th'
        item_xpath = '//table[@class="liste"]//tbody/tr'

        class item(Transaction.TransactionElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 3 and len(self.el.xpath('./td[@class="i g" or @class="p g" or contains(@class, "_c1")]')) > 0

            class OwnRaw(Filter):
                def __call__(self, item):
                    el = TableCell('raw')(item)[0]

                    # Remove hidden parts of labels:
                    # hideifscript: Date de valeur XX/XX/XXXX
                    # fd: Avis d'opéré
                    for sub in el.xpath('.//*[has-class("hideifscript") or has-class("fd")]'):
                        sub.drop_tree()

                    parts = [txt.strip() for txt in el.itertext() if len(txt.strip()) > 0]

                    # To simplify categorization of CB, reverse order of parts to separate
                    # location and institution.
                    if parts[0].startswith('PAIEMENT CB'):
                        parts.reverse()

                    return u' '.join(parts)

            obj_raw = Transaction.Raw(OwnRaw())

    def find_amount(self, title):
        try:
            td = self.doc.xpath(u'//th[contains(text(), "%s")]/../td' % title)[0]
        except IndexError:
            return None
        else:
            return Decimal(FrenchTransaction.clean_amount(td.text))

    def get_coming_link(self):
        try:
            a = self.doc.xpath(u'//a[contains(text(), "Opérations à venir")]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['href']


class ComingPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[@class="liste"]//thead//tr/th/text()'
        item_xpath = '//table[@class="liste"]//tbody/tr'

        col_date = u"Date de l'annonce"

        class item(Transaction.TransactionElement):
            obj__is_coming = True


class CardPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, ListElement):
        class list_cards(ListElement):
            item_xpath = '//table[@class="liste"]/tbody/tr/td/a'

            class item(ItemElement):
                def __iter__(self):
                    card_link = self.el.get('href')
                    history_url = '%s/%s/fr/banque/%s' % (self.page.browser.BASEURL, self.page.browser.currentSubBank, card_link)
                    page = self.page.browser.location(history_url).page

                    for op in page.get_history():
                        yield op

        class list_history(Transaction.TransactionsElement):
            head_xpath = '//table[@class="liste"]//thead/tr/th'
            item_xpath = '//table[@class="liste"]/tbody/tr'
            col_commerce = u'Commerce'
            col_ville = u'Ville'

            def parse(self, el):
                label = CleanText('//div[contains(@class, "lister")]//p[@class="c"]')(el)
                if not label:
                    return
                label = re.findall('(\d+ [^ ]+ \d+)', label)[-1]
                # use the trick of relativedelta to get the last day of month.
                self.env['debit_date'] = (parse_french_date(label) + relativedelta(day=31)).date()

            class item(Transaction.TransactionElement):
                condition = lambda self: len(self.el.xpath('./td')) >= 4

                obj_raw = Transaction.Raw(Env('raw'))
                obj_type = Transaction.TYPE_CARD
                obj_date = Env('debit_date')
                obj_rdate = Transaction.Date(TableCell('date'))
                obj_amount = Env('amount')
                obj_original_amount = Env('original_amount')
                obj_original_currency = Env('original_currency')

                def parse(self, el):
                    try:
                        self.env['raw'] = "%s %s" % (CleanText().filter(TableCell('commerce')(self)[0].text), CleanText().filter(TableCell('ville')(self)[0].text))
                    except ColumnNotFound:
                        self.env['raw'] = "%s" % (CleanText().filter(TableCell('commerce')(self)[0].text))

                    self.env['amount'] = CleanDecimal(replace_dots=True).filter(TableCell('credit')(self)[0].text)
                    original_amount = TableCell('credit')(self)[0].xpath('./span')[0].text
                    if original_amount:
                        self.env['original_amount'] = CleanDecimal(replace_dots=True).filter(original_amount)
                        self.env['original_currency'] =  Account.get_currency(original_amount[1:-1])
                    else:
                        self.env['original_amount'] = NotAvailable
                        self.env['original_currency'] = NotAvailable


class NoOperationsPage(OperationsPage, LoggedPage):
    def get_history(self):
        return iter([])


class LIAccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_li_accounts(ListElement):
        item_xpath = '//table[@class]/tbody/tr[count(td)>4]'

        class item(ItemElement):
            klass = Account

            load_details = Attr('.//a', 'href', default=NotAvailable) & AsyncLoad

            obj__link_id = Async('details', Link('//li/a[contains(text(), "Mouvements")]'))
            obj__link_inv = Link('./td[1]/a', default=NotAvailable)
            obj_id = CleanText('./td[2]', replace=[(' ', '')])
            obj_label = CleanText('./td[1]')
            obj_balance = CleanDecimal('./td[3]', replace_dots=True)
            obj_currency = FrenchTransaction.Currency('./td[4]')
            obj__card_links = []
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj__is_inv = True

    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'

        class item(ItemElement):
            klass = FrenchTransaction

            obj_date = Date(CleanText('./td[1]'))
            obj_rdate = Date(CleanText('./td[1]'))
            obj_raw = CleanText('./td[2]')
            obj_amount  = CleanDecimal('./td[4]', replace_dots=True, default=Decimal('0'))
            obj_original_currency = FrenchTransaction.Currency('./td[4]')
            obj_type = Transaction.TYPE_BANK
            obj__is_coming = False

            def obj_commission(self):
                gross_amount = CleanDecimal('./td[3]', replace_dots=True, default=NotAvailable)(self)
                if gross_amount:
                    return gross_amount - Field('amount')(self)
                return NotAvailable

    @method
    class iter_investment(TableElement):
        item_xpath = '//table[@class="liste"]/tbody/tr[count(td)>7]'
        head_xpath = '//table[@class="liste"]/thead/tr/th'

        col_label = u'Support'
        col_code = re.compile(r'^Code ISIN')
        col_unitprice = re.compile(r'^Prix d\'achat moyen')
        col_vdate = re.compile(r'Date de cotation')
        col_unitvalue = u'Valeur de la part'
        col_quantity = u'Nombre de parts'
        col_valuation = u'Valeur atteinte'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_unitprice = CleanDecimal(TableCell('unitprice', default=NotAvailable), default=NotAvailable, replace_dots=True)
            obj_vdate = Date(CleanText(TableCell('vdate'), replace=[('-', '')]), default=NotAvailable)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), default=NotAvailable, replace_dots=True)
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable, replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), default=Decimal(0), replace_dots=True)

            def obj_code(self):
                return CleanText(TableCell('code'), replace=[('-', '')])(self) or NotAvailable


class PorPage(LoggedPage, HTMLPage):
    def find_amount(self, title):
        return None

    def add_por_accounts(self, accounts):
        for ele in self.doc.xpath('//select[contains(@name, "POR_Synthese")]/option'):
            for a in accounts:
                if a.id.startswith(ele.attrib['value']):
                    a._is_inv = True
                    a.type = Account.TYPE_MARKET
                    self.fill(a)
                    break
            else:
                acc = Account()
                acc.id = ele.attrib['value']
                if acc.id == '9999':
                    # fake account
                    continue
                acc.label = unicode(re.sub("\d", '', ele.text).strip())
                acc._link_id = None
                acc.type = Account.TYPE_MARKET
                acc._is_inv = True
                self.fill(acc)
                accounts.append(acc)

    def fill(self, acc):
        self.send_form(acc)
        ele = self.browser.page.doc.xpath('.//table[@class="fiche bourse"]')[0]
        balance = CleanDecimal(ele.xpath('.//td[contains(@id, "Valorisation")]'), default=Decimal(0), replace_dots=True)(ele)
        acc.balance = balance + acc.balance if acc.balance else balance
        acc.currency = FrenchTransaction.Currency('.')(ele)
        acc.valuation_diff = CleanDecimal(ele.xpath('.//td[contains(@id, "Variation")]'), default=Decimal(0), replace_dots=True)(ele)

    def send_form(self, account):
        form = self.get_form(name="frmMere")
        form['POR_SyntheseEntete1$esdselLstPor'] = re.sub('\D', '', account.id)
        form.submit()

    @method
    class iter_investment(ListElement):
        item_xpath = '//table[@id="bwebDynamicTable"]/tbody/tr[not(@id="LigneTableVide")]'
        class item(ItemElement):
            klass = Investment

            obj_label = CleanText('.//td[1]/a')
            obj_code = CleanText('.//td[1]/a/@title') & Regexp(pattern='^([^ ]+)')
            obj_quantity = CleanDecimal('.//td[2]', default=Decimal(0), replace_dots=True)
            obj_unitprice = CleanDecimal('.//td[3]', default=Decimal(0), replace_dots=True)
            obj_unitvalue = CleanDecimal('.//td[4]', default=Decimal(0), replace_dots=True)
            obj_valuation = CleanDecimal('.//td[5]', default=Decimal(0), replace_dots=True)
            obj_diff = CleanDecimal('.//td[6]', default=Decimal(0), replace_dots=True)


class IbanPage(LoggedPage, HTMLPage):
    def fill_iban(self, accounts):
        for ele in self.doc.xpath('//table[@class="liste"]/tr[@class]/td[1]'):
            for a in accounts:
                if a._is_webid:
                    if a.label in CleanText('.//div[1]')(ele).title():
                        a.iban = CleanText('.//div[5]/em', replace=[(' ', '')])(ele)
                elif self.browser.is_new_website:
                    if a.id in CleanText('.//div[5]/em', replace=[(' ','')])(ele).title():
                        a.iban = CleanText('.//div[5]/em', replace=[(' ', '')])(ele)
                else:
                    if a.id[:-3] in CleanText('.//div[5]/em', replace=[(' ','')])(ele).title():
                        a.iban = CleanText('.//div[5]/em', replace=[(' ', '')])(ele)
