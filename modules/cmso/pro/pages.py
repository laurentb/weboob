# -*- coding: utf-8 -*-

# Copyright(C) 2014      smurail
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.pages import HTMLPage, JsonPage, pagination
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, DateGuesser, Env, Field, Filter, Regexp, Currency, Date
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.compat import urljoin, parse_qsl
from weboob.tools.capabilities.bank.investments import is_isin_valid


__all__ = ['LoginPage']


class UselessPage(HTMLPage):
    pass


class PasswordCreationPage(HTMLPage):
    def get_message(self):
        xpath = '//div[@class="bienvenueMdp"]/following-sibling::div'
        return '%s%s' % (CleanText(xpath + '/strong')(self.doc), CleanText(xpath, children=False)(self.doc))


class ChoiceLinkPage(HTMLPage):
    def on_load(self):
        link_line = self.doc.xpath('//script')[-1].text
        m = re.search(r'lien\("(.*)"', link_line)
        if m:
            self.browser.location(m.group(1))


class SubscriptionPage(HTMLPage):
    def on_load(self):
        if "Vous ne disposez d'aucun contrat sur cet accès." in CleanText('.')(self.doc):
            raise BrowserIncorrectPassword()

    def get_csrf(self):
        div = self.doc.xpath('.//div[@onclick]')[0]
        m = re.search(r'csrf=(\w+)', div.attrib['onclick'])
        return m.group(1)

    def get_areas(self):
        for div in self.doc.xpath('//div[@class="listeAbonnementsBox"]'):
            site_type = div.xpath('./div[1]')[0].text
            if site_type != 'Particulier':
                for link in div.xpath('./div/@onclick'):
                    m = re.search(r"href='(.*)'", link)
                    if m:
                        yield m.group(1)

class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form('//form[@id="formAuthent"]')

        form['noPersonne'] = username
        form['motDePasse'] = password[:16]

        form.submit()


class CMSOPage(HTMLPage):
    @property
    def logged(self):
        if len(self.doc.xpath('//b[text()="Session interrompue"]')) > 0:
            return False
        return True


class AccountsPage(CMSOPage):
    TYPES = {'COMPTE CHEQUES':               Account.TYPE_CHECKING,
             'COMPTE TITRES':                Account.TYPE_MARKET,
             "ACTIV'EPARGNE":                Account.TYPE_SAVINGS,
             "TRESO'VIV":                    Account.TYPE_SAVINGS,
            }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[has-class("groupe-comptes")]//li'

        class item(ItemElement):
            klass = Account

            class Type(Filter):
                def filter(self, label):
                    for pattern, actype in AccountsPage.TYPES.items():
                        if label.startswith(pattern):
                            return actype
                    return Account.TYPE_UNKNOWN

            obj__history_url = Link('.//a[1]')
            obj_id = CleanText('.//span[has-class("numero-compte")]') & Regexp(pattern=r'(\d{3,}[\w]+)', default='')
            obj_label = CleanText('.//span[has-class("libelle")][1]')
            obj_currency = Currency('//span[has-class("montant")]')
            obj_balance = CleanDecimal('.//span[has-class("montant")]', replace_dots=True)
            obj_type = Type(Field('label'))
            # Last numbers replaced with XX... or we have to send sms to get RIB.
            obj_iban = NotAvailable

            # some accounts may appear on multiple areas, but the area where they come from is indicated
            obj__owner = CleanText('(./preceding-sibling::tr[@class="LnMnTiers"])[last()]')

            def validate(self, obj):
                if obj.id is None:
                    obj.id = obj.label.replace(' ', '')
                return True

    def on_load(self):
        if self.doc.xpath('//p[contains(text(), "incident technique")]'):
            raise BrowserIncorrectPassword("Vous n'avez aucun compte sur cet espace. " \
                                           "Veuillez choisir un autre type de compte.")


class InvestmentPage(CMSOPage):
    def has_error(self):
        return CleanText('//span[@id="id_error_msg"]')(self.doc)

    @method
    class iter_accounts(ListElement):
        item_xpath = '//table[@class="Tb" and tr[1][@class="LnTit"]]/tr[@class="LnA" or @class="LnB"]'

        class item(ItemElement):
            klass = Account

            def obj_id(self):
                area_id = Regexp(CleanText('(./preceding-sibling::tr[@class="LnMnTiers"][1])//span[@class="CelMnTiersT1"]'),
                            r'\((\d+)\)', default='')(self)
                acc_id = Regexp(CleanText('./td[1]'), r'(\d+)\s*(\d+)', r'\1\2')(self)
                if area_id:
                    return '%s.%s' % (area_id, acc_id)
                return acc_id

            def obj__formdata(self):
                js = Attr('./td/a[1]', 'onclick', default=None)(self)
                if js is None:
                    return
                args = re.search(r'\((.*)\)', js).group(1).split(',')

                form = args[0].strip().split('.')[1]
                idx = args[2].strip()
                idroot = args[4].strip().replace("'", "")
                return (form, idx, idroot)

            obj_url = Link('./td/a[1]', default=None)

    def go_account(self, form, idx, idroot):
        form = self.get_form(name=form)
        form['indiceCompte'] = idx
        form['idRacine'] = idroot
        form.submit()


