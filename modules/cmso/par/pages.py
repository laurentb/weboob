# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


import re, requests, json
import datetime as dt
from collections import OrderedDict

from weboob.browser.pages import HTMLPage, JsonPage, RawPage, LoggedPage, pagination
from weboob.browser.elements import DictElement, ItemElement, TableElement, SkipItem, method
from weboob.browser.filters.standard import CleanText, Upper, Date, Regexp, Format, CleanDecimal, Filter, Env, Slugify, Field
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.browser.exceptions import ServerError
from weboob.capabilities.bank import Account, Investment, Loan
from weboob.capabilities.contact import Advisor
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.exceptions import BrowserIncorrectPassword

def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    pass


class LogoutPage(RawPage):
    pass


class InfosPage(LoggedPage, HTMLPage):
    def get_typelist(self):
        url = Attr(None, 'src').filter(self.doc.xpath('//script[contains(@src, "comptes/scripts")]'))
        m = re.search('synthesecomptes[^\w]+([^:]+)[^\w]+([^"]+)', self.browser.open(url).content)
        return {m.group(1): m.group(2)}


class AccountsPage(LoggedPage, JsonPage):
    TYPES = OrderedDict([('courant',             Account.TYPE_CHECKING),
                         ('pee',                 Account.TYPE_PEE),
                         ('epargne en actions',  Account.TYPE_PEA),
                         ('pea',                 Account.TYPE_PEA),
                         ('preference',          Account.TYPE_LOAN),
                         ('livret',              Account.TYPE_SAVINGS),
                         ('vie',                 Account.TYPE_LIFE_INSURANCE),
                         ('previ_option',        Account.TYPE_LIFE_INSURANCE),
                         ('actions',             Account.TYPE_MARKET),
                         ('titres',              Account.TYPE_MARKET),
                         ('ldd cm',              Account.TYPE_SAVINGS),
                         ('librissime',          Account.TYPE_SAVINGS),
                         ('epargne logement',    Account.TYPE_SAVINGS),
                         ('plan bleu',           Account.TYPE_SAVINGS),
                       ])

    def get_keys(self):
        """Returns the keys for which the value is a list or dict"""
        if "exception" in self.doc:
            return []
        return [k for k, v in self.doc.items() if v and isinstance(v, (dict, list))]

    def check_response(self):
        if "exception" in self.doc:
            raise BrowserIncorrectPassword("Vous n'avez pas de comptes sur l'espace particulier de ce site.")

    def get_numbers(self):
        keys = self.get_keys()
        numbers = {}
        for key in keys:
            if isinstance(self.doc[key], dict):
                keys = [k for k in self.doc[key] if isinstance(k, unicode)]
                contracts = [v for v in self.doc[key][k] for k in keys]
            else:
                contracts = [v for v in self.doc[key]]
            numbers.update({c['index']: c['numeroContratSouscrit'] for c in contracts})
        return numbers

    @method
    class iter_accounts(DictElement):
        def parse(self, el):
            self.item_xpath = "%s/*" % Env('key')(self)

        def find_elements(self):
            selector = self.item_xpath.split('/')
            for el in selector:
                if isinstance(self.el, dict) and el == '*' and self.el.values():
                    self.el = self.el.values()[0]
                if el == '*':
                    continue
                self.el = self.el[el]
            for el in self.el:
                yield el

        class item(ItemElement):
            klass = Account

            condition = lambda self: "LIVRET" not in Dict('accountType')(self.el)

            obj_id = Dict('numeroContratSouscrit')
            obj_label = Upper(Dict('lib'))
            obj_currency =  Dict('deviseCompteCode')
            obj_coming = CleanDecimal(Dict('AVenir', default=None), default=NotAvailable)
            # Iban is available without last 5 numbers, or by sms
            obj_iban = NotAvailable
            obj__index = Dict('index')

            def obj_balance(self):
                balance = CleanDecimal(Dict('soldeEuro', default="0"))(self)
                return -abs(balance) if Field('type')(self) == Account.TYPE_LOAN else balance

            def obj_type(self):
                return self.page.TYPES.get(Dict('accountType', default=None)(self).lower(), Account.TYPE_UNKNOWN)

    @method
    class iter_savings(DictElement):
        @property
        def item_xpath(self):
            return "%s/*/savingsProducts" % Env('key')(self)

        # the accounts really are deeper, but the account type is in a middle-level
        class iter_accounts(DictElement):
            item_xpath = 'savingsAccounts'

            def parse(self, el):
                # accounts may have a user-entered label, so it shouldn't be relied too much on for parsing the account type
                self.env['type_label'] = el['libelleProduit']

            class item(ItemElement):
                klass = Account

                obj_label = Upper(Dict('libelleContrat'))
                obj_balance = CleanDecimal(Dict('solde', default="0"))
                obj_currency = u'EUR'
                obj_coming = CleanDecimal(Dict('AVenir', default=None), default=NotAvailable)
                obj__index = Dict('index')
                obj__owner = Dict('nomTitulaire')

                def obj_id(self):
                    type = Field('type')(self)
                    if type == Account.TYPE_LIFE_INSURANCE:
                        return self.get_lifenumber()
                    elif type in (Account.TYPE_PEA, Account.TYPE_MARKET):
                        return self.get_market_number()

                    try:
                        return Env('numbers')(self)[Dict('index')(self)]
                    except KeyError:
                        # index often changes, so we can't use it... and have to do something ugly
                        return Slugify(Format('%s-%s', Dict('libelleContrat'), Dict('nomTitulaire')))(self)

                def obj_type(self):
                    for key in self.page.TYPES:
                        if key in Env('type_label')(self).lower():
                            return self.page.TYPES[key]
                    return Account.TYPE_UNKNOWN

                def get_market_number(self):
                    label = Field('label')(self)
                    page = self.page.browser._go_market_history()
                    return page.get_account_id(label, Field('_owner')(self))

                def get_lifenumber(self):
                    index = Dict('index')(self)
                    data = json.loads(self.page.browser.lifeinsurance.open(accid=index).content)
                    if not data:
                        raise SkipItem('account seems unavailable')
                    url = data['url']
                    page = self.page.browser.open(url).page
                    return page.get_account_id()

    @method
    class iter_loans(DictElement):
        def parse(self, el):
            self.item_xpath = Env('key')(self)
            if "Pret" in Env('key')(self):
                self.item_xpath = "%s/*/lstPret" % self.item_xpath

        class item(ItemElement):
            klass = Loan

            def obj_id(self):
                # it seems that if we don't have "numeroContratSouscrit", "identifiantTechnique" is unique : only this direction !
                return Dict('numeroContratSouscrit', default=None)(self) or Dict('identifiantTechnique')(self)

            obj_label = Dict('libelle')
            obj_currency = u'EUR'
            obj_type = Account.TYPE_LOAN

            def obj_total_amount(self):
                # Json key change depending on loan type, consumer credit or revolving credit
                if 'montantEmprunte' in self.page.text:
                    return Dict('montantEmprunte')(self)
                else:
                    return Dict('montantUtilise')(self)

            # Key not always available, when revolving credit not yet consummed
            obj_next_payment_amount = Dict('montantProchaineEcheance', default=NotAvailable)

            # obj_rate = can't find the info on website except pdf :(

            # Dates scraped are timestamp, to remove last '000' we divide by 1000
            def obj_maturity_date(self):
                # Key not always available, when revolving credit not yet consummed
                if 'dateFin' in self.page.text:
                    return dt.date.fromtimestamp(Dict('dateFin')(self)/1000)
                else:
                    return NotAvailable

            def obj_next_payment_date(self):
                # Key not always available, when revolving credit not yet consummed
                if 'dateProchaineEcheance' in self.page.text:
                    return dt.date.fromtimestamp(Dict('dateProchaineEcheance')(self)/1000)
                else:
                    return NotAvailable

            def obj_balance(self):
                return -abs(CleanDecimal().filter(Dict('montantRestant', default=None)(self) or Dict('montantUtilise')(self)))

            # only for revolving loans
            obj_available_amount = CleanDecimal(Dict('montantDisponible', default=NotAvailable), default=NotAvailable)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^CARTE (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'), FrenchTransaction.TYPE_CARD),
                (re.compile(u'^(?P<text>(PRLV|PRELEVEMENTS).*)'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>RET DAB.*)'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^(?P<text>ECH.*)'), FrenchTransaction.TYPE_LOAN_PAYMENT),
                (re.compile(u'^(?P<text>VIR.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^(?P<text>ANN.*)'), FrenchTransaction.TYPE_PAYBACK),
                (re.compile(u'^(?P<text>(VRST|VERSEMENT).*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK)
               ]


class HistoryPage(LoggedPage, JsonPage):
    def has_deferred_cards(self):
        return Dict('pendingDeferredDebitCardList/currentMonthCardList', default=None)

    def get_keys(self):
        if 'exception' in self.doc:
            return []
        return [k for k, v in self.doc.items() if v and isinstance(v, (dict, list))]

    @pagination
    @method
    class iter_history(DictElement):
        def next_page(self):
            if len(Env('nbs', default=[])(self)):
                data = {'index': Env('index')(self),
                        'filtreOperationsComptabilisees': "MOIS_MOINS_%s" % Env('nbs')(self)[0]
                       }
                Env('nbs')(self).pop(0)
                return requests.Request('POST', data=json.dumps(data), headers={'Content-Type': 'application/json'})

        def parse(self, el):
            # Key only if coming
            key = Env('key', default=None)(self)
            self.item_xpath = "%s/operationList" % key if key and "CardList" not in key else \
                              "%s/currentMonthCardList/*/listeOperations" % key if key else \
                              "listOperationProxy"

        class item(ItemElement):
            klass = Transaction

            class FromTimestamp(Filter):
                def filter(self, timestamp):
                    return dt.date.fromtimestamp(int(timestamp[:-3]))

            obj_date = FromTimestamp(Dict('dateOperation'))
            obj_raw = Transaction.Raw(Dict('libelleCourt'))
            obj_vdate = Date(Dict('dateValeur'), dayfirst=True)
            obj_amount = CleanDecimal(Dict('montantEnEuro'), default=NotAvailable)

            def parse(self, el):
                key = Env('key', default=None)(self)
                if key and "DeferredDebit" in key:
                    for x in Dict('%s/currentMonthCardList' % key)(self.page.doc):
                        deferred_date = Dict('dateDiffere', default=None)(x)
                        if deferred_date:
                            break
                    setattr(self.obj, '_deferred_date', self.FromTimestamp().filter(deferred_date))

                # Skip duplicate transactions
                amount = Dict('montantEnEuro', default=None)(self)
                tr = Dict('libelleCourt')(self) + Dict('dateOperation')(self) + str(amount)
                if amount is None or (tr in self.page.browser.trs['list'] and self.page.browser.trs['lastdate'] <= Field('date')(self)):
                    raise SkipItem()

                self.page.browser.trs['lastdate'] = Field('date')(self)
                self.page.browser.trs['list'].append(tr)


class LifeinsurancePage(LoggedPage, HTMLPage):
    def get_account_id(self):
        return re.sub(r'\s', '', Regexp(CleanText('//h1[@class="portlet-title"]'), ur'n° ([\d\s]+)')(self.doc))

    def get_link(self, page):
        return Link(default=NotAvailable).filter(self.doc.xpath(u'//a[contains(text(), "%s")]' % page))

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr[contains(@class, "results")]'
        head_xpath = '//table/thead/tr/th'

        col_date = re.compile('Date')
        col_label = re.compile(u'Libellé')
        col_amount = re.compile('Montant')

        next_page = Link('//a[contains(text(), "Suivant") and not(contains(@href, "javascript"))]', default=None)

        class item(ItemElement):
            klass = Transaction

            obj_raw = Transaction.Raw(TableCell('label'))
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = MyDecimal(TableCell('amount'))

    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tbody/tr[contains(@class, "results")]'
        head_xpath = '//table/thead/tr/th'

        col_label = re.compile(u'Libellé')
        col_quantity = re.compile('Nb parts')
        col_vdate = re.compile('Date VL')
        col_unitvalue = re.compile('VL')
        col_unitprice = re.compile('Prix de revient')
        col_valuation = re.compile('Solde')

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_code = Regexp(Link('./td/a'), 'Isin%253D([^%]+)')
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_unitprice = MyDecimal(TableCell('unitprice'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)


class MarketPage(LoggedPage, HTMLPage):
    def find_account(self, acclabel, accowner):
        accowner = sorted(accowner.lower().split()) # first name and last name may not be ordered the same way on market site...

        # Check if history is present
        if CleanText(default=None).filter(self.doc.xpath('//body/p[contains(text(), "indisponible pour le moment")]')):
            return False

        ids = None
        for a in self.doc.xpath('//a[contains(@onclick, "indiceCompte")]'):
            self.logger.debug("get investment from onclick")

            label = CleanText('.')(a)
            owner = CleanText('./ancestor::tr/preceding-sibling::tr[@class="LnMnTiers"][1]')(a)
            owner = sorted(owner.lower().split())

            if label == acclabel and owner == accowner:
                ids = list(re.search(r'indiceCompte[^\d]+(\d+).*idRacine[^\d]+(\d+)', Attr('.', 'onclick')(a)).groups())
                ids.append(CleanText('./ancestor::td/preceding-sibling::td')(a))
                self.logger.debug("assign value to ids: {}".format(ids))
                return ids

        for a in self.doc.xpath('//a[contains(@href, "indiceCompte")]'):
            self.logger.debug("get investment from href")
            if CleanText('.')(a) == acclabel:
                ids = list(re.search(r'indiceCompte[^\d]+(\d+).*idRacine[^\d]+(\d+)', Attr('.', 'href')(a)).groups())
                ids.append(CleanText('./ancestor::td/preceding-sibling::td')(a))
                self.logger.debug("assign value to ids: {}".format(ids))
                return ids

    def get_account_id(self, acclabel, owner):
        return self.find_account(acclabel, owner)[2].replace(' ', '')

    def go_account(self, acclabel, owner):
        ids = self.find_account(acclabel, owner)
        if not ids:
            return

        form = self.get_form(name="formCompte")
        form['indiceCompte'] = ids[0]
        form['idRacine'] = ids[1]
        try:
            return form.submit()
        except ServerError:
            return False

    def go_account_full(self):
        form = self.get_form(name="formOperation")
        form['dateDebut'] = "02/01/1970"
        try:
            return form.submit()
        except ServerError:
            return False

    @method
    class iter_history(TableElement):
        item_xpath = '//table[has-class("domifrontTb")]/tr[not(has-class("LnTit") or has-class("LnTot"))]'
        head_xpath = '//table[has-class("domifrontTb")]/tr[1]/td'

        col_date = re.compile('Date')
        col_label = u'Opération'
        col_code = u'Code'
        col_quantity = u'Quantité'
        col_amount = re.compile('Montant')

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_type = Transaction.TYPE_BANK
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = CleanDecimal(TableCell('amount'))
            obj_investments = Env('investments')

            def parse(self, el):
                i = Investment()
                i.label = Field('label')(self)
                i.code = CleanText(TableCell('code'))(self)
                i.quantity = MyDecimal(TableCell('quantity'))(self)
                i.valuation = Field('amount')(self)
                i.vdate = Field('date')(self)
                self.env['investments'] = [i]

    @method
    class iter_investment(TableElement):
        item_xpath = '//table/tr[not(has-class("LnTit") or has-class("LnTot"))]'
        head_xpath = '//table/tr[1]/td'

        col_label = u'Valeur'
        col_code = u'Code'
        col_quantity = u'Qté'
        col_vdate = u'Date cours'
        col_unitvalue = u'Cours'
        col_unitprice = re.compile('P.R.U')
        col_valuation = u'Valorisation'

        class item(ItemElement):
            klass = Investment

            condition = lambda self: not CleanText('//div[has-class("errorConteneur")]', default=None)(self.el)

            obj_label = Upper(TableCell('label'))
            obj_code = CleanText(TableCell('code'))
            obj_quantity = CleanDecimal(TableCell('quantity'), default=NotAvailable)
            obj_unitprice = MyDecimal(TableCell('unitprice'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = CleanDecimal(TableCell('valuation'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True, default=NotAvailable)


class AdvisorPage(LoggedPage, JsonPage):
    @method
    class get_advisor(ItemElement):
        klass = Advisor

        obj_name = Dict('nomPrenom')
        obj_email = obj_mobile = NotAvailable

        def obj_phone(self):
            return Dict('numeroTelephone')(self) or NotAvailable

    @method
    class update_agency(ItemElement):
        obj_fax = CleanText(Dict('numeroFax'), replace=[(' ', '')])
        obj_agency = Dict('nom')
        obj_address = Format('%s %s', Dict('adresse1'), Dict('adresse3'))


class RecipientsPage(LoggedPage, JsonPage):
    def get_numbers(self):
        return {
            d['index']: d['numeroContratSouscrit']
            for d in self.doc['listCompteTitulaireCotitulaire']
        }
