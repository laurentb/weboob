# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from decimal import Decimal
import re

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable, Currency
from weboob.exceptions import BrowserUnavailable
from weboob.browser.exceptions import ServerError
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.filters.standard import CleanText, CleanDecimal
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date
from weboob.tools.js import Javascript


class LandingPage(HTMLPage):
    pass

class OldWebsitePage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserUnavailable('Old Website is not supported anymore.')


class PromoPage(LoggedPage, HTMLPage):
    def on_load(self):
        # We land sometimes on this page, it's better to raise an unavailable browser
        # than an Incorrect Password
        raise BrowserUnavailable('Promo Page')

class LoginPage(HTMLPage):
    def get_token_and_csrf(self, code):
        code1 = re.search('(function .*)\(function\(\)', code).group(1)
        # Another victory for the scrapper team # CommitStrip Data Wars
        code1 = re.sub('return typeof document!="undefined"&&typeof document.createAttribute!="undefined"', 'return 1==1', code1)
        # now it checks if some browsers-only builtin variables are defined:
        # e+=function(e,t){return typeof navigator!="undefined"?e:t}
        js = Javascript('var navigator = {}; var document = {}; document.lastModified = 1; \
        document.getElementsByTagName = 1; document.implementation = 1; document.createAttribute = 1; document.getElementsByName = 1;'+ code1)
        func_name = re.search(r'function (\w+)\(\)', code1).group(1)
        token = str(js.call(func_name))
        csrf = re.search(r'csrf="\+encodeURIComponent\("(.*?)"\)', code).group(1)
        key, value = re.search(r'"/auth/verifychallenge",t,"([^"]+)","([^"]+)"', code).groups()
        return token, csrf, key, value

    def login(self, login, password):
        form = self.get_form(name='login')
        form['login_email'] = login
        form['login_password'] = password
        return form.submit(headers={'X-Requested-With': 'XMLHttpRequest'})

    def get_script_url(self):
        body = self.doc.xpath('//body')[0]
        if 'data-ads-challenge-url' in body.attrib:
            return 'https://www.paypal.com%s' % body.attrib['data-ads-challenge-url']

        # Paypal still use old method sometimes
        list1 = self.doc.xpath('//script')
        for s in list1:
            if 'src' in s.attrib and 'challenge' in s.attrib['src']:
                return s.attrib['src']

class ErrorPage(HTMLPage):
    pass

