# -*- coding: utf-8 -*-

# Copyright(C) 2018 Arthur Huillet
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

from weboob.browser.filters.html import Attr
from weboob.browser.filters.standard import CleanText, CleanDecimal, Currency, Date
from weboob.browser.filters.json import Dict

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account, Transaction, Investment
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
from weboob.browser.elements import method, ItemElement, DictElement


class LoginPage(HTMLPage):
    def login(self, login, passwd):

        form = self.get_form(id='loginForm')
        form['UserName'] = login
        form['Password'] = passwd
        form.submit()


class AccountSelectionBar(LoggedPage, HTMLPage):
    def get_account_selector_verification_token(self):
        return self.doc.xpath("//div[@class='accounts']//input[@name='__RequestVerificationToken']/@value")[0]


class AccountsList(AccountSelectionBar):

    def get_list(self):
        accounts = []

        for account_category in self.doc.xpath('//div[@id="AccountGroups"]//h1'):
            type_mappings = {'PEA'           : Account.TYPE_PEA,
                             'Compte-titres' : Account.TYPE_MARKET,
                             'Livret'        : Account.TYPE_SAVINGS,
                             # XXX PEA-PME?
                             }

            try:
                current_type = type_mappings[account_category.text]
            except KeyError:
                self.logger.warning("Unknown account type for " + CleanText().filter(account_category))
                current_type = Account.TYPE_UNKNOWN

            for cpt in account_category.xpath('..//tr[@data-accountnumber]'):
                account = Account()
                account.type = current_type
                account.id = Attr(".", "data-accountnumber")(cpt)
                account.label = CleanText("./td[1]")(cpt)
                account.balance = CleanDecimal("./td[2]", replace_dots=True)(cpt)
                account.iban = NotAvailable  # XXX need IBAN
                accounts.append(account)
        return accounts


class TransactionHistoryJSON(JsonPage):
    @method
    class iter_history(DictElement):
        item_xpath = 'Transactions'
        '''
{u'CurrentPage': 0,
 u'EndOfData': True,
 u'LastSequenceNumber': 1,
 u'MutationGroupIntroductionText': u'Historique des transactions',
 u'MutationGroupIntroductionTitle': u'Toutes les transactions',
 u'Pages': [24],
 u'Transactions': [{u'Amount': u'0,00 \u20ac',
   u'Date': u'06/04/2017',
   u'Description': u'\xe0 xxxx',
   u'Mutation': u'-345,99 \u20ac',
   u'Number': 24,
   u'TransactionId': 20333,
   u'Type': u'Virement interne',
   u'ValueDate': u'06/04/2017'},
  {u'Amount': u'345,99 \u20ac',
   u'Date': u'05/04/2017',
   u'Description': u"'Frais remboursement'",
   u'Mutation': u'5,00 \u20ac',
   u'Number': 23,
   u'TransactionId': 2031111,
   u'Type': u'Commissions',
   u'ValueDate': u'05/04/2017'},
}
'''
        class item(ItemElement):
            klass = Transaction
            obj_id = Dict('TransactionId')
            obj_date = Date(Dict('Date'), dayfirst=True, default=NotAvailable)
            obj_label = CleanText(Dict('Description'))
            obj_amount = CleanDecimal(Dict('Mutation'), replace_dots=True, default=NotAvailable)
            obj__account_balance = CleanDecimal(Dict('Amount'), replace_dots=True, default=NotAvailable)
            obj__num_oper = Dict('Number')
            obj__transaction_id = Dict('TransactionId')
            # XXX this page has types that do not make a lot of sense, and
            # crappy descriptions, and weboob does not have the types we want
            # anyway. Don't bother filling in the type.
            obj_type = Transaction.TYPE_BANK
            obj_vdate = Date(Dict('ValueDate'), dayfirst=True, default=NotAvailable)

            def obj_original_currency(self):
                return Account.get_currency(Dict('Mutation')(self))

            def obj__transaction_detail(self):
                return
                'https://web.binck.fr/TransactionDetails/TransactionDetails?transactionSequenceNumber=%d&currencyCode=%s' % \
                    (self.obj._num_oper, self.obj.original_currency)


class InvestmentListJSON(JsonPage):
    '''
{
    "PortfolioOverviewGroups": [
        {
            "GroupName": "ETF",
            "Items": [
                {
                    "CurrencyCode": "EUR",
                    "SecurityId": 4019272,
                    "SecurityName": "Amundi ETF MSCI Emg Markets UCITS EUR C",
                    "Quantity": "5\u00a0052",
                    "QuantityValue": 5052.0,
                    "Quote": "4,1265",
                    "ValueInEuro": "20\u00a0847,08 \u20ac",
                    "ValueInEuroRaw": 20847.08,
                    "HistoricQuote": "3,68289",
                    "HistoricValue": "18\u00a0605,95 \u20ac",
                    "HistoricValueInEuro": "18\u00a0605,95 \u20ac",
                    "ResultValueInEuro": "2\u00a0241,12 \u20ac",
                    "ResultPercentageInEuro": "12,05 %",
                    "ValueInSecurityCurrency": "20\u00a0847,08 \u20ac",
                    "Difference": "-0,0285",
                    "DifferencePercentage": "-0,69 %",
                    "ResultValueInSecurityCurrency": "2\u00a0241,12 \u20ac",
                    "ResultPercentageInSecurityCurrency": "12,05 %",
                    "DayResultInEuro": "-166,72 \u20ac",
                    "LowestPrice": "4,1294",
                    "HighestPrice": "4,141",
                    "OpeningPrice": "4,1305",
                    "ClosingPrice": "4,1595",
                    "IsinCode": "LU1681045370",
                    "SecurityCategory": "ETF",
                },
            '''
    @method
    class iter_investment(DictElement):
        item_xpath = 'PortfolioOverviewGroups/*/Items'

        class item(ItemElement):
            klass = Investment
            obj_id = Dict('SecurityId')
            obj_label = Dict('SecurityName')
            obj_code = Dict('IsinCode')
            obj_code_type = Investment.CODE_TYPE_ISIN
            obj_quantity = CleanDecimal(Dict('QuantityValue'))
            obj_unitprice = CleanDecimal(Dict('HistoricQuote'), replace_dots=True)
            obj_unitvalue = CleanDecimal(Dict('Quote'), replace_dots=True)
            obj_valuation = CleanDecimal(Dict('ValueInEuroRaw'))
            obj_diff = CleanDecimal(Dict('ResultValueInEuro'), replace_dots=True)
            obj_diff_percent = CleanDecimal(Dict('ResultPercentageInEuro'), replace_dots=True)
            obj_original_currency = Currency(Dict('CurrencyCode'))
            obj_original_valuation = CleanDecimal(Dict('ValueInSecurityCurrency'), replace_dots=True)
            obj_original_diff = CleanDecimal(Dict('ResultValueInSecurityCurrency'), replace_dots=True)

