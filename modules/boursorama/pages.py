# -*- coding: utf-8 -*-

# Copyright(C) 2016       Baptiste Delpey
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
from io import BytesIO
from datetime import date, timedelta

from weboob.browser.pages import HTMLPage, LoggedPage, pagination, NextPage
from weboob.browser.elements import ListElement, ItemElement, method, TableElement, SkipItem
from weboob.browser.filters.standard import CleanText, CleanDecimal, Field, Format, TableCell, \
                                            Regexp, Date, AsyncLoad, Async, Eval, RegexpError, Env
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable, empty
from weboob.capabilities.profile import Person
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.value import Value
from weboob.tools.date import parse_french_date
from weboob.tools.captcha.virtkeyboard import VirtKeyboard
from weboob.exceptions import BrowserQuestion, BrowserIncorrectPassword, BrowserHTTPNotFound


class BrowserAuthenticationCodeMaxLimit(BrowserIncorrectPassword):
    pass

class IncidentPage(HTMLPage):
    pass

class IbanPage(LoggedPage, HTMLPage):
    def get_iban(self):
        if self.doc.xpath('//div[has-class("alert")]/p[contains(text(), "Une erreur est survenue")]') or \
           self.doc.xpath('//div[has-class("alert")]/p[contains(text(), "Le compte est introuvable")]'):
            return NotAvailable
        return CleanText('//table[thead[tr[th[contains(text(), "Code I.B.A.N")]]]]/tbody/tr/td[2]', replace=[(' ', '')])(self.doc)

