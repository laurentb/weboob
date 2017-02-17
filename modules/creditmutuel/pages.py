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


import re

try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs

from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from random import randint

from weboob.browser.pages import HTMLPage, FormNotFound, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, SkipItem, method, TableElement
from weboob.browser.filters.standard import Filter, Env, CleanText, CleanDecimal, Field, TableCell, Regexp, Async, AsyncLoad, Date, ColumnNotFound, Format
from weboob.browser.filters.html import Link, Attr
from weboob.exceptions import BrowserIncorrectPassword, ParseError, NoAccountsException, ActionNeeded
from weboob.capabilities import NotAvailable
from weboob.capabilities.base import empty
from weboob.capabilities.bank import Account, Investment, Recipient, TransferError, Transfer
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Profile
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class RedirectPage(LoggedPage, HTMLPage):
    def on_load(self):
        super(RedirectPage, self).on_load()
        link = self.doc.xpath('//a[@id="P:F_1.R2:link"]')
        if link:
            self.browser.location(link[0].attrib['href'])


class NewHomePage(LoggedPage, HTMLPage):
    def on_load(self):
        self.browser.is_new_website = True
        super(NewHomePage, self).on_load()


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
    def on_load(self):
        raise BrowserIncorrectPassword(CleanText('//div[has-class("blocmsg")]')(self.doc))


class EmptyPage(LoggedPage, HTMLPage):
    REFRESH_MAX = 10.0


class UserSpacePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//form[@id="GoValider"]'):
            raise ActionNeeded(u"Le site du contrat Banque à Distance a besoin d'informations supplémentaires")
        super(UserSpacePage, self).on_load()


class ChangePasswordPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Please change your password')


class VerifCodePage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Unable to login: website asks a code from a card')


