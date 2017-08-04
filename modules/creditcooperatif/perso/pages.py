# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Kevin Pouget, Florent Fourcot
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

from weboob.tools.json import json
from weboob.capabilities.bank import Account, NotAvailable, Recipient, TransferBankError, Transfer
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage, PartialHTMLPage
from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import (
    Filter, Format, CleanText, CleanDecimal, BrowserURL, Field, Async, AsyncLoad,
    Date, Regexp,
)
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.exceptions import ServerError


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(xpath='//form[@id="AuthForm"]')
        form['j_username'] = login.encode('iso-8859-15')
        form['j_password'] = password.encode('iso-8859-15')
        form.submit()


class CreditLoggedPage(HTMLPage):
    def get_error(self):
        div = self.doc.xpath('//div[@class="errorForm-msg"]')
        if len(div) == 0:
            return None

        msg = u', '.join([li.text.strip() for li in div[0].xpath('.//li')])
        return re.sub('[\r\n\t\xa0]+', ' ', msg)


class AddType(Filter):
    types = {u'COMPTE NEF': Account.TYPE_CHECKING,
             u'CPTE A VUE': Account.TYPE_CHECKING,
             u'LIVRET AGIR': Account.TYPE_SAVINGS,
             u'LIVRET A PART': Account.TYPE_SAVINGS,
             u'PEL': Account.TYPE_SAVINGS,
             }

    def filter(self, str_type):
        for key, acc_type in self.types.items():
            if key == str_type:
                return acc_type
        return Account.TYPE_UNKNOWN


class AccountsPage(LoggedPage, HTMLPage):
    @method
    class get_list(ListElement):
        item_xpath = '//table[has-class("table-synthese")]'

        class item(ItemElement):
            klass = Account

            load_details = BrowserURL('iban', account_id=Field('id')) & AsyncLoad

            obj_label = Format('%s %s', CleanText('.//h2[@class="tt_compte"][1]'), CleanText('.//ul[@class="nClient"]/li[1]'))
            obj_id = CleanText('.//ul[@class="nClient"]/li[last()]', symbols=u'N°')
            obj_type = AddType(CleanText('.//h2[@class="tt_compte"][1]'))
            obj_balance = CleanDecimal('.//td[@class="sum_solde"]//span[last()]', replace_dots=True)
            obj_currency = u'EUR'

            def obj_iban(self):
                try:
                    return Async('details', CleanText('(.//div[@class="iban"]/p)[1]', replace=[(' ', '')]))(self)
                except ServerError:
                    return NotAvailable


