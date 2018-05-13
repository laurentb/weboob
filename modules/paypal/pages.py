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

from ast import literal_eval
from decimal import Decimal, ROUND_DOWN
import json
import re

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable, Currency
from weboob.exceptions import BrowserUnavailable, ActionNeeded
from weboob.browser.exceptions import ServerError
from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.filters.standard import CleanText, CleanDecimal
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date
from weboob.tools.js import Javascript


class LandingPage(HTMLPage):
    pass

class OldWebsitePage(LoggedPage, HTMLPage):
    pass


class InfoPage(HTMLPage):
    def on_load(self):
        raise ActionNeeded(CleanText('//h1[@class="falconHeaderText"]')(self.doc))


class PromoPage(LoggedPage, HTMLPage):
    def on_load(self):
        # We land sometimes on this page, it's better to raise an unavailable browser
        # than an Incorrect Password
        raise BrowserUnavailable('Promo Page')

class LoginPage(HTMLPage):
    def get_token_and_csrf(self, code):
        mtc = re.search(r'var (_0x\w{4})=function.*?\};', code)
        decoder_name = mtc.group(1)

        decoder_code = re.search(r'var _0x\w{4}=\[.*var (_0x\w{4})=function.*?\};', code).group(0)
        decoder_code += """
        ;function mapDecoder(array) {
            var map = {};
            for (var key in array) {
                map[key] = %s(key);
            }
            return map;
        }
        """ % decoder_name
        decoder_js = Javascript(decoder_code)

        # clean string obfuscation like: '\x70\x61\x79\x70\x61\x6c\x20\x73\x75\x63\x6b\x73'
        def basic_decoder(mtc):
            return repr(literal_eval(mtc.group(0)).encode('utf-8'))
        cleaner_code = re.sub(r"'.*?(?<!\\)'", basic_decoder, code)

        # clean other obfuscation like: _0x1234('0x42')
        # Do only one call to JS by putting all the elements to decode in an
        # array that will be mapped in JS to a structure of the form {encoded:
        # decoded}.
        to_decode = set()
        for m in re.finditer(r"%s\('([^']+)'\)" % re.escape(decoder_name), cleaner_code):
            to_decode.add(literal_eval(m.group(1)))

        decoded_map = decoder_js.call('mapDecoder', [k for k in to_decode])

        def exec_decoder(mtc):
            key = repr(literal_eval(mtc.group(1)))
            # Use json.dumps to force utf8 encoding.
            ret = json.dumps(str(decoded_map[key]))
            # Force simple quoting around the string.
            return "'" + ret[1:-1] + "'"
        cleaner_code = re.sub(r"%s\('([^']+)'\)" % re.escape(decoder_name), exec_decoder, cleaner_code)

        cookie = re.search(r'xppcts = (\w+);', cleaner_code).group(1)
        sessionID = re.search(r"%s'([^']+)'" % re.escape("'&_sessionID='+encodeURIComponent("), cleaner_code).group(1)
        csrf = re.search(r"%s'([^']+)'" % re.escape("'&_csrf='+encodeURIComponent("), cleaner_code).group(1)
        key, value = re.findall(r"'(\w+)','(\w+)'", cleaner_code)[-1]

        # Detect the name of the function that computes the token, detect the
        # variable that stores the result and store it as a global.
        get_token_func_name = re.search(r"ads_token_js='\+encodeURIComponent\((\w+)\)", cleaner_code).group(1)
        get_token_func_declaration = "var " + get_token_func_name + "="
        cleaner_code = cleaner_code.replace(get_token_func_declaration, get_token_func_declaration + "window.ADS_JS_TOKEN=")

        # Remove the call to an infinite loop
        loop_func_name = re.search(r"\(function\(\w+,\s?\w+,\s?\w+,\s?\w+\)\{var\s(\w+)=", cleaner_code).group(1)
        cleaner_code = cleaner_code.replace(loop_func_name + "();", "")
        cleaner_code = cleaner_code.replace("data;", "return;")

        # Simulate a browser environment
        simulate_browser_code = """
            if (!document.createAttribute) {
                document.createAttribute = null;
            }

            if (!document.domain) {
                document.domain = "paypal.com";
            }

            if (!document.styleSheets) {
                document.styleSheets = null;
            }

            if (!document.characterSet) {
                document.characterSet = "UTF-8";
            }

            if (!document.documentElement) {
                document.documentElement = {};
            }

            if (!window.innerWidth || !window.innerHeight) {
                window.innerWidth = 1280;
                window.innerHeight = 800;
            }

            if (typeof(screen) === "undefined") {
                var screen = window.screen = {
                    width: 1280,
                    height: 800
                };
            }

            if (typeof(history) === "undefined") {
                var history = window.history = {};
            }

            if (typeof(location) === "undefined") {
                var location = window.location = {
                    host: "paypal.com"
                };
            }

            var XMLHttpRequest = function() {};
            XMLHttpRequest.prototype.onreadystatechange = function(){};
            XMLHttpRequest.prototype.open = function(){};
            XMLHttpRequest.prototype.setRequestHeader = function(){};
            XMLHttpRequest.prototype.send = function(){};
            window.XMLHttpRequest = XMLHttpRequest;

            if (!navigator.appName) {
                navigator.appName =  "Netscape";
            }

            navigator.userAgent = "Mozilla/5.0 (X11; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0";
        """

        # Add a function that returns the token
        cleaner_code += """
        function GET_ADS_JS_TOKEN()
        {
            return window.ADS_JS_TOKEN || "INVALID_TOKEN";
        }
        """

        token = str(Javascript(simulate_browser_code + cleaner_code).call("GET_ADS_JS_TOKEN"))
        return token, csrf, key, value, sessionID, cookie

    def login(self, login, password, ):
        form = self.get_form(name='login')
        form['login_email'] = login
        form['login_password'] = password
        form['splitLoginContext'] = 'inputPassword'
        form['splitLoginCookiedFallback'] = True
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
        content = self.doc.xpath('//div[@id="moneyPage" or @id="MoneyPage"]')[0]

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
            amount = Decimal(re.sub(r'[^\d]', '', amount))/Decimal((10 ** m.start())) if m else Decimal(amount)

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
        # Add secondary transactions on label condition.
        for t in transaction['secondaryTransactions']:
            if t['transactionDescription']['description'] == u'Virement à partir de':
                trans.extend(self.parse_transaction(t, account))
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
                                                                                       u'Paid',
                                                                                       u'Pending',
                                                                                       u'Canceled',
                                                                                       u'Suspended']:
            return []
        for pattern in [u'Commande à', u'Offre de remboursement', u'Bill to']:
            if 'description' not in transaction['transactionDescription'] or transaction['transactionDescription']['description'].startswith(pattern):
                return []

        t = FrenchTransaction(transaction['transactionId'])
        # Those are not really transactions.
        if 'grossAmount' not in transaction or not 'currency' in transaction['grossAmount'] \
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
            t.original_amount = Decimal(str(transaction['netAmount']['amountUnformatted']))
            t.original_currency = original_currency
            t.amount = Decimal(str(cc[0]))
        else:
            t.amount = Decimal(str(transaction['netAmount']['amountUnformatted']))
        date = parse_french_date(transaction['transactionTime'])
        raw = "%s %s" % (transaction['transactionDescription']['description'], transaction['transactionDescription']['name'])
        if raw == "Transfert de Compte bancaire":
            t.type = FrenchTransaction.TYPE_TRANSFER
        if raw == u'Annulation des frais de PayPal':
            return []

        # Dougs told us that commission should always be netAmount minus grossAmount
        grossAmount = Decimal(str(transaction['grossAmount']['amountUnformatted']))
        t.commission = Decimal(str(transaction['feeAmount']['amountUnformatted']))
        if t.commission:
            if original_currency == account.currency:
                assert abs(t.amount - grossAmount) == abs(t.commission)
                t.commission = t.amount - grossAmount
            else:
                t.commission = (t.commission * t.amount / t.original_amount).quantize(Decimal('.01'), rounding=ROUND_DOWN)

        t.parse(date=date, raw=raw)
        trans.append(t)
        return trans