class AccountsPage(LoggedPage, HTMLPage):
    def on_load(self):
        super(AccountsPage, self).on_load()

        no_account_message = CleanText(u'//td[contains(text(), "Votre contrat de banque à distance ne vous donne accès à aucun compte.")]')(self.doc)
        if no_account_message:
            raise NoAccountsException(no_account_message)

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
             u'Contrat Personnel': Account.TYPE_CHECKING,
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
                        and (first_td.find('a') is not None or (first_td.find('.//span') is not None
                        and "cartes" in first_td.findtext('.//span') and first_td.find('./div/a') is not None)))

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
            obj_label = Label(CleanText('./td[1]/a/text() | ./td[1]/a/span[@class and not(contains(@class, "doux"))] | ./td[1]/div/a[has-class("cb")]'))
            obj_coming = Env('coming')
            obj_balance = Env('balance')
            obj_currency = FrenchTransaction.Currency('./td[2] | ./td[3]')
            obj__link_id = Link('./td[1]//a')
            obj__card_links = []
            obj_type = Type(Field('label'))
            obj__is_inv = False
            obj__is_webid = Env('_is_webid')

            def parse(self, el):
                link = el.xpath('./td[1]//a')[0].get('href', '')
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
                    if 'lien_inter_sites' in link:
                        raise SkipItem()
                    else:
                        raise ParseError('Unable to find balance for account %s' % CleanText('./td[1]/a')(el))

                self.env['_is_webid'] = False

                if "cartes" in CleanText('./td[1]')(el):
                    # handle cb differed card
                    if "cartes" in CleanText('./preceding-sibling::tr[1]/td[1]', replace=[(' ', '')])(el):
                        # In case it's the second month of card history present, we need to ignore the first
                        # one to get the attach accoount
                        id_xpath = './preceding-sibling::tr[2]/td[1]/a/node()[contains(@class, "doux")]'
                    else:
                        # first month of history, the previous tr is the attached account
                        id_xpath = './preceding-sibling::tr[1]/td[1]/a/node()[contains(@class, "doux")]'
                else:
                    # classical account
                    id_xpath = './td[1]/a/node()[contains(@class, "doux")]'


                id = CleanText(id_xpath, replace=[(' ', '')])(el)
                if not id:
                    if 'rib' in p:
                        id = p['rib'][0]
                    else:
                        id = p['webid'][0]
                        self.env['_is_webid'] = True

                page = self.page.browser.open(link).page

                # Handle cards
                if id in self.parent.objects:
                    # be sure that we don't have that case anymore
                    assert not page.is_fleet()

                    account = self.parent.objects[id]
                    if not account.coming:
                        account.coming = Decimal('0.0')
                    date = parse_french_date(Regexp(Field('label'), 'Fin (.+) (\d{4})', '01 \\1 \\2')(self)) + relativedelta(day=31)
                    if date > datetime.now() - relativedelta(day=1):
                        account.coming += balance

                    # on old website we want card's history in account's history
                    if not page.browser.is_new_website:
                        account._card_links.append(link)
                    else:
                        card_xpath = u'//*[contains(@id, "MonthSelector")]'
                        for el in page.doc.xpath(u'%s/li/div/div[1] | %s//span[contains(text(), "Carte")]' % (card_xpath, card_xpath)):
                            card_id = Regexp(CleanText('.', replace=[(' ', '')]), '(?=\d)([\dx]+)')(el)
                            if any(a.id == card_id for a in page.browser.accounts_list):
                                continue

                            card = Account()
                            card.id = card_id
                            card.label = "%s %s %s" % (Regexp(CleanText('.'), 'Carte\s(\w+)')(el), card_id, \
                                                       (Regexp(CleanText('.'), '\d{4}\s([A-Za-z\s]+)', default=None)(el) \
                                                       or CleanText('./following-sibling::div[1]')(el)).strip())

                            #<li id="I1:d1.C:MonthSelectorPanel.F1_0.richlb-item" role="radio" aria-checked="false" aria-label="Carte Business 5136 16xx xxxx 1359" tabindex="-1" class="_c1 ei_richlb_item _c1"><div aria-hidden="true" class="_c1 ei_richlb_content _c1" style="height:30px;">
                            #<span class="fd ei_sdsf_montant _c1 neg _c1">-36,00 EUR</span><div>
                            #Carte Business 1234 56xx xxxx 7890
                            #</div><div class="_c1 doux _c1">
                            #M MACHIN TRUC
                            #</div> <span class="_c1 ei_valign _c1"></span>
                            #</div></li>

                            balance_xpath = './preceding-sibling::span[contains(@class, "montant")]'
                            card.balance = CleanDecimal(balance_xpath, replace_dots=True, default=NotAvailable)(el)
                            card.currency = card.get_currency(CleanText(balance_xpath)(el))

                            card.type = Account.TYPE_CARD
                            card._link_id = link
                            nextmonth = Link('./following-sibling::tr[contains(@class, "encours")][1]/td[1]//a', default=None)(self)
                            card._card_pages = [page] if not nextmonth else [page, page.browser.open(nextmonth).page]
                            card._is_inv = False
                            card._is_webid = False

                            self.page.browser.accounts_list.append(card)

                    raise SkipItem()

                self.env['id'] = id

                # Handle real balances
                coming = page.find_amount(u"Opérations à venir") if page else None
                accounting = page.find_amount(u"Solde comptable") if page else None

                if accounting is not None and accounting + (coming or Decimal('0')) != balance:
                    self.page.logger.warning('%s + %s != %s' % (accounting, coming, balance))

                if accounting is not None:
                    balance = accounting

                self.env['balance'] = balance
                self.env['coming'] = coming or NotAvailable

    def get_advisor_link(self):
        return Link('//div[@id="e_conseiller"]/a', default=None)(self.doc)

    @method
    class get_advisor(ItemElement):
        klass = Advisor

        obj_name = CleanText('//div[@id="e_conseiller"]/a')

    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = CleanText('//div[@id="e_identification_ok_content"]//strong[1]')


