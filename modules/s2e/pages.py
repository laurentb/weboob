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


import re, requests
from cStringIO import StringIO
from decimal import Decimal

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ItemElement, TableElement, SkipItem, method
from weboob.browser.filters.standard import CleanText, Date, Regexp, Eval, CleanDecimal, Env, TableCell, Field
from weboob.browser.filters.html import Attr
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard
from weboob.exceptions import NoAccountsException


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class S2eVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0':'8adee734aaefb163fb008d26bb9b3a42',
               '1':'b815d6ce999910d48619b5912b81ddf1',
               '2':'54255a70694787a4e1bd7dd473b50228',
               '3':'ba06373d2bfba937d00bf52a31d475eb',
               '4':'3fa795ac70247922048c514115487b10',
               '5':'788963d15fa05832ee7640f7c2a21bc3',
               '6':'c8bf62dfaed9feeb86934d8617182503',
               '7':'f7543fdda3039bdd383531954dd4fc46',
               '8':'5c4210e2d8e39f7667d7a9e5534b18b7',
               '9':'94520ac801883fbfb700f43cd4172d41'
              }

    color = (0, 0, 0)

    def __init__(self, page, vkid):
        img = page.doc.find('//img[@id="clavier_virtuel"]')
        res = page.browser.open("/portal/rest/clavier_virtuel/%s" % vkid)
        MappedVirtKeyboard.__init__(self, StringIO(res.content), page.doc, img, self.color, convert='RGB')
        self.check_symbols(self.symbols, None)

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        m = re.search('(\d+)', code)
        if m:
            return m.group(1)

    def get_string_code(self, string):
        return ''.join([self.get_symbol_code(self.symbols[c]) for c in string])


class LoginPage(HTMLPage):
    def get_password(self, password, secret):
        vkid = Attr('//input[@id="identifiantClavierVirtuel"]', 'value')(self.doc)
        code = S2eVirtKeyboard(self, vkid).get_string_code(password)
        tcc = Attr('//input[@id="codeTCC"]', 'value')(self.doc)
        password = "%s|%s|#%s#" % (code, vkid, tcc)
        if secret:
            password = "%s%s" % (password, secret)
        return password

    def login(self, login, password, secret):
        data = {}
        data['initialURI'] = "/portal/private/salarie-%s" % self.browser.SLUG
        data['password'] = self.get_password(password, secret)
        data['username'] = login
        self.browser.location('/portal/login', data=data)

    def get_error(self):
        cgu = CleanText('//h1[contains(text(), "Conditions")]', default=None)(self.doc)
        if cgu:
            cgu = u"Veuillez accepter les conditions générales d'utilisation." if self.browser.LANG == "fr" \
               else "Please accept the general conditions of use." if self.browser.LANG == 'en' \
               else cgu
        return cgu or CleanText('//div[contains(text(), "Erreur")]', default='')(self.doc)


class ItemInvestment(ItemElement):
    klass = Investment

    obj_unitvalue = Env('unitvalue')
    obj_vdate = Env('vdate')

    def obj_label(self):
        return CleanText(TableCell('label')(self)[0].xpath('.//div[contains(@style, \
            "text-align")][1]'))(self).rsplit(' - ', 1)[0]

    def obj_valuation(self):
        return MyDecimal(TableCell('valuation')(self)[0].xpath('.//div[not(.//div)]'))(self)

    def parse(self, el):
        # Trying to find vdate and unitvalue
        unitvalue, vdate = None, None
        for span in TableCell('label')(self)[0].xpath('.//span'):
            if unitvalue is None:
                unitvalue = Regexp(CleanText('.'), '^([\d,]+)$', default=None)(span)
            if vdate is None:
                vdate = None if any(x in CleanText('./parent::div')(span) for x in [u"échéance", "Maturity"]) else \
                        Regexp(CleanText('.'), '^([\d\/]+)$', default=None)(span)
        self.env['unitvalue'] = MyDecimal().filter(unitvalue) if unitvalue else NotAvailable
        self.env['vdate'] = Date(dayfirst=True).filter(vdate) if vdate else NotAvailable