class AuthenticationPage(HTMLPage):
    def authenticate(self):
        self.logger.info('Using the PIN Code %s to login', self.browser.config['pin_code'].get())
        self.logger.info('Using the auth_token %s to login', self.browser.auth_token)

        form = self.get_form()
        form['otp_confirm[otpCode]'] = self.browser.config['pin_code'].get()
        form['flow_secureForm_instance'] = self.browser.auth_token
        form['otp_confirm[validate]'] = ''
        form['flow_secureForm_step'] = 2
        form.submit()

        self.browser.auth_token = None

    def sms_first_step(self):
        """
        This function simulates the registration of a device on
        boursorama two factor authentification web page.
        @param device device name to register
        @exception BrowserAuthenticationCodeMaxLimit when daily limit is consumed
        """
        form = self.get_form()
        form.submit()

    def sms_second_step(self):
        # <div class="form-errors"><ul><li>Vous avez atteint le nombre maximal de demandes pour aujourd&#039;hui</li></ul></div>
        error = CleanText('//div[has-class("form-errors")]')(self.doc)
        if len(error) > 0:
            raise BrowserIncorrectPassword(error)

        form = self.get_form()
        self.browser.auth_token = form['flow_secureForm_instance']
        form['otp_prepare[receiveCode]'] = ''
        form.submit()

        raise BrowserQuestion(Value('pin_code', label='Enter the PIN Code'))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^CHQ\. (?P<text>.*)'),        FrenchTransaction.TYPE_CHECK),
                (re.compile('^(ACHAT|PAIEMENT) CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile(r'^(?P<text>[A-Z][\sa-z]*)?(ACHAT|PAIEMENT) CARTE (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{4}) (?P<text2>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^(PRLV SEPA |PRLV |TIP )(?P<text>.*)'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^([A-Z][\sa-z]* )?RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{4}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^(Virement .* )?VIR( SEPA)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^AVOIR (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}) (?P<text>.*)'),   FrenchTransaction.TYPE_PAYBACK),
                (re.compile(r'^(?P<text>[A-Z][\sa-z]* )?AVOIR (?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{4}) (?P<text2>.*)'),   FrenchTransaction.TYPE_PAYBACK),
                (re.compile('^REM CHQ (?P<text>.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(ur'Relevé différé Carte (.*)'), FrenchTransaction.TYPE_CARD_SUMMARY),
               ]


class VirtKeyboardPage(HTMLPage):
    pass

class BoursoramaVirtKeyboard(VirtKeyboard):
    symbols = {'0': (17, 7, 24, 17),
               '1': (18, 6, 21, 18),
               '2': (9, 7, 32, 34),
               '3': (10, 7, 31, 34),
               '4': (11, 6, 29, 34),
               '5': (14, 6, 28, 34),
               '6': (7, 7, 34, 34),
               '7': (5, 6, 36, 34),
               '8': (8, 7, 32, 34),
               '9': (4, 7, 38, 34)}

    color = (255,255,255)
    md5 = {}

    def __init__(self, page):
        for span in page.doc.xpath('//span'):
            c = span.attrib['data-matrix-key']
            img = BytesIO(span.xpath('./img/@src')[0].replace('data:image/png;base64,', '').decode('base64'))
            self.load_image(img, self.color, convert='RGB')
            self.load_symbols((0,0,42,42), c)

    def load_symbols(self, coords, c):
        coord = self.get_symbol_coords(coords)
        if coord == (-1, -1, -1, -1):
            return
        self.md5[coord] = c

    def get_code(self, password):
        code = ''
        for i, d in enumerate(password):
            if i > 0:
                code += '|'
            code += self.md5[self.symbols[d]]
        return code


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form()
        keyboard_page = self.browser.keyboard.open()
        vk = BoursoramaVirtKeyboard(keyboard_page)
        code = vk.get_code(password)
        form['form[login]'] = login
        form['form[fakePassword]'] = len(password) * '•'
        form['form[password]'] = code
        form['form[matrixRandomChallenge]'] = re.search('val\("(.*)"', CleanText('//script')(keyboard_page.doc)).group(1)
        form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    def is_here(self):
        return not self.doc.xpath('//div[contains(@id, "alert-random")]')

    ACCOUNT_TYPES = {u'Comptes courants':      Account.TYPE_CHECKING,
                     u'Comptes épargne':       Account.TYPE_SAVINGS,
                     u'Comptes bourse':        Account.TYPE_MARKET,
                     u'Assurances Vie':        Account.TYPE_LIFE_INSURANCE,
                     u'Mes crédits':           Account.TYPE_LOAN,
                     u'crédit':                Account.TYPE_LOAN,
                     u'prêt':                  Account.TYPE_LOAN,
                     u'pea':                   Account.TYPE_PEA,
                    }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@class="table table--accounts"]/tr[has-class("table__line--account") and count(descendant::td) > 1]'

        class item(ItemElement):
            klass = Account

            load_details = Field('_link') & AsyncLoad

            obj_label = CleanText('.//a[@class="account--name"] | .//div[@class="account--name"]')
            obj_balance = CleanDecimal('.//a[has-class("account--balance")]', replace_dots=True)
            obj_currency = FrenchTransaction.Currency('.//a[has-class("account--balance")]')
            obj_valuation_diff = Async('details') & CleanDecimal('//li[h4[text()="Total des +/- values"]]/h3 |\
                        //li[span[text()="Total des +/- values latentes"]]/span[has-class("overview__value")]', replace_dots=True, default=NotAvailable)
            obj__card = Async('details') & Attr('//a[@data-modal-behavior="credit_card-modal-trigger"]', 'href', default=NotAvailable)
            obj__holder = None

            def obj_coming(self):
                # Don't duplicate coming (card balance with account coming)
                # TODO: fetch coming which is not card coming for account with cards.
                if self.obj__card(self):
                    return NotAvailable
                return Async('details', CleanDecimal(u'//li[h4[text()="Mouvements à venir"]]/h3', replace_dots=True, default=NotAvailable))(self)

            def obj_id(self):
                id = Async('details', Regexp(CleanText('//h3[has-class("account-number")]'), r'(\d+)', default=NotAvailable))(self)
                if not id:
                    raise SkipItem()
                return id

            def obj_type(self):
                return next((self.page.ACCOUNT_TYPES.get(word) for word in self.obj_label(self).lower().split() if self.page.ACCOUNT_TYPES.get(word)), Account.TYPE_UNKNOWN) \
                    or self.page.ACCOUNT_TYPES.get(CleanText('./preceding-sibling::tr[has-class("list--accounts--master")]//h4')(self), Account.TYPE_UNKNOWN)

            def obj__link(self):
                link = Attr('.//a[@class="account--name"] | .//a[2]', 'href', default=NotAvailable)(self)
                if not self.page.browser.webid:
                    self.page.browser.webid = re.search('\/([^\/|?|$]{32})(\/|\?|$)', link).group(1)
                return link

            def obj__webid(self):
                m = re.search('([a-z\d]{32})', self.obj__link())
                if m:
                    return m.group(1)
                return None

            # We do not yield other banks accounts for the moment.
            def validate(self, obj):
                return not Async('details', CleanText(u'//h4[contains(text(), "Établissement bancaire")]'))(self) and not \
                    Async('details', CleanText(u'//h4/div[contains(text(), "Établissement bancaire")]'))(self)


class CalendarPage(LoggedPage, HTMLPage):
    def on_load(self):
        self.browser.deferred_card_calendar = map(parse_french_date,
        [CleanText('.')(td) for td in self.doc.xpath('//div[h3[contains(text(), "CALENDRIER")]]//tr[contains(@class, "table__line")]/td[3]')])


class HistoryPage(LoggedPage, HTMLPage):
    @method
    class iter_history(ListElement):
        item_xpath = '//ul[has-class("list__movement")]/li[div and not(contains(@class, "summary")) \
                                                               and not(contains(@class, "graph")) \
                                                               and not (contains(@class, "separator"))]'

        class item(ItemElement):
            klass = Transaction

            obj_id = Attr('.', 'data-id', default=NotAvailable) or Attr('.', 'data-custom-id')
            obj_raw = Transaction.Raw(CleanText('.//div[has-class("list__movement__line--label__name")]'))
            obj_date = Date(Attr('.//time', 'datetime'))
            obj_amount = CleanDecimal('.//div[has-class("list__movement__line--amount")]', replace_dots=True)
            obj_category = CleanText('.//div[has-class("category")]')

            def obj_type(self):
                if not Env('is_card', default=False)(self):
                    # keep the value previously set by Transaction.Raw
                    return self.obj.type
                return Transaction.TYPE_DEFERRED_CARD

            def obj_rdate(self):
                if self.obj.rdate:
                    # Transaction.Raw may have already set it
                    return self.obj.rdate

                s = Regexp(Field('raw'), ' (\d{2}/\d{2}/\d{2}) | (?!NUM) (\d{6}) ', default=NotAvailable)(self)
                if not s:
                    return Field('date')(self)
                s = s.replace('/', '')
                return Date(dayfirst=True).filter('%s%s%s%s%s' % (s[:2], '-', s[2:4], '-', s[4:]))

            def obj__is_coming(self):
                return Env('coming', default=False)(self) or len(self.xpath(u'.//span[@title="Mouvement à débit différé"]')) or self.obj_date() > date.today()

            def obj_date(self):
                if Env('is_card', default=False)(self):
                    date_text = CleanText(u'//li[h3]/h4[@class="summary__title" and contains(text(), "Solde débité au")]',
                                                            replace=[(u'Solde débité au ', '')])(self)
                    if not date_text:
                        return Date(Attr('.//time', 'datetime'))(self)
                    debit_date = parse_french_date(date_text)
                    if Env('is_previous', default=False)(self):
                        debit_date = (debit_date - timedelta(days=7)).replace(day=1)
                        if self.page.browser.deferred_card_calendar is None:
                            self.page.browser.location(Link('//a[contains(text(), "calendrier")]')(self))
                        debit_date = self.page.browser.get_closest(debit_date)
                    return debit_date.date()
                return Date(Attr('.//time', 'datetime'))(self)

            # These are on deffered cards accounts.
            def condition(self):
                return not len(self.xpath(u'.//span[has-class("icon-carte-bancaire")]'))


class Myiter_investment(TableElement):
    item_xpath = '//table[contains(@class, "operations")]/tbody/tr'
    head_xpath = '//table[contains(@class, "operations")]/thead/tr/th'

    col_value = u'Valeur'
    col_quantity = u'Quantité'
    col_unitprice = u'Px. Revient'
    col_unitvalue = u'Cours'
    col_valuation = u'Montant'
    col_diff = u'+/- latentes'


class Myitem(ItemElement):
    klass = Investment

    obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)
    obj_unitprice = CleanDecimal(TableCell('unitprice'), replace_dots=True, default=NotAvailable)
    obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True, default=NotAvailable)
    obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True, default=NotAvailable)
    obj_diff = CleanDecimal(TableCell('diff'), replace_dots=True, default=NotAvailable)

    def obj_label(self):
        return CleanText().filter((TableCell('value')(self)[0]).xpath('.//a'))

    def obj_code(self):
        return CleanText().filter((TableCell('value')(self)[0]).xpath('./span')) or NotAvailable