class NewAccountsPage(NewHomePage, AccountsPage):
    def get_agency(self):
        return Regexp(CleanText('//script[contains(text(), "lien_caisse")]', default=''),
                      r'(https://[^"]+)', default='')(self.doc)

    @method
    class get_advisor(ItemElement):
        klass = Advisor

        obj_name = Regexp(CleanText('//script[contains(text(), "Espace Conseiller")]'), 'consname.+?([\w\s]+)')

    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = CleanText('//p[contains(@class, "master_nom")]')


class AdvisorPage(LoggedPage, HTMLPage):
    @method
    class update_advisor(ItemElement):
        obj_email = CleanText('//table//*[@itemprop="email"]')
        obj_phone = CleanText('//table//*[@itemprop="telephone"]', replace=[(' ', '')])
        obj_mobile = NotAvailable
        obj_fax = CleanText('//table//*[@itemprop="faxNumber"]', replace=[(' ', '')])
        obj_agency = CleanText('//div/*[@itemprop="name"]')
        obj_address = Format('%s %s %s', CleanText('//table//*[@itemprop="streetAddress"]'),
                                         CleanText('//table//*[@itemprop="postalCode"]'),
                                         CleanText('//table//*[@itemprop="addressLocality"]'))


class CardsActivityPage(LoggedPage, HTMLPage):
    def companies_link(self):
        companies_link = []
        for tr in self.doc.xpath('//table[@summary="Liste des titulaires de contrats cartes"]//tr'):
            companies_link.append(Link(tr.xpath('.//a'))(self))
        return companies_link