class IbanPage(LoggedPage, HTMLPage):
    pass


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(?P<text>RETRAIT DAB) (?P<dd>\d{2})-(?P<mm>\d{2})-([\d\-]+)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})-(?P<mm>\d{2})-([\d\-]+) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CARTE (?P<dd>\d{2})(?P<mm>\d{2}) \d+ (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_CARD),
                (re.compile('^VIR COOPA (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^COOPA (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^VIR(EMENT|EMT| SEPA EMET :)? (?P<text>.*?)(- .*)?$'),
                                                            FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^(PRLV|PRELEVEMENT) SEPA (?P<text>.*?)(- .*)?$'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^(PRLV|PRELEVEMENT) (?P<text>.*?)(- .*)?$'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^CHEQUE.*'),                   FrenchTransaction.TYPE_CHECK),
                (re.compile('^(AGIOS /|FRAIS) (?P<text>.*)'), FrenchTransaction.TYPE_BANK),
                (re.compile('^ABONNEMENT (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),        FrenchTransaction.TYPE_DEPOSIT),
                (re.compile('^(?P<text>.*)( \d+)? QUITTANCE .*'),
                                                            FrenchTransaction.TYPE_ORDER),
                (re.compile('^.* LE (?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{2})$'),
                                                            FrenchTransaction.TYPE_UNKNOWN),
               ]


class TransactionsPage(LoggedPage, HTMLPage):
    pass


class TransactionsJSONPage(LoggedPage, JsonPage):
    ROW_DATE =    0
    ROW_TEXT =    2
    ROW_CREDIT = -1
    ROW_DEBIT =  -2

    def get_transactions(self):
        seen = set()
        for tr in self.doc['exportData'][1:]:
            t = Transaction()
            t.parse(tr[self.ROW_DATE], tr[self.ROW_TEXT])
            t.set_amount(tr[self.ROW_CREDIT], tr[self.ROW_DEBIT])
            t.id = t.unique_id(seen)
            yield t


class ComingTransactionsPage(LoggedPage, HTMLPage):
    ROW_REF =     0
    ROW_TEXT =    1
    ROW_DATE =    2
    ROW_CREDIT = -1
    ROW_DEBIT =  -2

    def get_transactions(self):
        data = []
        for script in self.doc.xpath('//script'):
            txt = script.text
            if txt is None:
                continue

            pattern = 'var jsonData ='
            start = txt.find(pattern)
            if start < 0:
                continue

            txt = txt[start+len(pattern):start+txt[start:].find(';')]
            data = json.loads(txt)
            break

        for tr in data:
            if tr[self.ROW_DATE] == 'En attente de comptabilisation':
                self.logger.debug('skipping transaction without a date: %r', tr[self.ROW_TEXT])
                continue

            t = Transaction()
            t.parse(tr[self.ROW_DATE], tr[self.ROW_TEXT])
            t.set_amount(tr[self.ROW_CREDIT], tr[self.ROW_DEBIT])
            yield t


class RecipientsPage(LoggedPage, PartialHTMLPage):
    @method
    class iter_internal_recipients(ListElement):
        item_xpath = '//div[@class="internAcount"]//ul[@class="accountListe"]/li'

        class item(ItemElement):
            klass = Recipient

            obj_label = Format('%s - %s (%s)',
                               CleanText('.//div[@class="crediteur"]/span[@class="crediteurDetail"]/strong'),
                               CleanText('.//div[@class="crediteur"]/span[@class="crediteurDetail"]/span/strong'),
                               CleanText('.//div[@class="crediteur"]/span[@class="crediteurDetail"]/small[@class="smallTxt"]'))

            obj_id = Attr('.//input[@name="nCompteCred"]', 'value')

            obj_category = u'Interne'
            obj_bank_name = u'Crédit Coopératif'

    @method
    class iter_external_recipients(ListElement):
        item_xpath = '//div[@class="externAcount"]//ul[@class="accountListe"]/li'

        class item(ItemElement):
            klass = Recipient

            obj_label = CleanText('.//span[@class="tabTxt"]/strong')
            obj_id = Attr('.//input[@name="nCompteCred"]', 'value')

            obj_category = u'Externe'

            obj_bank_name = CleanText('.//small/span[3]')

            def obj_iban(self):
                return CleanText('.//small/span[2]')(self).replace(' ', '')

    def iter_recipients(self):
        for r in self.iter_internal_recipients():
            yield r
        for r in self.iter_external_recipients():
            yield r


class EmittersPage(LoggedPage, PartialHTMLPage):
    @method
    class iter_emitters(ListElement):
        item_xpath = '//ul[@class="accountListe"]/li'

        class item(ItemElement):
            klass = Recipient

            obj_id = Attr('.//input[@name="nCompteDeb"]', 'value')


class TransferPage(LoggedPage, HTMLPage):
    def prepare_form(self, transfer, date):
        form = self.get_form(id='formCreateVir')
        form['typevirradio'] = 'ponct'
        form['isBenef'] = 'false'
        form['nCompteDeb'] = form['numCptDeb'] = transfer.account_id
        form['nCompteCred'] = form['numCptCred'] = transfer.recipient_id
        form['dtponct'] = date.strftime('%d/%m/%Y')
        form['montant'] = str(transfer.amount)
        form['intitule'] = transfer.label or ''
        form.req = None
        return form


class TransferDatesPage(LoggedPage, PartialHTMLPage):
    def iter_dates(self):
        for opt in self.doc.xpath('//select[@name="dtponct"]/option'):
            yield Date(CleanText('./@value'), dayfirst=True)(opt)


class TransferValidatePage(LoggedPage, PartialHTMLPage):
    def on_load(self):
        msg = CleanText('//li')(self.doc)
        if msg:
            raise TransferBankError(message=msg)


class TransferPostPage(LoggedPage, PartialHTMLPage):
    @method
    class get_transfer(ItemElement):
        klass = Transfer

        obj_amount = CleanDecimal('//p[@class="tabTxt tabTxt2"]/strong[1]', replace_dots=True)
        obj_exec_date = Date(CleanText('//p[@class="tabTxt tabTxt2"]/strong[2]'), dayfirst=True)
        obj_label = Regexp(CleanText('//p[@class="tabTxt tabTxt2"]/strong[3]'), u'« (.*) »')
        obj_account_id = Regexp(CleanText('//div[@class="transAction"]/div[@class="inner"]/div[@class="first"]//small'), ur'N°(\w+)')
        obj_recipient_id = Regexp(CleanText('//div[@class="transAction"]/div[@class="inner"]/div[not(@class="first")]//small'), ur'N°(\w+)', default=None)

        def obj_recipient_iban(self):
            if Field('recipient_id')(self) is None:
                return CleanText('//div[@class="transAction"]/div[@class="inner"]/div[not(@class="first")]//span[@class="tabTxt"]')(self).replace(' ', '')

    def finish(self):
        self.get_form(id='form').submit()


class TransferFinishPage(LoggedPage, PartialHTMLPage):
    def on_load(self):
        assert b'Votre demande a bien &eacute;t&eacute; prise en compte' in self.data
