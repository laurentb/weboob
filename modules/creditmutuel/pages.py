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

from __future__ import unicode_literals

import re
import hashlib

from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from random import randint
from collections import OrderedDict

from weboob.browser.pages import HTMLPage, FormNotFound, LoggedPage, pagination
from weboob.browser.elements import ListElement, ItemElement, SkipItem, method, TableElement
from weboob.browser.filters.standard import Filter, Env, CleanText, CleanDecimal, Field, \
    Regexp, Async, AsyncLoad, Date, Format, Type, Currency
from weboob.browser.filters.html import Link, Attr, TableCell, ColumnNotFound
from weboob.exceptions import (
    BrowserIncorrectPassword, ParseError, NoAccountsException, ActionNeeded, BrowserUnavailable,
    AuthMethodNotImplemented,
)
from weboob.capabilities import NotAvailable
from weboob.capabilities.base import empty, find_object
from weboob.capabilities.bank import Account, Investment, Recipient, TransferError, TransferBankError, \
    Transfer, AddRecipientError, AddRecipientStep, Loan
from weboob.capabilities.contact import Advisor
from weboob.capabilities.profile import Profile
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.capabilities.bill import Subscription, Document
from weboob.tools.compat import urlparse, parse_qs, urljoin, range, unicode
from weboob.tools.date import parse_french_date
from weboob.tools.value import Value


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)

def MyDate(*args, **kwargs):
    kwargs.update(dayfirst=True, default=NotAvailable)
    return Date(*args, **kwargs)

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

    def on_load(self):
        error_msg_xpath = '//div[has-class("err")]//p[contains(text(), "votre mot de passe est faux")]'
        if self.doc.xpath(error_msg_xpath):
            raise BrowserIncorrectPassword(CleanText(error_msg_xpath)(self.doc))

    def login(self, login, passwd):
        form = self.get_form(xpath='//form[contains(@name, "ident")]')
        # format login/password like login/password sent by firefox or chromium browser
        form['_cm_user'] = login.encode('cp1252', errors='xmlcharrefreplace').decode('cp1252')
        form['_cm_pwd'] = passwd.encode('cp1252', errors='xmlcharrefreplace').decode('cp1252')
        form.submit()

    @property
    def logged(self):
        return self.doc.xpath('//div[@id="e_identification_ok"]')