class UselessPage(LoggedPage, HTMLPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    def detect_account_type(self):
        if self.doc.xpath('//a[contains(@href, "businessexp")] | //script[contains(text(), "business")]'):
            self.browser.account_type = "pro"
        elif self.doc.xpath('//a[contains(@href, "myaccount")]'):
            self.browser.account_type = "perso"


class AccountPage(HomePage):
    def get_account(self, _id):
        return self.get_accounts().get(_id)

    def get_accounts(self):
        accounts = {}
        content = self.doc.xpath('//div[@id="moneyPage"]')[0]

        # Multiple accounts
        lines = content.xpath('(//div[@class="col-md-8 multi-currency"])[1]/ul/li')
        for li in lines:
            account = Account()
            account.iban = NotAvailable
            account.type = Account.TYPE_CHECKING
            currency_code = CleanText().filter((li.xpath('./span[@class="currencyUnit"]/span') or li.xpath('./span[1]'))[0])
            currency = Currency.get_currency(currency_code)
            if not currency:
                self.logger.warning('Unable to find currency %r', currency_code)
                continue
            account.id = currency
            account.currency = currency
            account.balance = CleanDecimal(replace_dots=True).filter(li.xpath('./span[@class="amount"]/text()'))
            account.label = u'%s %s*' % (self.browser.username, account.currency)
            accounts[account.id] = account
            self.browser.account_currencies.append(account.currency)

        if not accounts:
        # Primary currency account
            primary_account = Account()
            primary_account.iban = NotAvailable
            primary_account.type = Account.TYPE_CHECKING
            try:
                balance = CleanText('.')(content.xpath('//div[contains(@class, "col-md-6")][contains(@class, "available")]')[0])
            except IndexError:
                primary_account.id = 'EUR'
                primary_account.currency = u'EUR'
                primary_account.balance = NotAvailable
                primary_account.label = u'%s' % (self.browser.username)
            else:
                primary_account.currency = Account.get_currency(balance)
                primary_account.id = unicode(primary_account.currency)
                primary_account.balance = Decimal(FrenchTransaction.clean_amount(balance))
                primary_account.label = u'%s %s*' % (self.browser.username, primary_account.currency)

            accounts[primary_account.id] = primary_account

        return accounts


class HistoryPage(LoggedPage):
    def iter_transactions(self, account):
        for trans in self.parse(account):
            yield trans

    def parse(self, account):
        transactions = list()

        transacs = self.get_transactions()

        for t in transacs:
            for trans in self.parse_transaction(t, account):
                transactions.append(trans)

        for t in transactions:
            yield t

    def format_amount(self, amount, is_credit):
        """
        This function takes a textual amount to convert it to Decimal.

        It tries to guess what is the decimal separator (, or .).
        """
        if not isinstance(amount, Decimal):
            m = re.search(r"\D", amount.strip(u'€').strip(u'\xa0')[::-1])
            amount = Decimal(re.sub(r'[^\d]', '', amount))/Decimal((10 ** m.start()))

        if is_credit:
            return abs(amount)
        else:
            return -abs(amount)

class ProHistoryPage(HistoryPage, JsonPage):
    def transaction_left(self):
        return 'transactions' in self.doc['data'] and self.doc['data']['transactions']

    def get_next_page_token(self):
        if 'nextpageurl' in self.doc['data']:
            return self.doc['data']['nextpageurl']
        return None

    def get_transactions(self):
        return self.doc['data']['transactions']

    def parse_transaction(self, transaction, account):
        trans = []
        if 'transactionStatus' in transaction and transaction['transactionStatus'] in [u'Créé',
                                                                                       u'Annulé',
                                                                                       u'Suspendu',
                                                                                       u'Mis à jour',
                                                                                       u'Actif', u'Payé',
                                                                                       u'En attente',
                                                                                       u'Rejeté',
                                                                                       u'Expiré',
                                                                                       u'Created',
                                                                                       u'Brouillon',
                                                                                       u'Canceled']:
            return []
        for pattern in [u'Commande à', u'Offre de remboursement', u'Bill to']:
            if 'description' not in transaction['transactionDescription'] or transaction['transactionDescription']['description'].startswith(pattern):
                return []

        t = FrenchTransaction(transaction['transactionId'])
        # Those are not really transactions.
        if not 'currency' in transaction['grossAmount'] \
                or transaction['transactionDescription']['description'].startswith("Conversion de devise"):
            return []
        original_currency = unicode(transaction['grossAmount']['currency'])
        if not original_currency == account.currency:
            if original_currency in self.browser.account_currencies:
                return []
            cc = [tr['grossAmount']['amountUnformatted'] for tr in transaction['secondaryTransactions'] \
                 if account.currency == tr['grossAmount']['currency'] \
                  and (tr['grossAmount']['amountUnformatted'] < 0) == (transaction['grossAmount']['amountUnformatted'] < 0) \
                  and tr['transactionDescription']['description'].startswith('Conversion de devise')]
            if not cc:
                return []
            assert len(cc) == 1
            t.original_amount = Decimal(str(transaction['grossAmount']['amountUnformatted']))
            t.original_currency = original_currency
            t.amount = Decimal(str(cc[0]))
        else:
            t.amount = Decimal(str(transaction['netAmount']['amountUnformatted']))
        date = parse_french_date(transaction['transactionTime'])
        raw = "%s %s" % (transaction['transactionDescription']['description'], transaction['transactionDescription']['name'])
        if raw == "Transfert de Compte bancaire":
            t.type = FrenchTransaction.TYPE_TRANSFER
        t.commission = Decimal(str(transaction['feeAmount']['amountUnformatted']))
        t.parse(date=date, raw=raw)
        trans.append(t)
        return trans


class PartHistoryPage(HistoryPage, JsonPage):
    def transaction_left(self):
        return self.doc['data']['activity']['hasTransactionsCompleted'] or self.doc['data']['activity']['hasTransactionsPending']

    def get_transactions(self):
            return self.doc['data']['activity']['transactions']

    def parse_transaction(self, transaction, account):
        t = FrenchTransaction(transaction['id'])
        if not transaction['isPrimaryCurrency']:
            original_currency = unicode(transaction['amounts']['txnCurrency'])
            if original_currency in self.browser.account_currencies:
                return []
            if 'conversionFrom' in transaction['amounts'] and 'value' in transaction['amounts']['conversionFrom'] and account.currency == transaction['amounts']['conversionFrom']['currency']:
                cc = self.format_amount(transaction['amounts']['conversionFrom']['value'], transaction['isCredit'])
            else:
                try:
                    cc = self.browser.convert_amount(account, transaction, transaction['detailsLink'])
                except ServerError:
                    self.logger.warning('Unable to go on detail, transaction skipped.')
                    return []
            if not cc:
                return []
            t.original_amount = self.format_amount(transaction['amounts']['net']['value'], transaction["isCredit"])
            t.original_currency = original_currency
            t.amount = self.format_amount(cc, transaction['isCredit'])
        else:
            t.amount = self.format_amount(transaction['amounts']['net']['value'], transaction['isCredit'])
        date = parse_french_date(transaction['date']['formattedDate'] + ' ' + transaction['date']['year'])
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        return [t]

class HistoryDetailsPage(LoggedPage, HTMLPage):
    def get_converted_amount(self, account):
        find_td = self.doc.xpath('//td[contains(text(),"' + account.currency + '")] | //dd[contains(text(),"' + account.currency + '")]')
        if len(find_td) > 0 :
            # In case text is "12,34 EUR = 56.78 USD" or "-£115,62 GBP soit -€163,64 EUR"
            for f in find_td:
                for text in re.split('=|soit|equals', CleanText().filter(f)):
                    if ' %s' % account.currency in text:
                        return Decimal(FrenchTransaction.clean_amount(text.split(account.currency)[0]))
        return False