def my_pagination(func):
    def inner(page, *args, **kwargs):
        while True:
            try:
                for r in func(page, *args, **kwargs):
                    yield r
            except NextPage as e:
                try:
                    result = page.browser.location(e.request)
                    page = result.page
                except BrowserHTTPNotFound as e:
                    page.logger.warning(e)
                    return
            else:
                return
    return inner


class MarketPage(LoggedPage, HTMLPage):
    @my_pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr'
        head_xpath = '//table/thead/tr/th'

        col_label = 'Nature'
        col_amount = 'Montant'
        col_date = ['Date d\'effet', 'Date']

        next_page = Link('//li[@class="pagination__next"]/a')

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_raw = Transaction.Raw(CleanText(TableCell('label')))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True, default=NotAvailable)
            obj__is_coming = False

            def parse(self, el):
                if el.xpath('./td[2]/a'):
                    m = re.search('(\d+)', el.xpath('./td[2]/a')[0].get('data-modal-alert-behavior', ''))
                    if m:
                        self.env['account']._history_pages.append((Field('raw')(self),\
                                                                self.page.browser.open('%s%s%s' % (self.page.url.split('mouvements')[0], 'mouvement/', m.group(1))).page))
                        raise SkipItem()

    @method
    class iter_investment(Myiter_investment):
        class item (Myitem):
            def obj_unitvalue(self):
                return CleanDecimal(replace_dots=True, default=NotAvailable).filter((TableCell('unitvalue')(self)[0]).xpath('./span[not(@class)]'))

    def get_transactions_from_detail(self, account):
        for label, page in account._history_pages:
            amounts = page.doc.xpath('//span[contains(text(), "Montant")]/following-sibling::span')
            if len(amounts) == 3:
                amounts.pop(0)
            for table in page.doc.xpath('//table'):
                t = Transaction()

                t.date = Date(CleanText(page.doc.xpath('//span[contains(text(), "Date d\'effet")]/following-sibling::span')), dayfirst=True)(page)
                t.label  = label
                t.amount = CleanDecimal(replace_dots=True).filter(amounts[0])
                amounts.pop(0)
                t._is_coming = False
                t.investments = []
                for tr in table.xpath('./tbody/tr'):
                    i = Investment()
                    i.label = CleanText().filter(tr.xpath('./td[1]'))
                    i.vdate = Date(CleanText(tr.xpath('./td[2]')), dayfirst=True)(tr)
                    i.unitvalue = CleanDecimal(replace_dots=True).filter(tr.xpath('./td[3]'))
                    i.quantity = CleanDecimal(replace_dots=True).filter(tr.xpath('./td[4]'))
                    i.valuation = CleanDecimal(replace_dots=True).filter(tr.xpath('./td[5]'))
                    t.investments.append(i)

                yield t