class MultiPage(HTMLPage):
    def get_multi(self):
        return [Attr('.', 'value')(option) for option in \
            self.doc.xpath('//select[@class="ComboEntreprise"]/option')]

    def go_multi(self, id):
        if Attr('//select[@class="ComboEntreprise"]/option[@selected]', 'value')(self.doc) != id:
            form = self.get_form('//select[@class="ComboEntreprise"]/ancestor::form[1]')
            key = [k for k, v in dict(form).iteritems() if "SelectItems" in k][0]
            form[key] = id
            form['javax.faces.source'] = key
            form.submit()


class AccountsPage(LoggedPage, MultiPage):
    def on_load(self):
        no_accounts_message = CleanText('//span[contains(text(), "On this date, you still have no employee savings in this company.")] | \
                        //span[contains(text(), "On this date, you do not yet have any employee savings in this company.")]')(self.doc)
        if no_accounts_message:
            raise NoAccountsException(no_accounts_message)

    TYPES = {'PEE': Account.TYPE_PEE,
             'PEI': Account.TYPE_PEE,
             'PEEG': Account.TYPE_PEE,
             'PEG': Account.TYPE_PEE,
             'PLAN': Account.TYPE_PEE,
             'PERCO': Account.TYPE_PERCO,
             'PERCOI': Account.TYPE_PERCO,
             'SWISS': Account.TYPE_MARKET
            }

    @method
    class iter_accounts(TableElement):
        item_xpath = '//div[contains(@id, "Dispositif")]//table/tbody/tr[td[2]]'
        head_xpath = '//div[contains(@id, "Dispositif")]//table/thead/tr/th'

        col_label = [u'My schemes', u'Mes dispositifs']
        col_balance = [re.compile(u'Total'), re.compile(u'Montant')]

        class item(ItemElement):
            klass = Account

            obj_id = Env('id')
            obj_label = Env('label')

            def obj_type(self):
                return self.page.TYPES.get(Field('label')(self).split()[0].upper(), Account.TYPE_UNKNOWN)

            def obj_balance(self):
                return MyDecimal(TableCell('balance')(self)[0].xpath('.//div[has-class("nowrap")]'))(self)

            def obj_currency(self):
                return Account.get_currency(CleanText(TableCell('balance')(self)[0].xpath('.//div[has-class("nowrap")]'))(self))

            def parse(self, el):
                id, label = CleanText(TableCell('label'))(self).split(' ', 1)
                self.env['id'] = id
                self.env['label'] = label

    def get_investment_pages(self, accid, valuation=True):
        form = self.get_form('//div[@id="operation"]//form')
        div_xpath = '//div[contains(@id, "ongletDetailParSupport")]'
        input_id = Attr('//input[contains(@id, "onglets")]', 'name')(self.doc)
        select_id = Attr('%s//select' % div_xpath, 'id')(self.doc)
        option_value = Attr('//option[contains(text(), "%s")]' % accid, 'value')(self.doc)
        form[select_id] = option_value
        form[input_id] = "onglet2"
        # Select display : amount or quantity
        radio_txt = ("En montant" if valuation else [u"Quantité", "En parts"]) if self.browser.LANG == "fr" else \
                    ("In amount" if valuation else ["Quantity", "In units"])
        if isinstance(radio_txt, list):
            radio_txt = '" or text()="'.join(radio_txt)
        input_id = Regexp(Attr('%s//span[text()="%s"]/preceding-sibling::a[1]' \
            % (div_xpath, radio_txt), 'onclick'), '"([^"]+)')(self.doc)
        form[input_id] = input_id
        form['javax.faces.source'] = input_id
        form['valorisationMontant'] = "true" if valuation else "false"
        data = {k: v for k, v in dict(form).iteritems() if "blocages" not in v}
        self.browser.location(form.url, data=data)

    def update_quantity(self, invs):
        for inv in invs:
            inv.quantity = MyDecimal().filter(CleanText('//div[contains(@id, "ongletDetailParSupport")] \
                 //tr[.//div[contains(text(), "%s")]]/td[last()]//div/text()' % inv.label)(self.doc))
        return invs

    @method
    class iter_investment(TableElement):
        item_xpath = '//div[contains(@id, "ongletDetailParSupport")]//table/tbody/tr[td[4]]'
        head_xpath = '//div[contains(@id, "ongletDetailParSupport")]//table/thead/tr/th'

        col_label = [re.compile(u'My investment'), re.compile(u'Mes supports')]
        col_valuation = [re.compile(u'Gross amount'), re.compile(u'Montant brut')]
        col_portfolio_share = [u'Distribution', u'Répartition']

        class item(ItemInvestment):
            def obj_portfolio_share(self):
                return Eval(lambda x: x / 100, MyDecimal(TableCell('portfolio_share')(self)[0] \
                    .xpath('.//div[has-class("nowrap")]'))(self))(self)