class CmsoTableElement(TableElement):
    head_xpath = '//table[has-class("Tb")]/tr[has-class("LnTit")]/td'
    item_xpath = '//table[has-class("Tb")]/tr[has-class("LnA") or has-class("LnB")]'


class InvestmentAccountPage(CMSOPage):
    @method
    class iter_investments(CmsoTableElement):
        col_label = 'Valeur'
        col_code = 'Code'
        col_quantity = 'Qté'
        col_unitvalue = 'Cours'
        col_valuation = 'Valorisation'
        col_vdate = 'Date cours'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)

            def obj_code(self):
                if Field('label')(self) == "LIQUIDITES":
                    return 'XX-liquidity'
                code = CleanText(TableCell('code'))(self)
                return code if is_isin_valid(code) else NotAvailable

            def obj_code_type(self):
                return Investment.CODE_TYPE_ISIN if is_isin_valid(Field('code')(self)) else NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^RET DAB (?P<dd>\d{2})/?(?P<mm>\d{2})(/?(?P<yy>\d{2}))? (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('CARTE (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_CARD),
                (re.compile('^(?P<category>VIR(EMEN)?T? (SEPA)?(RECU|FAVEUR)?)( /FRM)?(?P<text>.*)'),
                                                              FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)( \d+)?$'),    FrenchTransaction.TYPE_ORDER),
                (re.compile('^(CHQ|CHEQUE) .*$'),             FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^(CONVENTION \d+ |F )?COTIS(ATION)? (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),          FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                              FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                              FrenchTransaction.TYPE_UNKNOWN),
                (re.compile('^.* PAIEMENT (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                              FrenchTransaction.TYPE_UNKNOWN),
               ]


class CmsoTransactionElement(ItemElement):
    klass = Transaction

    def condition(self):
        return len(self.el) >= 5 and not self.el.get('id', '').startswith('libelleLong')


class HistoryPage(CMSOPage):
    def get_date_range_list(self):
        return [d for d in self.doc.xpath('//select[@name="date"]/option/@value') if d]

    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '//div[contains(@class, "master-table")]//ul/li'

        def next_page(self):
            pager = self.page.doc.xpath('//div[@class="pager"]')
            if pager:  # more than one page if only enough transactions
                assert len(pager) == 1

                next_links = pager[0].xpath('./span/following-sibling::a[@class="page"]')
                if next_links:
                    url_next_page = Link('.')(next_links[0])
                    url_next_page = urljoin(self.page.url, url_next_page)
                    return self.page.browser.build_request(url_next_page)

        class item(CmsoTransactionElement):

            def date(selector):
                return DateGuesser(CleanText(selector, children=False), Env('date_guesser')) | Transaction.Date(selector)

            # CAUTION: this website write a 'Date valeur' inside a div with a class == 'c-ope'
            # and a 'Date opération' inside a div with a class == 'c-val'
            # so actually i assume 'c-val' class is the real operation date and 'c-ope' is value date
            obj_date = date('./div[contains(@class, "c-val")]')
            obj_vdate = date('./div[contains(@class, "c-ope")]')
            obj_raw = Transaction.Raw('./div[contains(@class, "c-libelle-long")]', children=False)
            obj_amount = Transaction.Amount('./div[contains(@class, "c-credit")]', './div[contains(@class, "c-debit")]')


class UpdateTokenMixin(object):
    def on_load(self):
        if 'Authentication' in self.response.headers:
            self.browser.token = self.response.headers['Authentication'].split(' ')[-1]


class SSODomiPage(JsonPage, UpdateTokenMixin):
    def get_sso_url(self):
        return self.doc['urlSSO']


class TokenPage(CMSOPage, UpdateTokenMixin):
    def on_load(self):
        auth_query_params = re.search(r'parent\.location = ".*#(.*)";', self.text)
        assert auth_query_params, 'Url query parameter with token for authentication was not found'
        auth_query_params = auth_query_params.group(1)

        params = dict(parse_qsl(auth_query_params))
        self.browser.token = params['id_token']
        self.browser.csrf = params['access_token']


class AuthCheckUser(HTMLPage):
    pass