class SavingMarketPage(MarketPage):
    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr'
        head_xpath = '//table/thead/tr/th'

        col_label = u'Opération'
        col_amount = u'Montant'
        col_date = u'Date opération'
        col_vdate = u'Date Val'

        next_page = Link('//li[@class="pagination__next"]/a')

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal(TableCell('amount'), replace_dots=True)
            obj__is_coming = False

            def obj_date(self):
                return parse_french_date(CleanText(TableCell('date'))(self))

            def obj_vdate(self):
                return parse_french_date(CleanText(TableCell('vdate'))(self))

    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tbody/tr[count(descendant::td) > 4]'
        head_xpath = '//table/thead/tr[count(descendant::th) > 4]/th'

        col_label = u'Fonds'
        col_code = u'Code Isin'
        col_unitvalue = u'Valeur de la part'
        col_quantity = u'Nombre de parts'
        col_vdate = u'Date VL'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = CleanText(TableCell('code'))
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)
            obj_valuation = Eval(lambda x, y: x * y, Field('quantity'), Field('unitvalue'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)


class AsvPage(MarketPage):
    @method
    class iter_investment(Myiter_investment):
        col_vdate = u'Date de Valeur'

        class item(Myitem):
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)


class AccbisPage(LoggedPage, HTMLPage):
    def populate(self, accounts):
        cards = []
        for account in accounts:
            for li in  self.doc.xpath('//li[@class="nav-category"]'):
                title = CleanText().filter(li.xpath('./h3'))
                for a in li.xpath('./ul/li//a'):
                    label = CleanText().filter(a.xpath('.//span[@class="nav-category__name"]'))
                    balance_el = a.xpath('.//span[@class="nav-category__value"]')
                    balance = CleanDecimal(replace_dots=True, default=NotAvailable).filter(balance_el)
                    if 'CARTE' in label and not empty(balance):
                        acc = Account()
                        acc.balance = balance
                        acc.label = label
                        acc.currency = FrenchTransaction.Currency().filter(balance_el)
                        acc._link = Link().filter(a.xpath('.'))
                        acc._history_page = acc._link
                        try:
                            acc.id = acc._webid = Regexp(pattern='carte/(.*)$').filter(Link().filter(a.xpath('.')))
                        except RegexpError:
                            # Those are external cards, ie: amex cards
                            continue
                        acc.type = Account.TYPE_CARD
                        if not acc in cards:
                            cards.append(acc)
                    elif account.label == label and account.balance == balance:
                        if not account.type:
                            account.type = AccountsPage.ACCOUNT_TYPES.get(title, Account.TYPE_UNKNOWN)
                        account._webid = Attr(None, 'data-account-label').filter(a.xpath('.//span[@class="nav-category__name"]'))
        if cards:
            self.browser.go_cards_number()
            if self.browser.cards.is_here():
                self.browser.page.populate_cards_number(cards)
                accounts.extend(cards)