class PartHistoryPage(HistoryPage, JsonPage):
    def transaction_left(self):
        return self.doc['data']['activity']['hasTransactionsCompleted'] or self.doc['data']['activity']['hasTransactionsPending']

    def get_transactions(self):
            return self.doc['data']['activity']['transactions']

    def return_detail_page(self, link):
        return self.browser.open('%s%s' % (self.browser.BASEURL, link.replace(self.browser.BASEURL, '')), headers={'Accept': 'application/json'}).page

    def parse_transaction(self, transaction, account):
        page = None
        if 'id' not in transaction or not transaction['date']:
            return []
        t = FrenchTransaction(transaction['id'])
        if not transaction['isPrimaryCurrency']:
            if not 'txnCurrency' in transaction['amounts']:
                return []
            original_currency = unicode(transaction['amounts']['txnCurrency'])
            if original_currency in self.browser.account_currencies:
                return []
            if 'conversionFrom' in transaction['amounts'] and 'value' in transaction['amounts']['conversionFrom'] and account.currency == transaction['amounts']['conversionFrom']['currency']:
                cc = self.format_amount(transaction['amounts']['conversionFrom']['value'], transaction['isCredit'])
            else:
                try:
                    page = self.return_detail_page(transaction['detailsLink'])
                    cc = page.get_converted_amount() if isinstance(page, HistoryDetailsPage) else None
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
        date = parse_french_date(transaction['date']['formattedDate'] + ' ' + transaction['date']['year']).date()
        raw = transaction.get('counterparty', transaction['displayType'])
        t.parse(date=date, raw=raw)

        if page is None and t.amount < 0:
            page = self.return_detail_page(transaction['detailsLink'])
        funding_src = page.get_funding_src(t) if isinstance(page, HistoryDetailsPage) else None

        return [t] if funding_src is None else ([t] + [funding_src])


class HistoryDetailsPage(LoggedPage, JsonPage):
    def get_converted_amount(self):
        try:
            currency_conversion = self.doc['data']['details']['currencyConversion']
            assert len(currency_conversion) <= 1
            return CleanDecimal(replace_dots=True).filter(currency_conversion[0]['sourceAmount'])
        except KeyError:
            return None

    # This creates a mirror transaction when payment is not from paypal balance.
    def get_funding_src(self, t):
        if 'fundingSource' not in self.doc['data']['details']:
            return None

        funding_src_lst = [src for src in self.doc['data']['details']['fundingSource']['fundingSourceList'] if src['type'] != 'BALANCE']
        assert len(funding_src_lst) <= 1
        for src in funding_src_lst:
            tr = FrenchTransaction(t.id+'_fundingSrc')
            tr.amount = CleanDecimal(replace_dots=True).filter(src['amount'])
            tr.date = tr.rdate = t.date
            tr.label = tr.raw = u'Crédit depuis %s' % src['institution']
            return tr
