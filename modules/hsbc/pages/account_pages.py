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

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.compat import urlparse, parse_qs, urljoin
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.filters.standard import (
    Filter, Env, CleanText, CleanDecimal, Field, DateGuesser, Regexp
)
from weboob.browser.filters.html import Link, AbsoluteLink, TableCell
from weboob.browser.filters.javascript import JSVar

from .landing_pages import GenericLandingPage


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile(r'^CB (?P<text>.*?)\s+(?P<dd>\d+)/(?P<mm>[01]\d)\s*(?P<loc>.*)'),
                                                           FrenchTransaction.TYPE_CARD),
                (re.compile(r'^DAB (?P<dd>\d{2})/(?P<mm>\d{2}) ((?P<HH>\d{2})H(?P<MM>\d{2}) )?(?P<text>.*?)( CB N°.*)?$'),
                                                           FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(r'^CHEQUE( \d+)?$'),           FrenchTransaction.TYPE_CHECK),
                (re.compile(r'^COTIS\.? (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile(r'^REMISE (?P<text>.*)'),      FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^FACTURES CB (?P<text>.*)'), FrenchTransaction.TYPE_CARD_SUMMARY),
                ]


class FrameContainer(GenericLandingPage):
    is_here = '//frameset'

    # main page, a frameset
    def on_load(self):
        txt = CleanText('//p[@class="debit"]', default='')(self.doc)
        if u"Vos données d'identification (identifiant - code secret) sont incorrectes" in txt:
            raise BrowserIncorrectPassword()

    def get_js_url(self):
        # look for frame url in the top page
        return urljoin(self.url, JSVar(CleanText('//script'), var='url')(self.doc))

    def get_frame(self):
        try:
            a = self.doc.xpath(u'//frame["@name=FrameWork"]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['src']


class UnavailablePage(GenericLandingPage):
    is_here = '//strong[contains(text(),"Service momentanément indisponible.")]'

    def on_load(self):
        raise BrowserUnavailable()


class AccountsPage(GenericLandingPage):
    is_here = '//h1[text()="Synthèse"]'

    @method
    class iter_accounts(ListElement):
        item_xpath = '//tr'
        flush_at_end = True

        class item(ItemElement):
            klass = Account

            def condition(self):
                return len(self.el.xpath('./td')) > 2

            class Label(Filter):
                def filter(self, text):
                    return text.lstrip(' 0123456789').title()

            class Type(Filter):
                PATTERNS = [
                    ('c.aff', Account.TYPE_CHECKING),
                    ('pea', Account.TYPE_PEA),
                    ('invest', Account.TYPE_MARKET),
                    ('ptf', Account.TYPE_MARKET),
                    ('ldd', Account.TYPE_SAVINGS),
                    ('cel', Account.TYPE_SAVINGS),
                    ('pel', Account.TYPE_SAVINGS),
                    ('livret', Account.TYPE_SAVINGS),
                    ('livjeu', Account.TYPE_SAVINGS),
                    ('compte', Account.TYPE_CHECKING),
                    ('cpte', Account.TYPE_CHECKING),
                    ('scpi', Account.TYPE_MARKET),
                    ('account', Account.TYPE_CHECKING),
                    ('pret', Account.TYPE_LOAN),
                    ('vie', Account.TYPE_LIFE_INSURANCE),
                    ('strategie patr.', Account.TYPE_LIFE_INSURANCE),
                    ('essentiel', Account.TYPE_LIFE_INSURANCE),
                    ('elysee', Account.TYPE_LIFE_INSURANCE),
                    ('abondance', Account.TYPE_LIFE_INSURANCE),
                    ('ely. retraite', Account.TYPE_LIFE_INSURANCE),
                    ('lae option assurance', Account.TYPE_LIFE_INSURANCE),
                    ('carte ', Account.TYPE_CARD),
                    ('plan assur. innovat.', Account.TYPE_LIFE_INSURANCE),
                    ('hsbc evol pat transf', Account.TYPE_LIFE_INSURANCE),
                    ('bourse libre', Account.TYPE_MARKET),
                ]

                def filter(self, label):
                    label = label.lower()
                    for pattern, type in self.PATTERNS:
                        if pattern in label:
                            return type
                    return Account.TYPE_UNKNOWN

            obj_label = Label(CleanText('./td[1]/a'))
            obj_coming = Env('coming')
            obj_currency = FrenchTransaction.Currency('./td[2]')

            obj_url = CleanText(AbsoluteLink('./td[1]/a'), replace=[('\n', '')])

            obj_type = Type(Field('label'))
            obj_coming = NotAvailable

            @property
            def obj_balance(self):
                if self.el.xpath('./parent::*/tr/th') and self.el.xpath('./parent::*/tr/th')[0].text in [u'Credits', u'Crédits']:
                    return CleanDecimal(replace_dots=True, sign=lambda x: -1).filter(self.el.xpath('./td[3]'))
                return CleanDecimal(replace_dots=True).filter(self.el.xpath('./td[3]'))

            @property
            def obj_id(self):
                # Investment account and main account can have the same id
                # so we had account type in case of Investment to prevent conflict
                # and also the same problem with scpi accounts.
                if "Scpi" in Field('label')(self):
                    return CleanText(replace=[('.', ''), (' ', '')]).filter(self.el.xpath('./td[2]')) + ".SCPI"
                if Field('type')(self) == Account.TYPE_MARKET:
                    return CleanText(replace=[('.', ''), (' ', '')]).filter(self.el.xpath('./td[2]')) + ".INVEST"
                return CleanText(replace=[('.', ''), (' ', '')]).filter(self.el.xpath('./td[2]'))


class RibPage(GenericLandingPage):
    def is_here(self):
        return bool(self.doc.xpath('//h1[contains(text(), "RIB/IBAN")]'))

    def link_rib(self, accounts):
        for id, acc in accounts.items():
            if acc.iban or acc.type is not Account.TYPE_CHECKING:
                continue
            digit_id = ''.join(re.findall('\d', id))
            if digit_id in CleanText('//div[@class="RIB_content"]')(self.doc):
                acc.iban = re.search('(FR\d{25})', CleanText('//div[strong[contains(text(), "IBAN")]]', replace=[(' ', '')])(self.doc)).group(1)

    def get_rib(self, accounts):
        self.link_rib(accounts)
        for nb in range(len(self.doc.xpath('//select/option')) - 1):
            form = self.get_form(name="FORM_RIB")
            form['index_rib'] = str(nb+1)
            form.submit()
            self.browser.page.link_rib(accounts)


class Pagination(object):
    def next_page(self):
        links = self.page.doc.xpath('//a[@class="fleche"]')
        if len(links) == 0:
            return
        current_page_found = False
        for link in links:
            l = link.attrib.get('href')
            if current_page_found and "#op" not in l:
                # Adding CB_IdPrestation so browser2 use CBOperationPage
                return l + "&CB_IdPrestation"
            elif "#op" in l:
                current_page_found = True
        return


class CBOperationPage(GenericLandingPage):
    is_here = '//h1[text()="Historique des opérations"]'

    def get_params(self, url):
        parsed = urlparse(url)
        base_url, params = parsed.path, parse_qs(parsed.query)
        for a in self.doc.xpath('//form[@name="FORM_LIB_CARTE"]//a[contains(@href, "sessionid")]'):
            params['sessionid'] = parse_qs(urlparse(Link('.')(a)).query)['sessionid']
            yield base_url, params

    @pagination
    @method
    class get_history(Pagination, Transaction.TransactionsElement):
        head_xpath = '//table//tr/th'
        item_xpath = '//table//tr'

        class item(Transaction.TransactionElement):
            def condition(self):
                return len(self.el.xpath('./td')) >= 4

            obj_rdate = Transaction.Date(TableCell('date'))

            def obj_date(self):
                return DateGuesser(Regexp(CleanText(self.page.doc.xpath('//table/tr[2]/td[1]')), r'(\d{2}/\d{2})'), Env("date_guesser"))(self)

    def get_parent_id(self):
        # The parent id is in the details of the card
        m = re.search(r'Solde du compte (.*)', CleanText('//div[@class="RecentTransactions"]/h2')(self.doc))
        return m.group(1)


class CPTOperationPage(GenericLandingPage):
    is_here = '''//h1[text()="Historique des opérations"] and //h2[text()="Recherche d'opération"]'''

    def get_history(self):
        if self.doc.xpath('//form[@name="FORM_SUITE"]'):
            m = re.search('suite[\s]+=[\s]+([\w]+)', CleanText().filter(self.doc.xpath('//script[contains(text(), "var suite")]')))
            if m and m.group(1) == "true":
                form = self.get_form(name="FORM_SUITE")
                self.doc = self.browser.location("%s" % form.url, params=dict(form)).page.doc

        for script in self.doc.xpath('//script'):
            if script.text is None or script.text.find('\nCL(0') < 0:
                continue

            first_history = None
            for m in re.finditer(r"CL\((\d+),'(.+)','(.+)','(.+)','([\d -\.,]+)',('([\d -\.,]+)',)?'\d+','\d+','[\w\s]+'\);", script.text, flags=re.MULTILINE | re.UNICODE):
                op = Transaction()
                raw = re.sub(u'[ ]+', u' ', m.group(4).replace(u'\n', u' ').replace(r"\'", "'"))
                op.parse(date=m.group(3), raw=raw)
                op.set_amount(m.group(5))
                op._coming = (re.match(r'\d+/\d+/\d+', m.group(2)) is None)
                if first_history is None:
                    first_history = op.to_dict()
                elif first_history == op.to_dict():
                    self.logger.warning("Find already used line {}".format(first_history))
                    break
                yield op


class AppGonePage(HTMLPage):
    def on_load(self):
        self.browser.app_gone = True
        self.logger.info('Application has gone. Relogging...')
        self.browser.do_logout()
        self.browser.do_login()


class LoginPage(HTMLPage):
    @property
    def logged(self):
        if self.doc.xpath(u'//p[contains(text(), "You are now being redirected to your Personal Internet Banking.")]'):
            return True
        return False

    def on_load(self):
        for message in self.doc.xpath('//div[has-class("csPanelErrors")]'):
            error_msg = CleanText('.')(message)
            if any(msg in error_msg for msg in ['Please enter valid credentials for memorable answer and password.',
                                                'mot de passe invalide']):
                raise BrowserIncorrectPassword(error_msg)
            else:
                raise BrowserUnavailable(error_msg)

    def is_here(self):
        return not self.doc.xpath('//form[@name="launch"]')

    def login(self, login):
        form = self.get_form(id='idv_auth_form')
        form['userid'] = form['__hbfruserid'] = login
        form.submit()

    def get_no_secure_key(self):
        try:
            a = self.doc.xpath(u'//a[contains(text(), "Without HSBC Secure Key")]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['href']

    def login_w_secure(self, password, secret):
        form = self.get_form(nr=0)
        form['memorableAnswer'] = secret
        inputs = self.doc.xpath(u'//input[starts-with(@id, "keyrcc_password_first")]')
        split_pass = u''
        if len(password) < len(inputs):
            raise BrowserIncorrectPassword('The password must be at least %d characters' % len(inputs))
        elif len(password) > len(inputs):
            # HSBC only use 6 first and last two from the password
            password = password[:6] + password[-2:]

        for i, inpu in enumerate(inputs):
            # The good field are 1,2,3 and the bad one are 11,12,21,23,24,31 and so one
            if int(inpu.attrib['id'].split('first')[1]) < 10:
                split_pass += password[i]
        form['password'] = split_pass
        form.submit()

    def useless_form(self):
        form = self.get_form(nr=0)
        # There is space added at the end of the url
        form.url = form.url.rstrip()
        form.submit()


class OtherPage(HTMLPage):
    ERROR_CLASSES = [
        ('Votre contrat est suspendu', ActionNeeded),
        ("Vos données d'identification (identifiant - code secret) sont incorrectes", BrowserIncorrectPassword),
        ('Erreur : Votre contrat est clôturé.', ActionNeeded),
    ]

    def on_load(self):
        for msg, exc in self.ERROR_CLASSES:
            for tag in self.doc.xpath('//p[@class="debit"]//strong[text()[contains(.,$msg)]]', msg=msg):
                raise exc(CleanText('.')(tag))