class LoginErrorPage(HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword(CleanText('//div[has-class("blocmsg")]')(self.doc))


class EmptyPage(LoggedPage, HTMLPage):
    REFRESH_MAX = 10.0

    def on_load(self):
        # Action needed message is like "Votre Carte de Clés Personnelles numéro 3 est révoquée."
        action_needed = CleanText('//p[contains(text(), "Votre Carte de Clés Personnelles") and contains(text(), "est révoquée")]')(self.doc)
        if action_needed:
            raise ActionNeeded(action_needed)
        maintenance = CleanText('//td[@class="ALERTE"]/p/span[contains(text(), "Dans le cadre de l\'amélioration de nos services, nous vous informons que le service est interrompu")]')(self.doc)
        if maintenance:
            raise BrowserUnavailable(maintenance)


class UserSpacePage(LoggedPage, HTMLPage):
    def on_load(self):
        if self.doc.xpath('//form[@id="GoValider"]'):
            raise ActionNeeded(u"Le site du contrat Banque à Distance a besoin d'informations supplémentaires")
        super(UserSpacePage, self).on_load()


class ChangePasswordPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Please change your password')


class item_account_generic(ItemElement):
    klass = Account

    TYPES = OrderedDict([
        ('Credits Promoteurs',      Account.TYPE_CHECKING),  # it doesn't fit loan's model
        ('Compte Cheque',           Account.TYPE_CHECKING),
        ('Compte Courant',          Account.TYPE_CHECKING),
        ('Cpte Courant',            Account.TYPE_CHECKING),
        ('Contrat Personnel',       Account.TYPE_CHECKING),
        ('Cc Contrat Personnel',    Account.TYPE_CHECKING),
        ('C/C',                     Account.TYPE_CHECKING),
        ('Start',                   Account.TYPE_CHECKING),
        ('Comptes courants',        Account.TYPE_CHECKING),
        ('Catip',                   Account.TYPE_DEPOSIT),
        ('Cic Immo',                Account.TYPE_LOAN),
        ('Credit',                  Account.TYPE_LOAN),
        ('Crédits',                 Account.TYPE_LOAN),
        ('Eco-Prêt',                Account.TYPE_LOAN),
        ('Mcne',                    Account.TYPE_LOAN),
        ('Nouveau Prêt',            Account.TYPE_LOAN),
        ('Pret',                    Account.TYPE_LOAN),
        ('Regroupement De Credits', Account.TYPE_LOAN),
        ('Nouveau Pret 0%',         Account.TYPE_LOAN),
        ('Passeport Credit',        Account.TYPE_REVOLVING_CREDIT),
        ('Allure Libre',            Account.TYPE_REVOLVING_CREDIT),
        ('Preference',              Account.TYPE_REVOLVING_CREDIT),
        ('Plan 4',                  Account.TYPE_REVOLVING_CREDIT),
        ('P.E.A',                   Account.TYPE_PEA),
        ('Pea',                     Account.TYPE_PEA),
        ('Compte De Liquidite Pea', Account.TYPE_PEA),
        ('Compte Epargne',          Account.TYPE_SAVINGS),
        ('Etalis',                  Account.TYPE_SAVINGS),
        ('Ldd',                     Account.TYPE_SAVINGS),
        ('Livret',                  Account.TYPE_SAVINGS),
        ("Plan D'Epargne",          Account.TYPE_SAVINGS),
        ('Tonic Croissance',        Account.TYPE_SAVINGS),
        ('Capital Expansion',       Account.TYPE_SAVINGS),
        ('\xc9pargne',              Account.TYPE_SAVINGS),
        ('Compte Garantie Titres',  Account.TYPE_MARKET),
        ])

    REVOLVING_LOAN_LABELS = [
        'Passeport Credit',
        'Allure Libre',
        'Preference',
        'Plan 4',
        'Credit En Reserve',
    ]

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
            for pattern, actype in item_account_generic.TYPES.items():
                if label.startswith(pattern):
                    return actype
            return Account.TYPE_UNKNOWN

    obj_id = Env('id')
    obj_number = Env('id')
    obj__card_number = None
    obj_label = Label(CleanText('./td[1]/a/text() | ./td[1]/a/span[@class and not(contains(@class, "doux"))] | ./td[1]/div/a[has-class("cb")]'))
    obj_coming = Env('coming')
    obj_balance = Env('balance')
    obj_currency = FrenchTransaction.Currency('./td[2] | ./td[3]')
    obj__card_links = []

    def obj__link_id(self):
        if self.is_revolving(Field('label')(self)):
            page = self.page.browser.open(Link('./td[1]//a')(self)).page
            if page and page.doc.xpath('//div[@class="fg"]/a[contains(@href, "%s")]' % Field('id')(self)):
                return urljoin(page.url, Link('//div[@class="fg"]/a')(page.doc))
        return Link('./td[1]//a')(self)

    def obj_type(self):
        t = self.Type(Field('label'))(self)
        # sometimes, using the label is not enough to infer the account's type.
        # this is a fallback that uses the account's group label
        if t == 0:
            return self.Type(CleanText('./preceding-sibling::tr/th[contains(@class, "rupture eir_tblshowth")][1]'))(self)
        return t

    obj__is_inv = False
    obj__is_webid = Env('_is_webid')

    def parse(self, el):
        accounting = None
        coming = None
        page = None
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

        if self.is_revolving(Field('label')(self)):
            page = self.page.browser.open(link).page
            if isinstance(page, RevolvingLoansList):
                # some revolving loans are listed on an other page. On the accountList, there is just a link for this page
                # that's why we don't handle it here
                raise SkipItem()

        # Handle cards
        if id in self.parent.objects:
            if not page:
                page = self.page.browser.open(link).page
            # Handle real balances
            coming = page.find_amount(u"Opérations à venir") if page else None
            accounting = page.find_amount(u"Solde comptable") if page else None
            # on old website we want card's history in account's history
            if not page.browser.is_new_website:
                account = self.parent.objects[id]
                if not account.coming:
                    account.coming = Decimal('0.0')
                date = parse_french_date(Regexp(Field('label'), 'Fin (.+) (\d{4})', '01 \\1 \\2')(self)) + relativedelta(day=31)
                if date > datetime.now() - relativedelta(day=1):
                    account.coming += balance
                account._card_links.append(link)
            else:
                multiple_cards_xpath = '//select[@name="Data_SelectedCardItemKey"]/option[contains(text(),"Carte")]'
                single_card_xpath = '//span[has-class("_c1 fg _c1")]'
                card_xpath = multiple_cards_xpath + ' | ' + single_card_xpath
                for elem in page.doc.xpath(card_xpath):
                    card_id = Regexp(CleanText('.', symbols=' '), '([\dx]{16})')(elem)
                    if any(card_id in a.id for a in page.browser.accounts_list):
                        continue

                    card = Account()
                    card.type = Account.TYPE_CARD
                    card.id = card._card_number = card_id
                    card._link_id = link
                    card._is_inv = card._is_webid = False
                    card.parent = self.parent.objects[id]

                    pattern = 'Carte\s(\w+).*\d{4}\s([A-Za-z\s]+)(.*)'
                    m = re.search(pattern, CleanText('.')(elem))
                    card.label = "%s %s %s" % (m.group(1), card_id, m.group(2))
                    card.balance = Decimal('0.0')
                    card.currency = card.get_currency(m.group(3))
                    card._card_pages = [page]
                    card.coming = Decimal('0.0')
                    #handling the case were the month is the coming one. There won't be next_month here.
                    date = parse_french_date(Regexp(Field('label'), 'Fin (.+) (\d{4})', '01 \\1 \\2')(self)) + relativedelta(day=31)
                    if date > datetime.now() - relativedelta(day=1):
                        card.coming = CleanDecimal(replace_dots=True).filter(m.group(3))
                    next_month = Link('./following-sibling::tr[contains(@class, "encours")][1]/td[1]//a', default=None)(self)
                    if next_month:
                        card_page = page.browser.open(next_month).page
                        for e in card_page.doc.xpath(card_xpath):
                            if card.id == Regexp(CleanText('.', symbols=' '), '([\dx]{16})')(e):
                                m = re.search(pattern, CleanText('.')(e))
                                card._card_pages.append(card_page)
                                card.coming += CleanDecimal(replace_dots=True).filter(m.group(3))
                                break

                    self.page.browser.accounts_list.append(card)

            raise SkipItem()

        self.env['id'] = id

        if accounting is not None and accounting + (coming or Decimal('0')) != balance:
            self.page.logger.warning('%s + %s != %s' % (accounting, coming, balance))

        if accounting is not None:
            balance = accounting

        self.env['balance'] = balance
        self.env['coming'] = coming or NotAvailable

    def is_revolving(self, label):
        return any(revolving_loan_label in label
                   for revolving_loan_label in item_account_generic.REVOLVING_LOAN_LABELS) or label.lower() in self.page.browser.revolving_accounts


class AccountsPage(LoggedPage, HTMLPage):
    def on_load(self):
        super(AccountsPage, self).on_load()

        no_account_message = CleanText('//td[contains(text(), "Votre contrat de banque à distance ne vous donne accès à aucun compte.")]')(self.doc)
        if no_account_message:
            raise NoAccountsException(no_account_message)

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[has-class("a_blocappli")]//tr'
        flush_at_end = True

        class item_account(item_account_generic):
            def condition(self):
                type = Field('type')(self)
                return item_account_generic.condition(self) and type != Account.TYPE_LOAN

        class item_loan(item_account_generic):
            klass = Loan

            load_details = Link('.//a') & AsyncLoad

            obj_total_amount = Async('details') & MyDecimal('//div[@id="F4:expContent"]/table/tbody/tr[1]/td[1]/text()')
            obj_rate = Async('details') & MyDecimal('//div[@id="F4:expContent"]/table/tbody/tr[2]/td[1]')
            obj_account_label = Async('details') & CleanText('//div[@id="F4:expContent"]/table/tbody/tr[1]/td[2]')
            obj_nb_payments_left = Async('details') & Type(CleanText(
                '//div[@id="F4:expContent"]/table/tbody/tr[2]/td[2]/text()'), type=int, default=NotAvailable)
            obj_subscription_date = Async('details') & MyDate(Regexp(CleanText(
                '//*[@id="F4:expContent"]/table/tbody/tr[1]/th[1]'), ' (\d{2}/\d{2}/\d{4})', default=NotAvailable))
            obj_maturity_date = Async('details') & MyDate(
                CleanText('//div[@id="F4:expContent"]/table/tbody/tr[4]/td[2]'))

            obj_next_payment_amount = Async('details') & MyDecimal('//div[@id="F4:expContent"]/table/tbody/tr[3]/td[2]')
            obj_next_payment_date = Async('details') & MyDate(
                CleanText('//div[@id="F4:expContent"]/table/tbody/tr[3]/td[1]'))

            obj_last_payment_amount = Async('details') & MyDecimal('//td[@id="F2_0.T12"]')
            obj_last_payment_date = Async('details') & \
                MyDate(CleanText('//div[@id="F8:expContent"]/table/tbody/tr[1]/td[1]'))

            def condition(self):
                type = Field('type')(self)
                label = Field('label')(self)
                details_link = Link('.//a', default=None)(self)

                # mobile accounts are leading to a 404 error when parsing history
                # furthermore this is not exactly a loan account
                if re.search(r'Le\sMobile\s+([0-9]{2}\s?){5}', label):
                    return False

                if details_link and item_account_generic.condition and type == Account.TYPE_LOAN and not self.is_revolving(label):
                    details = self.page.browser.open(details_link)
                    if details.page and not 'cloturé' in CleanText('//form[@id="P:F"]//div[@class="blocmsg info"]//p')(details.page.doc):
                        return True
                return False


        class item_revolving_loan(item_account_generic):
            klass = Loan

            load_details = Link('.//a') & AsyncLoad

            obj_total_amount = Async('details') & MyDecimal('//main[@id="ei_tpl_content"]/div/div[2]/table/tbody/tr/td[3]')

            def obj_used_amount(self):
                return -Field('balance')(self)

            def condition(self):
                type = Field('type')(self)
                label = Field('label')(self)
                return (item_account_generic.condition(self) and type == Account.TYPE_LOAN
                        and self.is_revolving(label))

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
            form = self.page.get_form('//form[@id="paginationForm" or @id="frmSTARCpag"]')
        except FormNotFound:
            return self.next_month()

        text = CleanText.clean(form.el)
        m = re.search('(\d+)/(\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return self.next_month()

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return self.next_month()

        form['imgOpePagSui.x'] = randint(1, 29)
        form['imgOpePagSui.y'] = randint(1, 17)

        form['page'] = str(cur + 1)
        return form.request

    def next_month(self):
        try:
            form = self.page.get_form('//form[@id="frmStarcLstOpe"]')
        except FormNotFound:
            return

        try:
            form['moi'] = self.page.doc.xpath('//select[@id="moi"]/option[@selected]/following-sibling::option')[0].attrib['value']
            form['page'] = 1
        except IndexError:
            return

        return form.request


class CardsListPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_cards(TableElement):
        item_xpath = '//table[has-class("liste")]/tbody/tr'
        head_xpath = '//table[has-class("liste")]/thead//tr/th'

        col_owner = 'Porteur'
        col_card = 'Carte'

        def next_page(self):
            try:
                form = self.page.get_form('//form[contains(@id, "frmStarcLstCtrPag")]')
                form['imgCtrPagSui.x'] =  randint(1, 29)
                form['imgCtrPagSui.y'] =  randint(1, 17)
                m = re.search('(\d+)/(\d+)', CleanText('.')(form.el))
                if m and int(m.group(1)) < int(m.group(2)):
                    return form.request
            except FormNotFound:
                return

        class item(ItemElement):
            klass = Account

            load_details = Field('_link_id') & AsyncLoad

            obj_number = Field('_link_id') & Regexp(pattern='ctr=(\d+)')
            obj__card_number = Env('id', default="")
            obj_id = Format('%s%s', Env('id', default=""), Field('number'))
            obj_label = Format('%s %s %s', CleanText(TableCell('card')), Env('id', default=""), CleanText(TableCell('owner')))
            obj_coming = CleanDecimal('./td[@class="i d" or @class="p d"][2]', replace_dots=True, default=NotAvailable)
            obj_balance = Decimal('0.00')
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

                if len(page.doc.xpath('//caption[contains(text(), "débits immédiats")]')):
                    raise SkipItem()

                # Handle multi cards
                options = page.doc.xpath('//select[@id="iso"]/option')
                for option in options:
                    card = Account()
                    card_list_page = page.browser.open(Link('//form//a[text()="Contrat"]', default=None)(page.doc)).page
                    xpath = '//table[has-class("liste")]/tbody/tr'
                    active_card = CleanText('%s[td[text()="Active"]][1]/td[2]' % xpath, replace=[(' ', '')], default=None)(card_list_page.doc)
                    _id = CleanText('.', replace=[(' ', '')])(option)
                    if active_card == _id:
                        for attr in self._attrs:
                            self.handle_attr(attr, getattr(self, 'obj_%s' % attr))
                            setattr(card, attr, getattr(self.obj, attr))

                        card._card_number = _id
                        card.id = _id + card.number
                        card.label = card.label.replace('  ', ' %s ' % _id)

                        self.page.browser.accounts_list.append(card)

                # Skip multi and expired cards
                if len(options) or len(page.doc.xpath('//span[@id="ERREUR"]')):
                    raise SkipItem()

                # 1 card : we have to check on another page to get id
                page = page.browser.open(Link('//form//a[text()="Contrat"]', default=None)(page.doc)).page
                xpath = '//table[has-class("liste")]/tbody/tr'
                active_card = CleanText('%s[td[text()="Active"]][1]/td[2]' % xpath, replace=[(' ', '')], default=None)(page.doc)

                if not active_card and len(page.doc.xpath(xpath)) != 1:
                    raise SkipItem()

                self.env['id'] = active_card or CleanText('%s[1]/td[2]' % xpath, replace=[(' ', '')])(page.doc)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|Plt|PRELEVEMENT) (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
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
    def go_on_history_tab(self):
        form = self.get_form(id='I1:fm')
        form['_FID_DoShowListView'] = ''
        form.submit()

    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[has-class("liste")]//thead//tr/th'
        item_xpath = '//table[has-class("liste")]//tbody/tr'

        class item(Transaction.TransactionElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 3 and len(self.el.xpath('./td[@class="i g" or @class="p g" or contains(@class, "_c1")]')) > 0

            class OwnRaw(Filter):
                def __call__(self, item):
                    el = TableCell('raw')(item)[0]

                    # Remove hidden parts of labels:
                    # hideifscript: Date de valeur XX/XX/XXXX
                    # fd: Avis d'opéré
                    # survey to add other regx
                    parts = (re.sub('Détail|Date de valeur\s+:\s+\d{2}/\d{2}(/\d{4})?', '', txt.strip()) for txt in el.itertext() if len(txt.strip()) > 0)
                    # Removing empty strings:
                    parts = [s for s in parts if s]
                    # To simplify categorization of CB, reverse order of parts to separate
                    # location and institution.
                    detail = "Cliquer pour déplier ou plier le détail de l'opération"
                    if detail in parts:
                        parts.remove(detail)
                    if parts[0].startswith('PAIEMENT CB'):
                        parts.reverse()

                    return ' '.join(parts)

            obj_raw = Transaction.Raw(OwnRaw())

    def find_amount(self, title):
        try:
            td = self.doc.xpath('//th[contains(text(), $title)]/../td', title=title)[0]
        except IndexError:
            return None
        else:
            return Decimal(FrenchTransaction.clean_amount(td.text))

    def get_coming_link(self):
        try:
            a = self.doc.xpath('//a[contains(text(), "Opérations à venir")]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['href']


class CardsOpePage(OperationsPage):
    def select_card(self, card_number):
        if CleanText('//select[@id="iso"]', default=None)(self.doc):
            form = self.get_form('//p[has-class("restriction")]')
            card_number = ' '.join([card_number[j*4:j*4+4] for j in range(len(card_number)//4+1)]).strip()
            form['iso'] = Attr('//option[text()="%s"]' % card_number, 'value')(self.doc)
            moi = Attr('//select[@id="moi"]/option[@selected]', 'value', default=None)(self.doc)
            if moi:
                form['moi'] = moi
            return self.browser.open(form.url, data=dict(form)).page
        return self

    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[has-class("liste")]//thead//tr/th'
        item_xpath = '//table[has-class("liste")]/tr'

        col_city = 'Ville'
        col_original_amount = "Montant d'origine"
        col_amount = 'Montant'

        class item(Transaction.TransactionElement):
            condition = lambda self: len(self.el.xpath('./td')) >= 5

            obj_raw = obj_label = Format('%s %s', TableCell('raw') & CleanText, TableCell('city') & CleanText)
            obj_original_amount = CleanDecimal(TableCell('original_amount'), default=NotAvailable, replace_dots=True)
            obj_original_currency = FrenchTransaction.Currency(TableCell('original_amount'))
            obj_type = Transaction.TYPE_DEFERRED_CARD
            obj_rdate = Transaction.Date(TableCell('date'))
            obj_date = obj_vdate = Env('date')
            obj__is_coming = Env('_is_coming')

            obj__gross_amount = CleanDecimal(Env('amount'), replace_dots=True)
            obj_commission = CleanDecimal(Format('-%s', Env('commission')), replace_dots=True, default=NotAvailable)

            def obj_amount(self):
                commission = Field('commission')(self)
                gross = Field('_gross_amount')(self)
                if empty(commission):
                    return gross
                return (abs(gross) - abs(commission)).copy_sign(gross)

            def parse(self, el):
                self.env['date'] = Date(Regexp(CleanText('//td[contains(text(), "Total prélevé")]'), ' (\d{2}/\d{2}/\d{4})', \
                                               default=NotAvailable), default=NotAvailable)(self)
                if not self.env['date']:
                    try:
                        d = CleanText('//select[@id="moi"]/option[@selected]')(self) or \
                            re.search('pour le mois de (.*)', ''.join(w.strip() for w in self.page.doc.xpath('//div[@class="a_blocongfond"]/text()'))).group(1)
                    except AttributeError:
                        d = Regexp(CleanText('//p[has-class("restriction")]'), 'pour le mois de ((?:\w+\s+){2})', flags=re.UNICODE)(self)
                    self.env['date'] = (parse_french_date('%s %s' % ('1', d)) + relativedelta(day=31)).date()
                self.env['_is_coming'] = date.today() < self.env['date']
                amount = CleanText(TableCell('amount'))(self).split('dont frais')
                self.env['amount'] = amount[0]
                self.env['commission'] = amount[1] if len(amount) > 1 else NotAvailable


class ComingPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table[has-class("liste")]//thead//tr/th/text()'
        item_xpath = '//table[has-class("liste")]//tbody/tr'

        col_date = u"Date de l'annonce"

        class item(Transaction.TransactionElement):
            obj__is_coming = True


class CardPage(OperationsPage, LoggedPage):
    def select_card(self, card_number):
        for option in self.doc.xpath('//select[@name="Data_SelectedCardItemKey"]/option'):
            card_id = Regexp(CleanText('.', symbols=' '), '([\dx]+)')(option)
            if card_id != card_number:
                continue
            if Attr('.', 'selected', default=None)(option):
                break

            form = self.get_form(id="I1:fm")
            form['_FID_DoChangeCardDetails'] = ""
            form['Data_SelectedCardItemKey'] = Attr('.', 'value')(option)
            return self.browser.open(form.url, data=dict(form)).page
        return self

    @method
    class get_history(Pagination, ListElement):
        class list_cards(ListElement):
            item_xpath = '//table[has-class("liste")]/tbody/tr/td/a'

            class item(ItemElement):
                def __iter__(self):
                    card_link = self.el.get('href')
                    page = self.page.browser.location(card_link).page

                    for op in page.get_history():
                        yield op

        class list_history(Transaction.TransactionsElement):
            head_xpath = '//table[has-class("liste")]//thead/tr/th'
            item_xpath = '//table[has-class("liste")]/tbody/tr'

            col_commerce = 'Commerce'
            col_ville = 'Ville'

            def condition(self):
                return not CleanText('//td[contains(., "Aucun mouvement")]', default=False)(self)

            def parse(self, el):
                label = CleanText('//*[contains(text(), "Achats")]')(el)
                if not label:
                    return
                try:
                    label = re.findall('(\d+ [^ ]+ \d+)', label)[-1]
                except IndexError:
                    return
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
                                       if CleanText('//a[contains(text(), "Prélevé fin")]', default=None) else Transaction.TYPE_CARD
                    self.env['differed_date'] = parse_french_date(Regexp(CleanText('//*[contains(text(), "Achats")]'), 'au[\s]+(.*)')(self)).date()
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


class LIAccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_li_accounts(ListElement):
        item_xpath = '//table[@class]/tbody/tr[count(td)>4]'

        class item(ItemElement):
            klass = Account

            load_details = Attr('.//a', 'href', default=NotAvailable) & AsyncLoad

            obj__link_id = Async('details', Link('//li/a[contains(text(), "Mouvements")]', default=NotAvailable))
            obj__link_inv = Link('./td[1]/a', default=NotAvailable)
            obj_id = CleanText('./td[2]', replace=[(' ', '')])
            obj_label = CleanText('./td[1]')
            obj_balance = CleanDecimal('./td[3]', replace_dots=True, default=NotAvailable)
            obj_currency = FrenchTransaction.Currency('./td[3]')
            obj__card_links = []
            obj_type = Account.TYPE_LIFE_INSURANCE
            obj__is_inv = True
            obj__card_number = None

    @method
    class iter_history(ListElement):
        item_xpath = '//table[has-class("liste")]/tbody/tr'

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
        item_xpath = '//table[has-class("liste")]/tbody/tr[count(td)>=7]'
        head_xpath = '//table[has-class("liste")]/thead/tr/th'

        col_label = 'Support'
        col_unitprice = re.compile(r"^Prix d'achat moyen")
        col_vdate = re.compile(r'Date de cotation')
        col_unitvalue = 'Valeur de la part'
        col_quantity = 'Nombre de parts'
        col_valuation = 'Valeur atteinte'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_unitprice = CleanDecimal(TableCell('unitprice', default=NotAvailable), default=NotAvailable, replace_dots=True)
            obj_vdate = Date(CleanText(TableCell('vdate'), replace=[('-', '')]), default=NotAvailable, dayfirst=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), default=NotAvailable, replace_dots=True)
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable, replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), default=Decimal(0), replace_dots=True)

            def obj_code(self):
                link = Link(TableCell('label')(self)[0].xpath('./a'), default=NotAvailable)(self)
                if not link:
                    return NotAvailable
                return Regexp(pattern='isin=([A-Z\d]+)&?', default=NotAvailable).filter(link)



class PorPage(LoggedPage, HTMLPage):
    TYPES = {"PLAN D'EPARGNE EN ACTIONS": Account.TYPE_PEA,
             'P.E.A': Account.TYPE_PEA
            }

    def get_type(self, label):
        for pattern, actype in self.TYPES.items():
            if label.startswith(pattern):
                return actype
        return Account.TYPE_MARKET

    def find_amount(self, title):
        return None

    def add_por_accounts(self, accounts):
        for ele in self.doc.xpath('//select[contains(@name, "POR_Synthese")]/option'):
            for a in accounts:
                # we have to create another account instead of just update it
                if a.id.startswith(ele.attrib['value']) and not a.balance:
                    a._is_inv = True
                    a.type = self.get_type(a.label)
                    self.fill(a)
                    break
            else:
                acc = Account()
                acc._card_number = None
                acc.id = ele.attrib['value']
                if acc.id == '9999':
                    # fake account
                    continue
                acc.label = unicode(re.sub("\d", '', ele.text).strip())
                acc._link_id = None
                acc.type = self.get_type(acc.label)
                acc._is_inv = True
                self.fill(acc)
                accounts.append(acc)

    def fill(self, acc):
        self.send_form(acc)
        ele = self.browser.page.doc.xpath('.//table[has-class("fiche bourse")]')[0]
        balance = CleanDecimal(ele.xpath('.//td[contains(@id, "Valorisation")]'), default=Decimal(0), replace_dots=True)(ele)
        acc.balance = balance + acc.balance if acc.balance else balance
        acc.valuation_diff = CleanDecimal(ele.xpath('.//td[contains(@id, "Variation")]'), default=Decimal(0), replace_dots=True)(ele)
        if balance:
            acc.currency = Currency('.//td[contains(@id, "Valorisation")]')(ele)
        else:
            # - Table element's textual content also contains dates with slashes.
            # They produce a false match when looking for the currency
            # (Slashes are matched with the Peruvian currency 'S/').
            # - The remaining part of the table textual may contain different
            # balances with their currencies though, so keep this part.
            #
            # Solution: remove the date
            text_content = CleanText('.')(ele)
            date_pattern = r"\d{2}/\d{2}/\d{4}"
            no_date = re.sub(date_pattern, '', text_content)
            acc.currency = Currency().filter(no_date)

    def send_form(self, account):
        form = self.get_form(name="frmMere")
        form['POR_SyntheseEntete1$esdselLstPor'] = re.sub('\D', '', account.id)
        form.submit()

    @method
    class iter_investment(TableElement):
        item_xpath = '//table[@id="bwebDynamicTable"]/tbody/tr[not(@id="LigneTableVide")]'
        head_xpath = '//table[@id="bwebDynamicTable"]/thead/tr/th/@abbr'

        col_label = 'Valeur'
        col_unitprice = re.compile('Prix de revient')
        col_unitvalue = 'Cours'
        col_quantity = 'Quantité / Montant nominal'
        col_valuation = 'Valorisation'
        col_diff = '+/- Value latente'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'), default=NotAvailable)
            obj_code = CleanText('.//td[1]/a/@title') & Regexp(pattern='^([^ ]+)')
            obj_quantity = CleanDecimal(TableCell('quantity'), default=Decimal(0), replace_dots=True)
            obj_unitprice = CleanDecimal(TableCell('unitprice'), default=Decimal(0), replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), default=Decimal(0), replace_dots=True)
            obj_diff = CleanDecimal(TableCell('diff'), default=Decimal(0), replace_dots=True)

            def obj_unitvalue(self):
                r = CleanText(TableCell('unitvalue'))(self)
                if r[-1] == '%':
                    return None
                else:
                    return CleanDecimal(TableCell('unitvalue'), default=Decimal(0), replace_dots=True)(self)

            def obj_vdate(self):
                td = TableCell('unitvalue')(self)[0]
                return Date(Regexp(Attr('./img', 'title', default=''), r'Cours au : (\d{2}/\d{2}/\d{4})\b', default=None), dayfirst=True, default=NotAvailable)(td)


class IbanPage(LoggedPage, HTMLPage):
    def fill_iban(self, accounts):

        # Old website
        for ele in self.doc.xpath('//table[has-class("liste")]/tr[@class]/td[1]'):
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
        for ele in self.doc.xpath('//table[has-class("liste")]//tr[not(@class)]/td[1]'):
            for a in accounts:
                if a.id.split('EUR')[0] in CleanText('.//em[2]', replace=[(' ', '')])(ele):
                    a.iban = CleanText('.//em[2]', replace=[(' ', '')])(ele)


class MyRecipient(ItemElement):
    klass = Recipient

    obj_currency = 'EUR'
    obj_label = CleanText('.//div[@role="presentation"]/em | .//div[not(@id) and not(@role)]')

    def obj_enabled_at(self):
        return datetime.now().replace(microsecond=0)

    def validate(self, el):
        return not el.iban or is_iban_valid(el.iban)


class InternalTransferPage(LoggedPage, HTMLPage):
    RECIPIENT_STRING = 'data_input_indiceCompteACrediter'
    READY_FOR_TRANSFER_MSG = 'Confirmer un virement entre vos comptes'
    SUMMARY_RECIPIENT_TITLE = 'Compte à créditer'
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

            obj_bank_name = 'Crédit Mutuel'
            obj_label = CleanText('.//div[@role="presentation"]/em | .//div[not(@id) and not(@role)]')
            obj_id = CleanText('.//span[@class="_c1 doux _c1"]', replace=[(' ', '')])
            obj_category = 'Interne'

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
        content = self.text
        messages = ['Le montant du virement doit être positif, veuillez le modifier',
                    'Montant maximum autorisé au débit pour ce compte',
                    'Dépassement du montant journalier autorisé',
                    'Le solde de votre compte est insuffisant',
                    'Nom prénom du bénéficiaire différent du titulaire. Utilisez un compte courant',
                    "Pour effectuer cette opération, vous devez passer par l’intermédiaire d’un compte courant",
                    'Montant maximum autorisé au crédit pour ce compte',
                    'Débit interdit sur ce compte']

        for message in messages:
            if message in content:
                if self.doc.xpath('//div[@class="blocmsg err"]/p'):
                    # get full error message
                    message = CleanText('//div[@class="blocmsg err"]/p')(self.doc)
                raise TransferBankError(message=message)

    def check_success(self):
        # look for the known "all right" message
        if not self.doc.xpath('//span[contains(text(), $msg)]', msg=self.READY_FOR_TRANSFER_MSG):
            raise TransferError('The expected message "%s" was not found.' % self.READY_FOR_TRANSFER_MSG)

    def check_data_consistency(self, account_id, recipient_id, amount, reason):
        assert account_id in CleanText('//div[div[p[contains(text(), "Compte à débiter")]]]', replace=[(' ', '')])(self.doc)
        assert recipient_id in CleanText('//div[div[p[contains(text(), "%s")]]]' % self.SUMMARY_RECIPIENT_TITLE, replace=[(' ', '')])(self.doc)

        exec_date = Date(Regexp(CleanText('//table[@summary]/tbody/tr[th[contains(text(), "Date")]]/td'), '(\d{2}/\d{2}/\d{4})'), dayfirst=True)(self.doc)
        assert exec_date == datetime.today().date()
        r_amount = CleanDecimal('//table[@summary]/tbody/tr[th[contains(text(), "Montant")]]/td', replace_dots=True)(self.doc)
        assert r_amount == Decimal(amount)
        currency = FrenchTransaction.Currency('//table[@summary]/tbody/tr[th[contains(text(), "Montant")]]/td')(self.doc)
        if reason is not None:
            assert reason.upper().strip()[:22] in CleanText('//table[@summary]/tbody/tr[th[contains(text(), "Intitulé pour le compte à débiter")]]/td')(self.doc)
        return exec_date, r_amount, currency

    def handle_response(self, account, recipient, amount, reason):
        self.check_errors()
        self.check_success()

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
        self.check_errors()
        # look for the known "everything went well" message
        content = self.text
        transfer_ok_message = ['Votre virement a &#233;t&#233; ex&#233;cut&#233;',
                               'Ce virement a &#233;t&#233; enregistr&#233; ce jour',
                               'Ce virement a été enregistré ce jour']
        if not any(msg for msg in transfer_ok_message if msg in content):
            raise TransferError('The expected message "%s" was not found.' % transfer_ok_message)

        exec_date, r_amount, currency = self.check_data_consistency(transfer.account_id, transfer.recipient_id, transfer.amount, transfer.label)

        state = CleanText('//table[@summary]/tbody/tr[th[contains(text(), "Etat")]]/td')(self.doc)
        valid_states = ('Exécuté', 'Soumis')

        # tell user that transfer was done even though it wasn't done is better
        # than tell users that transfer state is bug even though it was done
        for valid_state in valid_states:
            if valid_state in state:
                break
        else:
            raise TransferError('Transfer state is %r' % state)

        assert transfer.amount == r_amount
        assert transfer.exec_date == exec_date
        assert transfer.currency == currency

        return transfer


class ExternalTransferPage(InternalTransferPage):
    RECIPIENT_STRING = 'data_input_indiceBeneficiaire'
    READY_FOR_TRANSFER_MSG = 'Confirmer un virement vers un bénéficiaire enregistré'
    SUMMARY_RECIPIENT_TITLE = 'Bénéficiaire à créditer'

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
                return self.env['category'] if 'category' in self.env else 'Externe'

            def obj_id(self):
                if self.page.IS_PRO_PAGE:
                    return CleanText('(.//span[@class="_c1 doux _c1"])[1]', replace=[(' ', '')])(self.el)
                else:
                    return CleanText('.//span[@class="_c1 doux _c1"]', replace=[(' ', '')])(self.el)

            def obj_iban(self):
                return Field('id')(self)

            def parse(self, el):
                self.env['origin_account']._external_recipients.add(Field('id')(self))


class VerifCodePage(LoggedPage, HTMLPage):
    HASHES = {
        ('c5aa0990f26b7ab94b956ca4a8f32620', '1a34be567967c34d53ef2ba73715d481'): 'A1',
        ('dc2e60c9ea7e8a4076f2ced9a0764c3c', '6fe82ee8a1ebe352f15e950abf248120'): 'A2',
        ('2c2842278e250204c16376a0efab5a95', '764e59ca04057aae0466cf0bc4f27a01'): 'A3',
        ('62b3987e9f1322bfdff6d5dc0b38db08', '599cd1197e50c7380db35f35e2b508c9'): 'A4',
        ('4d3bc686ee24c909cf3e513b315b5551', 'a41d16429734249f25b8426b4e4c641e'): 'A5',
        ('54c44d50e8ad2ce142d3116c24de3846', '6715d118267ab4af827f3a4b3a8f87fc'): 'A6',
        ('d079635c75592592f8fba617ba96f781', '48d84f64e4e696571b1f8109c97a7a7b'): 'A7',
        ('89b084012994c80ba29fd59ae759a9c1', '0dc1676008e0dd73a82ecedfc57e1ed1'): 'A8',
        ('4850adcdee0b34d2c496ae9512790422', 'a22ac030922232d72e4544885c931c4c'): 'B1',
        ('ecf777518d4ba4c84bc3784b53e33279', 'a10c7138295d2dddaa5cc46a96b3f874'): 'B2',
        ('bcbd6ff41afc246fa3c9d89ef1d7c8ba', '28b8d78bd89d46c0fd23f2969ba4bd36'): 'B3',
        ('ef70cdd8973f051c73027dddcf2905e0', 'f445c1ff3ed090a6582385901b72a590'): 'B4',
        ('76167582ad6272b7b2ccce1f218f1b68', '2b37f61aa64cb8c9eaaaa40a3cb7dd9d'): 'B5',
        ('2e42ff3e319b7788f40b8494b06d2e7f', 'aee9142703a64e4286388f5bb7b37ab0'): 'B6',
        ('fc379f6d576b803d20d23c143404b27b', '4ddea67432645a269634d28312cde6ff'): 'B7',
        ('e7b1bc375f6a2f022fc97d25345c275f', '6dcceade2fcbbff131ce39331aca0302'): 'B8',
        ('00cb13da73d8759dce3b1efa3c9073ed', '9cb3e55fe6e7287fdfe66ad335a99657'): 'C1',
        ('a7a60cfa11ac35f69e833e6993f4d620', 'afa19495194aa130cb0226101d2c1ecf'): 'C2',
        ('c391e1da87e22e4ffdc8e864285e858b', 'f8654ed4cf9b1c40da216ccc981e5328'): 'C3',
        ('a8b9b55786955656d4dcf3e1fda79865', 'a0f90e50d2b18e672693d325c61cd08f'): 'C4',
        ('d4a1ad08f9b43acb84b10bf8715b0cc6', '3db3f9c8b223c9aecb272e67c0548437'): 'C5',
        ('aea1cab2813ee28a00590f331b5dc148', 'b49628a46a50423afe8568763df373b3'): 'C6',
        ('cd9dfa746761b5b03384eb8988a77189', 'c2de8d8c1f2988e19474ce2ccda7aac6'): 'C7',
        ('81f95a02a90cadfbd555ba4b7e3d2203', '969db1200abdbcaa38c477fffbd16ac1'): 'C8',
        ('a7ddf5e4033fab294bba4a3abb1b7db4', 'a02376697a5f5bc3364a157209846c68'): 'D1',
        ('df6352fd5eeda71fd3fe49c6523f93ae', '80eae27b7225dd1141687a01a0b91a52'): 'D2',
        ('185ad70f321b901aa4a53f4364e747f5', '3f0ce53ac49085d9b161c7d6133510ff'): 'D3',
        ('6caf4a58ccf5e873a30c47e5ec56761e', '5c54e59cec34b2a4542c62ca7fc95e1f'): 'D4',
        ('3e63d6517b934c2f56a326d167040609', '5f082bc1949f359cf514e016a5a60fec'): 'D5',
        ('6703817598ecc33e12f285af111dee2e', '1dabb2b992d7d33d7b338d21f0bca026'): 'D6',
        ('cec8a1b5a815575b3ff549b63d7af98c', '382bfbb7bfe679fcf0f17dfdd330a7d5'): 'D7',
        ('3362f25f5b2cc5c5e0bdb09cd179bda0', '915971387e7125caddd19b134d250413'): 'D8',
        ('e2701343f157fc4ac5e47263b9b8663e', '8786bd17b43fc0f70f3595374dc16d71'): 'E1',
        ('2ee0dfbd7d34a415f87482f7ccd6fd36', '122762a913c28d26ac879ce8e1193340'): 'E2',
        ('112c85cfccf6a5fc7d925cc01572a041', 'f00fb7afd16c9ce7c1c3b1cf597fd775'): 'E3',
        ('809d68e42776c0a9f4b68e68c68fffd3', 'b7d54cd0c6feeb81dd3334b60db60402'): 'E4',
        ('af996f7e536f6fc905b92ab7c1c33d31', 'af9a53c2bcda08d26c68f1a98b8e7cd6'): 'E5',
        ('9e694194e4c16771d2d90085c0edbbd3', '5f7fb45d3b67dfeddeb7b9e6db633e30'): 'E6',
        ('e49c03811ce80bb5dec6df7dc817f545', '9260cb4ee31cbf8171c2b4ed125c7029'): 'E7',
        ('da4398cc81d9399dc0b1aebdf554dc9c', 'b5f61e3816a6c2e4e4dce47415e2d5cc'): 'E8',
        ('9fc496cc4d416fd53eda938d8643b9f4', '7177915e2a661e4c8202e96f0ea1a0d1'): 'F1',
        ('77ada5bfbeb73d0c77acd7d0d1ab50b4', '5688f91980bb7ad01c3c55eea4eeb79e'): 'F2',
        ('03837ab975dee769a3fc4418a9b27184', 'a3269c9f223dc4fde1b42dcc4c84f222'): 'F3',
        ('a68defaa9b8b6f9f63c337dc91f0af0f', '64c1f2fa82e0273a5821e4c8ae4f20f8'): 'F4',
        ('deaec96b46cd269b125705a50bc7db78', '8c5336120496f045689e61b0698d3b26'): 'F5',
        ('6cc495fa739c998320623e10b1a7a832', '8e92a39f5b115d3f583d23f6fe23b637'): 'F6',
        ('ed97b23f70d1ae7b22a89b14554c0df1', '993f2c8dd975541abfd90e067ef83f05'): 'F7',
        ('dc67341a14c5495d4422ee7b766a3d6d', 'b9e6e9b37ab35bc1d171d106bb20ae24'): 'F8',
        ('39a5e6807e9c10a1777fca5ab2d97f99', '78be55d32a664162065a0749437ed494'): 'G1',
        ('114f9c8d5440f6e31dd151b5f6c7b0d5', '64704aa9e54b3a666aaa415f97be48fb'): 'G2',
        ('d77bb8c4161b59186f038b4f3c2c7a7c', '2e1260ce780c906fa73718216c86371e'): 'G3',
        ('912d2bc8d64f6c87971a76e0a6d4d04c', 'a12629927ef319a9621db9a915862940'): 'G4',
        ('de00ec70d550474359fe671e8eada3c1', 'c609aca9677b37e499437e32a2ab3ee5'): 'G5',
        ('5a8211709a85604d1e01465f9e0e8440', '4ad2fe1572cebfede774bd815c5f8879'): 'G6',
        ('509e7acaad0ab886116a64798332bd68', 'c143e43dfbaac43e6324960892a77e0c'): 'G7',
        ('46ac73377b08712a1bbe297d5f3a51f3', 'cb937faa00e5c7f61bf05ae50193409d'): 'G8',
        ('bc288cbfa82b119c508cf4fbcfe75a6e', '1532e66e91cecf527733645f81a40d2e'): 'H1',
        ('6a8f5a82419fed29eeb8bd439a109920', '5a1f282e02cfe1aaf0db5511a9a6cdde'): 'H2',
        ('36ad9e845c7a6ca642b0021c3b2cef2c', '2cc8bfeea91f8d2be5af3a3671611a33'): 'H3',
        ('0124561f987c77a5118abe6b5b1a56d5', 'b511e98b398ba2e9c809d3f3e1ca66a8'): 'H4',
        ('d20f5baef6301de18cc0ffed06806f18', '5c31d4554b0159727acb6402f9dd6975'): 'H5',
        ('004c7a4ec9ad6fdcf1723269c6e78c6c', '9d407d3aad2b904f9bdc056801cbba3e'): 'H6',
        ('54b06cc669a176693649076c87eb1239', '88113a9fa2c104d1a85d6aad96d022ac'): 'H7',
        ('d5a615cd08d558cee1f2feaa4fb92785', '6028e69c33007466fdb137935941958d'): 'H8',
        }

    def on_load(self):
        error = CleanText('//p[contains(text(), "Clé invalide !")] | //p[contains(text(), "Vous n\'avez pas saisi de clé!")]')(self.doc)
        if error:
            raise AddRecipientError(message=error)

        action_needed = CleanText('//p[contains(text(), "Carte de CLÉS PERSONNELLES révoquée")]')(self.doc)
        if action_needed:
            raise ActionNeeded(action_needed)

    def get_key_case(self, _hash):
        for h, v in self.HASHES.items():
            if h == _hash or _hash in h:
                return v

    def get_question(self):
        s = CleanText('//label[@for="txtCle"]')(self.doc)
        img_hash_md5 = hashlib.md5(self.browser.open(Attr('//label[@for="txtCle"]/img', 'src')(self.doc)).content).hexdigest()
        key_case = self.get_key_case(img_hash_md5)
        assert key_case, "Hash %s not found, matching key case is available on session folder." % img_hash_md5
        return s[:25] + ' %s' % key_case + s[25:]

    def post_code(self, key):
        form = self.get_form(id='frm')
        form['code'] = key
        form['valChx.x'] = '1'
        form['valChx.y'] = '1'
        form.submit()


class RecipientsListPage(LoggedPage, HTMLPage):
    def on_load(self):
        txt = CleanText('//em[contains(text(), "Protection de vos opérations en ligne")]')(self.doc)
        if txt:
            self.browser.location(Link('//div[@class="blocboutons"]//a')(self.doc))

        error = CleanText('//div[@class="blocmsg err"]/p')(self.doc)
        if error and error != 'Veuillez renseigner le BIC ou les coordonnées de la banque':
            # don't reload state if it fails because it's not supported by the website
            self.browser.need_clear_storage = True
            raise AddRecipientError(message=error)

        app_validation = self.doc.xpath('//strong[contains(text(), "Démarrez votre application mobile Crédit Mutuel")]')
        if app_validation:
            # don't reload state if it fails because it's not supported by the website
            self.browser.need_clear_storage = True
            raise AuthMethodNotImplemented("La confirmation par validation sur votre application mobile n'est pas supportée")

    def has_list(self):
        return bool(CleanText('//th[contains(text(), "Listes pour virements ordinaires")]')(self.doc))

    def get_recipients_list(self):
        return [CleanText('.')(a) for a in self.doc.xpath('//tr[td[has-class("a_actions")]]//a[@title="Afficher le bénéficiaires de la liste"]')]

    def go_list(self, category):
        form = self.get_form(id='P1:F', submit='//input[@value="%s"]' % category)
        del form['_FID_DoAjoutListe']
        form.submit()

    def go_to_add(self):
        form = self.get_form(id='P1:F', submit='//input[@value="Ajouter"]')
        form.submit()

    def get_add_recipient_form(self, recipient):
        form = self.get_form(id='P:F')
        del form['_FID_GoI%5fRechercheBIC']
        form['[t:dbt%3astring;x(70)]data_input_nom'] = recipient.label
        form['[t:dbt%3astring;x(34)]data_input_IBANBBAN'] = recipient.iban
        form['_FID_DoValidate'] = ''

        # Needed because it requires that \xe9 is encoded %E9 instead of %C3%A9
        try:
            del form[u'data_pilotageAffichage_habilitéSaisieInternationale']
        except KeyError:
            pass
        else:
            form[b'data_pilotageAffichage_habilit\xe9SaisieInternationale'] = ''
        return form

    def add_recipient(self, recipient):
        form = self.get_add_recipient_form(recipient)
        form.submit()

    def bic_needed(self):
        error = CleanText('//div[@class="blocmsg err"]/p')(self.doc)
        if error == 'Veuillez renseigner le BIC ou les coordonnées de la banque':
            return True

    def set_browser_form(self, form):
        self.browser.form = dict((k, v) for k, v in form.items() if v)
        self.browser.form['url'] = form.url
        self.browser.page = None
        self.browser.logged = 1

    def ask_bic(self, recipient):
        form = self.get_add_recipient_form(recipient)
        self.set_browser_form(form)
        raise AddRecipientStep(recipient, Value('Bic', label='Veuillez renseigner le BIC'))

    def ask_sms(self, recipient):
        txt = CleanText('//span[contains(text(), "Pour confirmer votre opération, indiquez votre ")]')(self.doc)
        if txt:
            form = self.get_form(id='P:F')
            self.set_browser_form(form)
            raise AddRecipientStep(recipient, Value('code', label=txt))
        # don't reload state if it fails because it's not supported by the website
        self.browser.need_clear_storage = True
        raise AddRecipientError('Was expecting a page where sms code is asked')

class RevolvingLoansList(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//tbody/tr'
        flush_at_end = True

        class item_account(ItemElement):
            klass = Loan

            obj_id = Regexp(Attr('.//a','href'), r'(\d{16})\d{2}$')
            obj_label = CleanText('.//td[2]')
            obj_total_amount = MyDecimal('.//td[3]')
            obj_currency = FrenchTransaction.Currency(CleanText('.//td[3]'))
            obj_type = Account.TYPE_REVOLVING_CREDIT
            obj__is_inv = False
            obj__link_id = None

            load_details = Link('.//a') & AsyncLoad
            obj_balance = Async('details') & MyDecimal(
                Format('-%s',CleanText('//main[@id="ei_tpl_content"]/div/div[2]/table//tr[2]/td[1]')))
            obj_available_amount = Async('details') & MyDecimal('//main[@id="ei_tpl_content"]/div/div[2]/table//tr[3]/td[1]')

            def condition(self):
                return CleanText('.//a', default=None)(self)

class ErrorPage(HTMLPage):
    def on_load(self):
        error = CleanText('//td[@class="ALERTE"]')(self.doc)
        if error:
            raise BrowserUnavailable(error)

class RevolvingLoanDetails(LoggedPage, HTMLPage):
    pass


class SubscriptionPage(LoggedPage, HTMLPage):
    def submit_form(self, subscriber):
        form = self.get_form(id='frmDoc')
        form['SelTiers'] = subscriber
        form.submit()

    def get_subscriptions(self, subscription_list, subscriber=None):
        for account in self.doc.xpath('//table[@class="liste"]//tr//td[contains(text(), "Compte")]'):
            sub = Subscription()
            sub.id = Regexp(CleanText('.', replace=[('.', ''), (' ', '')]), r'(\d+)')(account)

            if find_object(subscription_list, id=sub.id):
                continue

            sub.label = CleanText('.')(account)

            if subscriber != None:
                sub.subscriber = CleanText('.')(subscriber)
            else:
                sub.subscriber = CleanText('//span[@id="NomTiers"]')(self.doc)

            subscription_list.append(sub)
            yield sub

    def iter_subscriptions(self):
        subscription_list = []

        options = self.doc.xpath('//select[@id="SelTiers"]/option')
        if options:
            for opt in options:
                subscriber = self.doc.xpath('//select[@id="SelTiers"]/option[contains(text(), "%s")]' % CleanText('.')(opt))[0]
                self.submit_form(Attr('.', 'value')(subscriber))
                for sub in self.get_subscriptions(subscription_list, subscriber):
                    yield sub
        else:
            for sub in self.get_subscriptions(subscription_list):
                yield sub

    @method
    class iter_documents(TableElement):
        item_xpath = '//table[caption[contains(text(), "Extraits de comptes")]]//tr[td]'
        head_xpath = '//table[@class="liste"]//th'

        col_date = 'Date'
        col_label = 'Information complémentaire'
        col_url = 'Nature du document'

        class item(ItemElement):
            def condition(self):
                return Env('sub_id')(self) == Regexp(CleanText(TableCell('label'), replace=[('.', ''), (' ', '')]), r'(\d+)')(self)

            klass = Document

            # Some documents may have the same date, name and label; only parts of the PDF href may change,
            # so we must pick a unique ID including the href to avoid document duplicates:
            obj_id = Format('%s_%s_%s', Env('sub_id'), CleanText(TableCell('date'), replace=[('/', '')]), Regexp(Field('url'), r'NOM=(.*)&RFL='))
            obj_label = Format('%s %s', CleanText(TableCell('url')), CleanText(TableCell('date')))
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_format = 'pdf'
            obj_type = 'other'

            def obj_url(self):
                return urljoin(self.page.url, '/fr/banque/%s' % Link('./a')(TableCell('url')(self)[0]))

    def next_page(self):
        form = self.get_form(id='frmDoc')
        form['__EVENTTARGET'] = ''
        form['__EVENTARGUMENT'] = ''
        form['__LASTFOCUS'] = ''
        form['SelIndex1'] = ''
        form['NEXT.x'] = '7'
        form['NEXT.y'] = '8'
        form.submit()

    def is_last_page(self):
        if self.doc.xpath('//td[has-class("ERREUR")]'):
            return True
        if re.search(r'(\d\/\d)', CleanText('//div[has-class("blocpaginb")]', symbols=' ')(self.doc)):
            return True
        return False