class HistoryPage(LoggedPage, MultiPage):
    XPATH_FORM = '//div[@id="operation"]//form'

    def get_history_form(self, idt, args={}):
        form = self.get_form(self.XPATH_FORM)
        form[idt] = idt
        form['javax.faces.source'] = idt
        form.update(args)
        return form

    def show_more(self, nb):
        form = self.get_form(self.XPATH_FORM)
        for select in self.doc.xpath('//select'):
            if Attr('./option[@selected]', 'value')(select) == nb:
                return
            idt = Attr('.', 'id')(select)
            form[idt] = nb
            if 'javax.faces.source' not in form:
                form['javax.faces.source'] = idt
        form.submit()

    def go_start(self):
        idt = Attr('//a[@title="debut" or @title="precedent"]', 'id', default=None)(self.doc)
        if idt:
            form = self.get_history_form(idt)
            form.submit()

    @method
    class get_investments(TableElement):
        item_xpath = '//table//table/tbody/tr[td[4]]'
        head_xpath = '//table//table/thead/tr/th'

        col_scheme = [u'Scheme', u'Dispositif']
        col_label = [re.compile(u'Investment'), re.compile('My investment'), u'fund', re.compile(u'Support')]
        col_quantity = [re.compile(u'Quantity'), re.compile(u'Quantité'), re.compile('En parts')]
        col_valuation = [u'Gross amount', u'Net amount', re.compile(u'Montant brut'), u'Montant Net']

        class item(ItemInvestment):
            def obj_quantity(self):
                return MyDecimal(TableCell('quantity')(self)[0].xpath('./text()'))(self)

            def condition(self):
                return Env('accid')(self) in CleanText(TableCell('scheme'))(self)

    @pagination
    @method
    class iter_history(TableElement):
        item_xpath = '//table/tbody/tr[td[4]]'
        head_xpath = '//table/thead/tr/th'

        col_id = [re.compile(u'Ref'), re.compile(u'Réf')]
        col_date = [re.compile(u'Date'), re.compile('Creation date')]
        col_label = [re.compile('Transaction'), re.compile(u'Type')]

        def next_page(self):
            idt = Attr('//a[@title="suivant"]', 'id', default=None)(self.page.doc)
            if idt:
                form = self.page.get_history_form(idt)
                return requests.Request("POST", form.url, data=dict(form))

        class item(ItemElement):
            klass = Transaction

            obj_id = CleanText(TableCell('id'))
            obj_label = CleanText(TableCell('label'))
            obj_type = Transaction.TYPE_BANK
            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_amount = Env('amount')
            obj_investments = Env('investments')

            def parse(self, el):
                # We have only one history for all accounts...
                # And we know only on details page if it match current account.
                trid = CleanText(TableCell('id'))(self)
                if trid not in self.page.browser.cache['details']:
                    # Thanks to stateful website : first go on details page...
                    idt = Attr(TableCell('id')(self)[0].xpath('./a'), 'id', default=None)(self)
                    typeop = Regexp(Attr(TableCell('id')(self)[0].xpath('./a'), 'onclick'), 'Operation.+?([A-Z_]+)')(self)
                    form = self.page.get_history_form(idt, {'referenceOp': trid, 'typeOperation': typeop})
                    page = self.page.browser.open(form.url, data=dict(form)).page
                    self.page.browser.cache['details'][trid] = page
                    # ...then go back to history list.
                    idt = Attr('//input[@title="Retour"]', 'id', default=None)(page.doc)
                    form = self.page.get_history_form(idt)
                    self.page.browser.open(form.url, data=dict(form)).page
                else:
                    page = self.page.browser.cache['details'][trid]

                # Check if page is related to the account
                if not len(page.doc.xpath('//td[contains(text(), "%s")]' % Env('accid')(self))):
                    raise SkipItem()

                self.env['investments'] = list(page.get_investments(accid=Env('accid')(self)))
                self.env['amount'] = sum([i.valuation or Decimal('0') for i in self.env['investments']])