class Pagination(object):
    def next_page(self):
        try:
            form = self.page.get_form('//form[@id="paginationForm"]')
        except FormNotFound:
            return self.next_month()

        text = CleanText.clean(form.el)
        m = re.search(u'(\d+) / (\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return self.next_month()

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return self.next_month()

        form['page'] = str(cur + 1)
        return form.request

    def next_month(self):
        try:
            form = self.page.get_form('//form[@id="frmStarcLstOpe"]')
        except FormNotFound:
            return

        try:
            form['moi'] = self.page.doc.xpath('//select[@id="moi"]/option[@selected]/following-sibling::option')[0].attrib['value']
        except IndexError:
            return

        return form.request


class CardsListPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_cards(TableElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'
        head_xpath = '//table[@class="liste"]/thead//tr/th'

        col_owner = 'Porteur'
        col_card = 'Carte'

        def next_page(self):
            try:
                form = self.page.get_form('//form[contains(@id, "frmStarcLstCtrPag")]')
                form['imgCtrPagSui.x'] =  randint(1, 29)
                form['imgCtrPagSui.y'] =  randint(1, 17)
                m = re.search(u'(\d+)/(\d+)', CleanText('.')(form.el))
                if m and int(m.group(1)) < int(m.group(2)):
                    return form.request
            except FormNotFound:
                return

        class item(ItemElement):
            klass = Account

            load_details = Field('_link_id') & AsyncLoad

            obj_id = Env('id', default="")
            obj_number = Field('_link_id') & Regexp(pattern='ctr=(\d+)')
            obj_label = Format('%s %s %s', CleanText(TableCell('card')), Field('id'), CleanText(TableCell('owner')))
            obj_balance = CleanDecimal('./td[small][1]', replace_dots=True, default=NotAvailable)
            obj_currency = FrenchTransaction.Currency(CleanText('./td[small][1]'))
            obj_type = Account.TYPE_CARD
            obj__card_pages = Env('page')
            obj__is_inv = False
            obj__is_webid = False

            def obj__pre_link(self):
                return self.page.url

            def obj__link_id(self):
                return Link(TableCell('card')(self)[0].xpath('./a'))(self)

            def parse(self, el):
                page = Async('details').loaded_page(self)
                self.env['page'] = [page]

                if len(page.doc.xpath(u'//caption[contains(text(), "débits immédiats")]')):
                    raise SkipItem()

                # Handle multi cards
                options = page.doc.xpath('//select[@id="iso"]/option')
                for option in options:
                    card = Account()

                    for attr in self._attrs:
                        self.handle_attr(attr, getattr(self, 'obj_%s' % attr))
                        setattr(card, attr, getattr(self.obj, attr))

                    card.id = CleanText('.', replace=[(' ', '')])(option)
                    card.label = card.label.replace('  ', ' %s ' % card.id)
                    card.balance = NotAvailable

                    self.page.browser.accounts_list.append(card)

                # Skip multi and expired cards
                if len(options) or len(page.doc.xpath('//span[@id="ERREUR"]')):
                    raise SkipItem()

                # 1 card : we have to check on another page to get id
                page = page.browser.open(Link('//form//a[text()="Contrat"]')(page.doc)).page
                xpath = '//table[@class="liste"]/tbody/tr'
                active_card = CleanText('%s[td[text()="Active"]][1]/td[2]' % xpath, replace=[(' ', '')], default=None)(page.doc)

                if not active_card and len(page.doc.xpath(xpath)) != 1:
                    raise SkipItem()

                self.env['id'] = active_card or CleanText('%s[1]/td[2]' % xpath, replace=[(' ', '')])(page.doc)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|Plt) (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^PAIEMENT PSC\s+(?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE \d+ ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<text>RELEVE CARTE.*)'), FrenchTransaction.TYPE_CARD_SUMMARY),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE( (?P<text>.*))?$'),  FrenchTransaction.TYPE_CHECK),
                (re.compile('^(F )?COTIS\.? (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(REMISE|REM CHQ) (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
               ]

    _is_coming = False


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
                    # survey to add other regx
                    parts = [re.sub(u'Détail|Date de valeur\s+:\s+\d{2}/\d{2}(/\d{4})?', '',txt.strip()) for txt in el.itertext() if len(txt.strip()) > 0]
                    # To simplify categorization of CB, reverse order of parts to separate
                    # location and institution.
                    if parts[0] == u"Cliquer pour déplier ou plier le détail de l'opération":
                        parts.pop(0)
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


class CardsOpePage(OperationsPage):
    def select_card(self, card_number):
        if CleanText('//select[@id="iso"]', default=None)(self.doc):
            form = self.get_form('//p[@class="restriction"]')
            card_number = ' '.join([card_number[j*4:j*4+4] for j in xrange(len(card_number)/4+1)]).strip()
            form['iso'] = Attr('//option[text()="%s"]' % card_number, 'value')(self.doc)
            moi = Attr('//select[@id="moi"]/option[@selected]', 'value', default=None)(self.doc)
            if moi:
                form['moi'] = moi
            return self.browser.open(form.url, data=dict(form)).page
        return self

    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[@class="liste"]//thead//tr/th'
        item_xpath = '//table[@class="liste"]/tr'

        col_city = u'Ville'
        col_original_amount = u'Montant d\'origine'
        col_amount = u'Montant'

        class item(Transaction.TransactionElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 5

            obj_raw = obj_label = Format('%s %s', TableCell('raw') & CleanText, TableCell('city') & CleanText)
            obj_original_amount = CleanDecimal(TableCell('original_amount'), default=NotAvailable, replace_dots=True)
            obj_original_currency = FrenchTransaction.Currency(TableCell('original_amount'))
            obj_type = Transaction.TYPE_DEFERRED_CARD
            obj_rdate = Transaction.Date(TableCell('date'))
            obj_date = obj_vdate = Env('date')
            obj__is_coming = Env('_is_coming')
            obj_amount = CleanDecimal(Env('amount'), replace_dots=True)
            obj_commission = CleanDecimal(Format('-%s', Env('commission')), replace_dots=True, default=NotAvailable)

            def parse(self, el):
                self.env['date'] = Date(Regexp(CleanText(u'//td[contains(text(), "Total prélevé")]'), ' (\d{2}/\d{2}/\d{4})', \
                                               default=NotAvailable), default=NotAvailable)(self)
                if not self.env['date']:
                    try:
                        d = CleanText(u'//select[@id="moi"]/option[@selected]')(self) or \
                            re.search('pour le mois de (.*)', ''.join(w.strip() for w in self.page.doc.xpath('//div[@class="a_blocongfond"]/text()'))).group(1)
                    except AttributeError:
                        d = Regexp(CleanText('//p[@class="restriction"]'), 'pour le mois de ((?:\w+\s+){2})', flags=re.UNICODE)(self)
                    self.env['date'] = (parse_french_date('%s %s' % ('1', d)) + relativedelta(day=31)).date()
                self.env['_is_coming'] = date.today() < self.env['date']
                amount = CleanText(TableCell('amount'))(self).split('dont frais')
                self.env['amount'] = amount[0]
                self.env['commission'] = amount[1] if len(amount) > 1 else NotAvailable


class ComingPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[@class="liste"]//thead//tr/th/text()'
        item_xpath = '//table[@class="liste"]//tbody/tr'

        col_date = u"Date de l'annonce"

        class item(Transaction.TransactionElement):
            obj__is_coming = True


class CardPage(OperationsPage, LoggedPage):
    def is_fleet(self):
        return len(self.doc.xpath('//table[@class="liste"]/tbody/tr/td/a')) >= 5

    def select_card(self, card_number):
        for option in self.doc.xpath('//select[@name="Data_SelectedCardItemKey"]/option'):
            card_id = Regexp(CleanText('.', replace=[(' ', '')]), '(?=\d)([\dx]+)')(option)
            if card_id != card_number:
                continue
            if Attr('.', 'selected', default=None)(option):
                break

            form = self.get_form('//form[@id="I1:fm"]', submit='//input[@type="submit"]')
            [form.pop(k, None) for k in form.keys() if k.startswith('_FID_Do')]
            form['_FID_DoChangeCardDetails'] = ""
            form['Data_SelectedCardItemKey'] = Attr('.', 'value')(option)
            return self.browser.open(form.url, data=dict(form)).page
        return self

    @method
    class get_history(Pagination, ListElement):
        class list_cards(ListElement):
            item_xpath = '//table[@class="liste"]/tbody/tr/td/a'

            class item(ItemElement):
                def __iter__(self):
                    card_link = self.el.get('href')
                    page = self.page.browser.location(card_link).page

                    for op in page.get_history():
                        yield op

        class list_history(Transaction.TransactionsElement):
            head_xpath = '//table[@class="liste"]//thead/tr/th'
            item_xpath = '//table[@class="liste"]/tbody/tr'

            col_commerce = u'Commerce'
            col_ville = u'Ville'

            def parse(self, el):
                label = CleanText(u'//*[contains(text(), "Achats")]')(el)
                if not label:
                    return
                label = re.findall('(\d+ [^ ]+ \d+)', label)[-1]
                # use the trick of relativedelta to get the last day of month.
                self.env['debit_date'] = (parse_french_date(label) + relativedelta(day=31)).date()

            class item(Transaction.TransactionElement):
                condition = lambda self: len(self.el.xpath('./td')) >= 4

                obj_raw = Transaction.Raw(Env('raw'))
                obj_type = Env('type')
                obj_date = Env('debit_date')
                obj_rdate = Transaction.Date(TableCell('date'))
                obj_amount = Env('amount')
                obj_original_amount = Env('original_amount')
                obj_original_currency = Env('original_currency')
                obj__differed_date = Env('differed_date')

                def parse(self, el):
                    try:
                        self.env['raw'] = "%s %s" % (CleanText().filter(TableCell('commerce')(self)[0].text), CleanText().filter(TableCell('ville')(self)[0].text))
                    except (ColumnNotFound, AttributeError):
                        self.env['raw'] = "%s" % (CleanText().filter(TableCell('commerce')(self)[0].text))

                    self.env['type'] = Transaction.TYPE_DEFERRED_CARD \
                                       if CleanText(u'//a[contains(text(), "Prélevé fin")]', default=None) else Transaction.TYPE_CARD
                    self.env['differed_date'] = parse_french_date(Regexp(CleanText(u'//*[contains(text(), "Achats")]'), 'au[\s]+(.*)')(self)).date()
                    amount = TableCell('credit')(self)[0]
                    if self.page.browser.is_new_website:
                        if not len(amount.xpath('./div')):
                            amount = TableCell('debit')(self)[0]
                        original_amount = amount.xpath('./div')[1].text if len(amount.xpath('./div')) > 1 else None
                        amount = amount.xpath('./div')[0]
                    else:
                        try:
                            original_amount = amount.xpath('./span')[0].text
                        except IndexError:
                            original_amount = None
                    self.env['amount'] = CleanDecimal(replace_dots=True).filter(amount.text)
                    self.env['original_amount'] = CleanDecimal(replace_dots=True).filter(original_amount) \
                                                  if original_amount is not None else NotAvailable
                    self.env['original_currency'] = Account.get_currency(original_amount[1:-1]) \
                                                  if original_amount is not None else NotAvailable


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
            obj_balance = CleanDecimal('./td[3]', replace_dots=True, default=NotAvailable)
            obj_currency = FrenchTransaction.Currency('./td[3]')
            obj__card_links = []
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj__is_inv = True

    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'

        class item(ItemElement):
            klass = FrenchTransaction

            obj_date = obj_rdate = Transaction.Date(CleanText('./td[1]'))
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
                link = Link(TableCell('label')(self)[0].xpath('./a'), default=NotAvailable)(self)
                if not link:
                    return NotAvailable
                return Regexp(pattern='isin=([A-Z\d]+)&?', default=NotAvailable).filter(link)



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

        # Old website
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

        # New website
        for ele in self.doc.xpath('//table[@class="liste"]//tr[not(@class)]/td[1]'):
            for a in accounts:
                if a.id.split('EUR')[0] in CleanText('.//em[2]', replace=[(' ', '')])(ele):
                    a.iban = CleanText('.//em[2]', replace=[(' ', '')])(ele)


class MyRecipient(ItemElement):
    klass = Recipient

    obj_currency = u'EUR'
    obj_label = CleanText('.//div[@role="presentation"]/em | .//div[not(@id) and not(@role)]')

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)

    def validate(self, el):
        return not el.iban or is_iban_valid(el.iban)


class InternalTransferPage(LoggedPage, HTMLPage):
    RECIPIENT_STRING = 'data_input_indiceCompteACrediter'
    READY_FOR_TRANSFER_MSG = u'Confirmer un virement entre vos comptes'
    SUMMARY_RECIPIENT_TITLE = u'Compte à créditer'
    IS_PRO_PAGE = False

    def can_transfer_pro(self, origin_account):
        for li in self.doc.xpath('//ul[@id="idDetailsListCptDebiterVertical:ul"]//ul/li'):
            if CleanText(li.xpath('.//span[@class="_c1 doux _c1"]'), replace=[(' ', '')])(self) in origin_account:
                return True

    def can_transfer(self, origin_account):
        if self.doc.xpath('//ul[@id="idDetailsListCptDebiterVertical:ul"]') or self.doc.xpath('//ul[@id="idDetailListCptDebiter:ul"]'):
            self.IS_PRO_PAGE = True
            return self.can_transfer_pro(origin_account)

        for li in self.doc.xpath('//ul[@id="idDetailsListCptDebiterHorizontal:ul"]/li'):
            if CleanText(li.xpath('.//span[@class="_c1 doux _c1"]'), replace=[(' ', '')])(self) in origin_account:
                return True

    @method
    class iter_recipients(ListElement):
        def parse(self, el):
            if self.page.IS_PRO_PAGE:
                self.item_xpath = '//ul[@id="idDetailsListCptCrediterVertical:ul"]//ul/li'
            else:
                self.item_xpath = '//ul[@id="idDetailsListCptCrediterHorizontal:ul"]//li[@role="radio"]'

        class item(MyRecipient):
            condition = lambda self: Field('id')(self) not in self.env['origin_account'].id

            obj_bank_name = u'Crédit Mutuel'
            obj_label = CleanText('.//div[@role="presentation"]/em | .//div[not(@id) and not(@role)]')
            obj_id = CleanText('.//span[@class="_c1 doux _c1"]', replace=[(' ', '')])
            obj_category = u'Interne'

            def obj_iban(self):
                l = [a for a in self.page.browser.get_accounts_list() if Field('id')(self) in a.id and empty(a.valuation_diff)]
                assert len(l) == 1
                return l[0].iban

    def get_account_index(self, direction, account):
        for div in self.doc.getroot().cssselect(".dw_dli_contents"):
            inp = div.cssselect("input")[0]
            if inp.name != direction:
                continue
            acct = div.cssselect("span.doux")[0].text.replace(" ", "")
            if account.endswith(acct):
                return inp.attrib['value']
        else:
            raise TransferError("account %s not found" % account)

    def get_from_account_index(self, account):
        return self.get_account_index('data_input_indiceCompteADebiter', account)

    def get_to_account_index(self, account):
        return self.get_account_index(self.RECIPIENT_STRING, account)

    def get_unicode_content(self):
        return self.content.decode(self.detect_encoding())

    def prepare_transfer(self, account, to, amount, reason):
        form = self.get_form(id='P:F', submit='//input[@type="submit" and contains(@value, "Valider")]')
        form['data_input_indiceCompteADebiter'] = self.get_from_account_index(account.id)
        form[self.RECIPIENT_STRING] = self.get_to_account_index(to.id)
        form['[t:dbt%3adouble;]data_input_montant_value_0_'] = str(amount).replace('.', ',')
        form['[t:dbt%3astring;x(27)]data_input_libelleCompteDebite'] = reason
        form['[t:dbt%3astring;x(31)]data_input_motifCompteCredite'] = reason
        form['[t:dbt%3astring;x(31)]data_input_motifCompteCredite1'] = reason

        form.submit()

    def check_errors(self):
        # look for known errors
        content = self.get_unicode_content()
        messages = [u'Le montant du virement doit être positif, veuillez le modifier',
                    u'Montant maximum autorisé au débit pour ce compte',
                    u'Dépassement du montant journalier autorisé']

        for message in messages:
            if message in content:
                raise TransferError(message)

        # look for the known "all right" message
        if not self.doc.xpath(u'//span[contains(text(), "%s")]' % self.READY_FOR_TRANSFER_MSG):
            raise TransferError('The expected message "%s" was not found.' % self.READY_FOR_TRANSFER_MSG)

    def check_data_consistency(self, account_id, recipient_id, amount, reason):
        assert account_id in CleanText(u'//div[div[p[contains(text(), "Compte à débiter")]]]', replace=[(' ', '')])(self.doc)
        assert recipient_id in CleanText(u'//div[div[p[contains(text(), "%s")]]]' % self.SUMMARY_RECIPIENT_TITLE, replace=[(' ', '')])(self.doc)

        exec_date = Date(Regexp(CleanText('//table[@summary]/tbody/tr[th[contains(text(), "Date")]]/td'), '(\d{2}/\d{2}/\d{4})'), dayfirst=True)(self.doc)
        assert exec_date == datetime.today().date()
        r_amount = CleanDecimal('//table[@summary]/tbody/tr[th[contains(text(), "Montant")]]/td', replace_dots=True)(self.doc)
        assert r_amount == Decimal(amount)
        currency = FrenchTransaction.Currency('//table[@summary]/tbody/tr[th[contains(text(), "Montant")]]/td')(self.doc)
        if reason is not None:
            assert reason.upper().strip()[:22] in CleanText(u'//table[@summary]/tbody/tr[th[contains(text(), "Intitulé pour le compte à débiter")]]/td')(self.doc)
        return exec_date, r_amount, currency

    def handle_response(self, account, recipient, amount, reason):
        self.check_errors()

        exec_date, r_amount, currency = self.check_data_consistency(account.id, recipient.id, amount, reason)
        parsed = urlparse(self.url)
        webid = parse_qs(parsed.query)['_saguid'][0]

        transfer = Transfer()
        transfer.currency = currency
        transfer.amount = r_amount
        transfer.account_iban = account.iban
        transfer.recipient_iban = recipient.iban
        transfer.account_id = account.id
        transfer.recipient_id = recipient.id
        transfer.exec_date = exec_date
        transfer.label = reason

        transfer.account_label = account.label
        transfer.recipient_label = recipient.label
        transfer.account_balance = account.balance
        transfer.id = webid

        return transfer

    def create_transfer(self, transfer):
        # look for the known "everything went well" message
        content = self.get_unicode_content()
        transfer_ok_message = u'Votre virement a &#233;t&#233; ex&#233;cut&#233;'
        if transfer_ok_message not in content:
            raise TransferError('The expected message "%s" was not found.' % transfer_ok_message)

        exec_date, r_amount, currency = self.check_data_consistency(transfer.account_id, transfer.recipient_id, transfer.amount, transfer.label)
        assert u'Exécuté' in CleanText(u'//table[@summary]/tbody/tr[th[contains(text(), "Etat")]]/td')(self.doc)

        assert transfer.amount == r_amount
        assert transfer.exec_date == exec_date
        assert transfer.currency == currency

        return transfer


class ExternalTransferPage(InternalTransferPage):
    RECIPIENT_STRING = 'data_input_indiceBeneficiaire'
    READY_FOR_TRANSFER_MSG = u'Confirmer un virement vers un bénéficiaire enregistré'
    SUMMARY_RECIPIENT_TITLE = u'Bénéficiaire à créditer'

    def can_transfer_pro(self, origin_account):
        for li in self.doc.xpath('//ul[@id="idDetailListCptDebiter:ul"]//ul/li'):
            if CleanText(li.xpath('.//span[@class="_c1 doux _c1"]'), replace=[(' ', '')])(self) in origin_account:
                return True

    def has_transfer_categories(self):
        select_elem = self.doc.xpath('//select[@name="data_input_indiceMarqueurListe"]')
        if select_elem:
            assert len(select_elem) == 1
            return True

    def iter_categories(self):
        for option in self.doc.xpath('//select[@name="data_input_indiceMarqueurListe"]/option'):
            # This is the default selector
            if option.attrib['value'] == '9999':
                continue
            yield {'name': CleanText('.')(option), 'index': option.attrib['value']}

    def go_on_category(self, category_index):
        form = self.get_form(id='P:F', submit='//input[@type="submit" and @value="Nom"]')
        form['data_input_indiceMarqueurListe'] = category_index
        form.submit()

    @method
    class iter_recipients(ListElement):
        def parse(self, el):
            if self.page.IS_PRO_PAGE:
                self.item_xpath = '//ul[@id="ben.idBen:ul"]/li'
            else:
                self.item_xpath = '//ul[@id="idDetailListCptCrediterHorizontal:ul"]/li'

        class item(MyRecipient):
            condition = lambda self: Field('id')(self) not in self.env['origin_account']._external_recipients

            obj_bank_name = CleanText('(.//span[@class="_c1 doux _c1"])[2]', default=NotAvailable)
            obj_label = CleanText('./div//em')

            def obj_category(self):
                return self.env['category'] if 'category' in self.env else u'Externe'

            def obj_id(self):
                if self.page.IS_PRO_PAGE:
                    return CleanText('(.//span[@class="_c1 doux _c1"])[1]', replace=[(' ', '')])(self.el)
                else:
                    return CleanText('.//span[@class="_c1 doux _c1"]', replace=[(' ', '')])(self.el)

            def obj_iban(self):
                return Field('id')(self)

            def parse(self, el):
                self.env['origin_account']._external_recipients.add(Field('id')(self))
