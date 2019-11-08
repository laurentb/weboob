# coding: utf-8
from __future__ import unicode_literals

import re
from decimal import Decimal

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Investment, AccountNotFound
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.pages import HTMLPage, LoggedPage, FormNotFound
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Field, Regexp, Eval, Date
)
from weboob.browser.filters.html import Link, XPathNotFound, TableCell
from weboob.browser.filters.javascript import JSVar

from .account_pages import Transaction

""" Life insurance subsite related pages """


class LITransaction(FrenchTransaction):

    PATTERNS = [
        (re.compile(r'^(?P<text>Arbitrage.*)'), FrenchTransaction.TYPE_ORDER),
        (re.compile(r'^(?P<text>Versement.*)'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile(r'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
    ]


class LifeInsurancePortal(LoggedPage, HTMLPage):
    def is_here(self):
        try:
            self.get_form(name='FORM_ERISA')
        except FormNotFound:
            return False
        return True

    def on_load(self):
        self.logger.debug('automatically following form')
        form = self.get_form(name='FORM_ERISA')
        form['token'] = JSVar(CleanText('//script'), var='document.FORM_ERISA.token.value')(self.doc)
        form.submit()


class LifeInsuranceMain(LoggedPage, HTMLPage):
    def on_load(self):
        self.logger.debug('automatically following form')
        form = self.get_form(name='formAccueil')
        form.url = 'https://assurances.hsbc.fr/navigation'
        form.submit()


class LifeInsurancesPage(LoggedPage, HTMLPage):
    @method
    class iter_history(TableElement):
        head_xpath = '(//table)[1]/thead/tr/th'
        item_xpath = '(//table)[1]/tbody/tr'

        col_label = "Actes"
        col_date = "Date d'effet"
        col_amount = "Montant net"
        col_gross_amount = "Montant brut"

        class item(ItemElement):
            klass = LITransaction

            obj_raw = LITransaction.Raw(CleanText(TableCell('label')))
            obj_date = Date(CleanText(TableCell('date')))
            obj_amount = Transaction.Amount(TableCell('amount'), TableCell('gross_amount'), replace_dots=False)

    @method
    class iter_investments(TableElement):
        head_xpath = '//div[contains(., "Détail de vos supports")]/following-sibling::div/table/thead/tr/th'
        item_xpath = '//div[contains(., "Détail de vos supports")]/following-sibling::div/table\
                      /tbody/tr[not(contains(@class, "light-yellow"))]'

        col_label = "Support"
        col_vdate = "Date de valorisation *"
        col_quantity = ["Nombre d'unités de compte", re.compile("Nombre de parts")]
        col_portfolio_share = "Répartition"
        col_unitvalue = ["Valeur liquidative", re.compile("Valeur de la part")]
        col_support_value = re.compile("Valeur support")

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_vdate = Date(CleanText(TableCell('vdate')), dayfirst=True)
            obj_portfolio_share = Eval(lambda x: x / 100, CleanDecimal(TableCell('portfolio_share')))
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), default=Decimal('1'))
            obj_valuation = CleanDecimal(TableCell('support_value'))

            def obj_code(self):
                if "Fonds en euros" in Field('label')(self):
                    return NotAvailable
                return Regexp(Link('.//a'), r'javascript:openSupportPerformanceWindow\(\'(.*?)\', \'(.*?)\'\)', '\\2')(self)

            def obj_quantity(self):
                # default for euro funds
                return CleanDecimal(TableCell('quantity'), default=CleanDecimal(TableCell('support_value'))(self))(self)

            def condition(self):
                return len(self.el.xpath('.//td')) > 1

    def get_lf_attributes(self, lfid):
        attributes = {}

        # values can be in JS var format but it's not mandatory param so we don't go to get the real value
        try:
            values = Regexp(Link('//a[contains(., "%s")]' % lfid[:-3].lstrip('0')), r'\((.*?)\)')(self.doc).replace(' ', '').replace('\'', '').split(',')
        except XPathNotFound:
            raise AccountNotFound('cannot find account id %s on life insurance site' % lfid)
        keys = Regexp(CleanText('//script'), r'consultationContrat\((.*?)\)')(self.doc).replace(' ', '').split(',')

        attributes = dict(zip(keys, values))
        return attributes

    def disconnect(self):
        self.get_form(name='formDeconnexion').submit()


class LifeInsuranceUseless(LoggedPage, HTMLPage):
    is_here = '//h1[text()="Assurance Vie"]'


class LifeNotFound(LoggedPage, HTMLPage):
    pass