class LoanPage(LoggedPage, HTMLPage):
    pass


class ErrorPage(HTMLPage):
    pass


class ExpertPage(LoggedPage, HTMLPage):
    pass


def MyInput(*args, **kwargs):
    args = (u'//input[contains(@name, "%s")]' % args[0], 'value',)
    kwargs.update(default=NotAvailable)
    return Attr(*args, **kwargs)


def MySelect(*args, **kwargs):
    args = (u'//select[contains(@name, "%s")]/option[@selected]' % args[0],)
    kwargs.update(default=NotAvailable)
    return CleanText(*args, **kwargs)


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Person

        obj_name = Format('%s %s %s', MySelect('genderTitle'), MyInput('firstName'), MyInput('lastName'))
        obj_nationality = CleanText(u'//span[contains(text(), "Nationalité")]/span')
        obj_spouse_name = MyInput('spouseFirstName')
        obj_children = CleanDecimal(MyInput('dependentChildren'), default=NotAvailable)
        obj_family_situation = MySelect('maritalStatus')
        obj_matrimonial = MySelect('matrimonial')
        obj_housing_status = MySelect('housingSituation')
        obj_job = MyInput('occupation')
        obj_job_start_date = Date(MyInput('employeeSince'))
        obj_company_name = MyInput('employer')
        obj_socioprofessional_category = MySelect('socioProfessionalCategory')


class LinksPage(LoggedPage, HTMLPage):
    def get_cards_number_link(self):
        return Link('//a[small[span[contains(text(), "carte bancaire")]]]', default=NotAvailable)(self.doc)


class CardsNumberPage(LoggedPage, HTMLPage):
    def populate_cards_number(self, cards):
        labels = [CleanText('.', replace=[('DEBIT DIFFERE ', '')])(o) for o in self.doc.xpath('//select/option')]
        for card in cards:
            match = [label for label in labels if card.label in label]
            if len(match) == 1:
                card.number = re.search('(\d{4}\*{8}(\d{4}|\*{4}))', match[0]).group(1)


class HomePage(LoggedPage, HTMLPage):
    pass
