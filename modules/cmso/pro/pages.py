# -*- coding: utf-8 -*-

# Copyright(C) 2014      smurail
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
import datetime

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ListElement, ItemElement, TableElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, DateGuesser, Env, Field, Filter, Regexp, \
                                            Currency
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['LoginPage']


class UselessPage(HTMLPage):
    pass


class ChoiceLinkPage(HTMLPage):
    def on_load(self):
        link_line = self.doc.xpath('//script')[-1].text
        m = re.search(r'lien\("(.*)"', link_line)
        if m:
            self.browser.location(m.group(1))

class SubscriptionPage(HTMLPage):
    def on_load(self):
        if u"Vous ne disposez d'aucun contrat sur cet accès." in CleanText(u'.')(self.doc):
            raise BrowserIncorrectPassword()

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


class CmsoListElement(ListElement):
    item_xpath = '//table[@class="Tb" and tr[1][@class="LnTit"]]/tr[@class="LnA" or @class="LnB"]'


class AccountsPage(CMSOPage):
    TYPES = {u'COMPTE CHEQUES':               Account.TYPE_CHECKING,
             u'COMPTE TITRES':                Account.TYPE_MARKET,
             u"ACTIV'EPARGNE":                Account.TYPE_SAVINGS,
            }

    @method
    class iter_accounts(CmsoListElement):
        class item(ItemElement):
            klass = Account

            class Type(Filter):
                def filter(self, label):
                    for pattern, actype in AccountsPage.TYPES.iteritems():
                        if label.startswith(pattern):
                            return actype
                    return Account.TYPE_UNKNOWN

            obj__history_url = Link('./td[1]/a')
            obj_label = CleanText('./td[1]')
            obj_currency = Currency('//span[contains(text(), "Solde")]')
            obj_balance = CleanDecimal('./td[2]', replace_dots=True)
            obj_type = Type(Field('label'))
            # Last numbers replaced with XX... or we have to send sms to get RIB.
            obj_iban = NotAvailable

            # some accounts may appear on multiple areas, but the area where they come from is indicated
            obj__owner = CleanText('(./preceding-sibling::tr[@class="LnMnTiers"])[last()]')

            def obj_id(self):
                history_url = Field('_history_url')(self)
                if history_url.startswith('javascript:'):
                    # Market account
                    page = self.page.browser.investment.go()

                    area_id = Regexp(CleanText('//span[@class="CelMnTiersT1"]'), r'\((\d+)\)', default='')(page.doc)

                    for tr in page.doc.xpath('.//table/tr[not(has-class("LnTit")) and not(has-class("LnTot"))]'):
                        # Try to match account with id and balance.
                        if CleanText('./td[2]//a')(tr) == Field('label')(self) \
                            and CleanDecimal('./td[3]//a')(tr) == Field('balance')(self):

                            acc_id = CleanText('./td[1]', replace=[(' ', '')])(tr)
                            if area_id:
                                # because the acc_id can be the same between multiple areas
                                return '%s.%s' % (area_id, acc_id)
                            return acc_id
                else:
                    page = self.page.browser.open(history_url).page
                    return Regexp(CleanText('//span[has-class("Rappel")]'), '(\d{18}) | (\d{3}\w\d{15})')(page.doc)

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
    class iter_accounts(CmsoListElement):
        class item(ItemElement):
            klass = Account

            def obj_id(self):
                area_id = Regexp(CleanText('//span[@class="CelMnTiersT1"]'), r'\((\d+)\)', default='')(self)
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
        col_isin = 'Code'
        col_quantity = u'Qté'
        col_unitvalue = 'Cours'
        col_valuation = 'Valorisation'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = CleanText(TableCell('isin'))
            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=(',', '.'))
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=('', ','))
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=(' ', '.'))


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
               ]


class CmsoTransactionElement(ItemElement):
    klass = Transaction

    def condition(self):
        return len(self.el) >= 5 and not self.el.get('id', '').startswith('libelleLong')


class HistoryPage(CMSOPage):
    def iter_history(self, *args, **kwargs):
        if self.doc.xpath('//a[contains(., "Revenir")]'):
            return self.iter_history_rest_page(*args, **kwargs)
        return self.iter_history_first_page(*args, **kwargs)

    @method
    class iter_history_first_page(CmsoListElement):
        class item(CmsoTransactionElement):
            def validate(self, obj):
                return obj.date >= datetime.date.today().replace(day=1)

            def date(selector):
                return DateGuesser(CleanText(selector), Env('date_guesser')) | Transaction.Date(selector)

            obj_date = date('./td[1]')
            obj_vdate = date('./td[2]')
            # Each row is followed by a "long labelled" version
            obj_raw = Transaction.Raw('./following-sibling::tr[1][starts-with(@id, "libelleLong")]/td[3]')
            obj_amount = Transaction.Amount('./td[5]', './td[4]')

            def condition(self):
                return len(self.el) >= 5 and not self.el.get('id', '').startswith('libelleLong') and len(self.el.xpath('.//i')) > 0

    @pagination
    @method
    class iter_history_rest_page(CmsoListElement):
        next_page = Link('//span[has-class("Rappel")]/following-sibling::*[1][@href]')

        class item(CmsoTransactionElement):
            obj_date = Transaction.Date('./td[2]')
            obj_vdate = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[3]')
            obj_amount = Transaction.Amount('./td[5]', './td[4]')
