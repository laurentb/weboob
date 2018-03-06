# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Nicolas Duhamel
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

from io import BytesIO
import re
from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Loan
from weboob.capabilities.contact import Advisor
from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.pages import LoggedPage, RawPage, PartialHTMLPage, HTMLPage
from weboob.browser.filters.html import Link, TableCell
from weboob.browser.filters.standard import CleanText, CleanDecimal, Regexp, Env, Field, BrowserURL, Currency, \
    Async, Date
from weboob.exceptions import BrowserUnavailable
from weboob.tools.compat import urljoin, unicode

from .base import MyHTMLPage


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)

def MyDate(*args, **kwargs):
    kwargs.update(dayfirst=True, default=NotAvailable)
    return Date(*args, **kwargs)


class item_account_generic(ItemElement):
    klass = Account

    def condition(self):
        return len(self.el.xpath('.//span[@class="number"]')) > 0

    obj_id = CleanText('.//abbr/following-sibling::text()')
    obj_currency = Currency('.//span[@class="number"]')

    def obj_url(self):
        url = Link(u'./a', default=NotAvailable)(self)
        if url:
            return urljoin(self.page.url, url)
        return url

    def obj_label(self):
        return CleanText('.//div[@class="title"]/h3')(self).upper()

    def obj_balance(self):
        if Field('type')(self) == Account.TYPE_LOAN:
            return -abs(CleanDecimal('.//span[@class="number"]', replace_dots=True)(self))
        return CleanDecimal('.//span[@class="number"]', replace_dots=True, default=NotAvailable)(self)

    def obj_coming(self):
        if Field('type')(self) == Account.TYPE_CHECKING:
            has_coming = False
            coming = 0

            coming_operations = self.page.browser.open(
                BrowserURL('par_account_checking_coming', accountId=Field('id'))(self))

            if CleanText('//span[@id="amount_total"]')(coming_operations.page.doc):
                has_coming = True
                coming += CleanDecimal('//span[@id="amount_total"]', replace_dots=True)(coming_operations.page.doc)

            if CleanText(u'.//dt[contains(., "Débit différé à débiter")]')(self):
                has_coming = True
                coming += CleanDecimal(u'.//dt[contains(., "Débit différé à débiter")]/following-sibling::dd[1]',
                                       replace_dots=True)(self)

            return coming if has_coming else NotAvailable
        return NotAvailable

    def obj_iban(self):
        response = self.page.browser.open(
                '/voscomptes/canalXHTML/comptesCommun/imprimerRIB/init-imprimer_rib.ea?numeroCompte=%s' % Field('id')(
                self))
        return response.page.get_iban()

    def obj_type(self):
        types = {'comptes? bancaires?': Account.TYPE_CHECKING,
                 'livrets?': Account.TYPE_SAVINGS,
                 'epargnes? logement': Account.TYPE_SAVINGS,
                 "autres produits d'epargne": Account.TYPE_SAVINGS,
                 'comptes? titres? et pea': Account.TYPE_MARKET,
                 'compte-titres': Account.TYPE_MARKET,
                 'assurances? vie et retraite': Account.TYPE_LIFE_INSURANCE,
                 u'prêt': Account.TYPE_LOAN,
                 u'crédits?': Account.TYPE_LOAN,
                 'plan d\'epargne en actions': Account.TYPE_PEA
                 }

        # first trying to match with label
        label = Field('label')(self)
        for atypetxt, atype in types.items():
            if re.findall(atypetxt, label.lower()):  # match with/without plurial in type
                return atype
        # then by type
        type = Regexp(CleanText('../../preceding-sibling::div[@class="avoirs"][1]/span[1]'), r'(\d+) (.*)', '\\2')(self)
        for atypetxt, atype in types.items():
            if re.findall(atypetxt, type.lower()):  # match with/without plurial in type
                return atype

        return Account.TYPE_UNKNOWN

    def obj__has_cards(self):
        return Link(u'.//a[contains(., "Débit différé")]', default=None)(self)


class AccountList(LoggedPage, MyHTMLPage):
    def on_load(self):
        MyHTMLPage.on_load(self)

        if self.doc.xpath(u'//h2[text()="ERREUR"]'): # website sometime crash
            self.browser.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/securite/authentification/initialiser-identif.ea')

            raise BrowserUnavailable()

    @property
    def no_accounts(self):
        return len(self.doc.xpath('//iframe[contains(@src, "/comptes_contrats/sans_")] |\
                                   //iframe[contains(@src, "bel_particuliers/prets/prets_nonclient")]')) > 0

    @property
    def has_mandate_management_space(self):
        return len(self.doc.xpath(u'//a[@title="Accéder aux Comptes Gérés Sous Mandat"]')) > 0

    def mandate_management_space_link(self):
        return Link(u'//a[@title="Accéder aux Comptes Gérés Sous Mandat"]')(self.doc)

    @method
    class iter_accounts(ListElement):
        item_xpath = u'//ul/li//div[contains(@class, "account-resume")]'
        class item_account(item_account_generic):
            def condition(self):
                return item_account_generic.condition(self)

    @method
    class iter_revolving_loans(ListElement):
        item_xpath = '//div[@class="bloc Tmargin"]//dl'

        class item_account(ItemElement):
            klass = Loan

            obj_id = CleanText('./dd[1]//em')
            obj_label = 'Crédit renouvelable'
            obj_total_amount = MyDecimal('./dd[2]/span')
            obj_used_amount = MyDecimal('./dd[3]/span')
            obj_available_amount = MyDecimal('./dd[4]//em')
            obj_insurance_label = CleanText('./dd[5]//em', children=False)
            obj__has_cards = False
            obj_type = Account.TYPE_LOAN

            def obj_url(self):
                return self.page.url

    @method
    class iter_loans(TableElement):
        head_xpath = '//table[@id="pret"]/thead//th'
        item_xpath = '//table[@id="pret"]/tbody/tr'

        col_label = u'Numéro du prêt'
        col_total_amount = u'Montant initial emprunté'
        col_subscription_date = u'MONTANT INITIAL EMPRUNTÉ'
        col_next_payment_amount = u'Montant prochaine échéance'
        col_next_payment_date = u'Date prochaine échéance'
        col_balance = re.compile('Capital')
        col_maturity_date = re.compile(u'Date dernière')

        class item_loans(ItemElement):
            # there is two cases : the mortgage and the consumption loan. These cases have differents way to get the details
            klass = Loan

            def condition(self):
                return CleanText(TableCell('balance'))(self) != u'Prêt non débloqué'

            def load_details(self):
                url = Link('.//a', default=NotAvailable)(self)
                return self.page.browser.async_open(url=url)

            obj_total_amount = CleanDecimal(TableCell('total_amount'), replace_dots=True)

            def obj_id(self):
                if TableCell('label', default=None)(self):
                    return Regexp(CleanText(Field('label'), default=NotAvailable), '- (\w{16})')(self)
                return CleanText('//form[@id="selection_offre"]/div[@class="bloc Tmargin"]/div[@class="formline"][2]/span/strong')(self)

            obj_type = Account.TYPE_LOAN

            def obj_label(self):
                cell = TableCell('label', default=None)(self)
                if cell:
                    return CleanText(cell, default=NotAvailable)(self)
                return CleanText('//form[@id="selection_offre"]/div[@class="bloc Tmargin"]/h2[@class="title-level2"]')(self)

            def obj_balance(self):
                if CleanText(TableCell('balance'))(self) != u'Remboursé intégralement':
                    return -abs(CleanDecimal(TableCell('balance'), replace_dots=True)(self))
                return Decimal(0)

            def obj_subscription_date(self):
                xpath = '//form[@id="selection_offre"]/div[1]/div[2]/span'
                if 'souscrite le' in CleanText(xpath)(self):
                    return MyDate(Regexp(CleanText(xpath), ' (\d{2}/\d{2}/\d{4})', default=NotAvailable))(self)
                return NotAvailable

            obj_next_payment_amount = CleanDecimal(TableCell('next_payment_amount'), replace_dots=True, default=NotAvailable)

            def obj_maturity_date(self):
                if Field('subscription_date')(self):
                    async_page = Async('details').loaded_page(self)
                    date = MyDate(CleanText('//div[@class="bloc Tmargin"]/dl[2]/dd[4]', default=NotAvailable))(async_page.doc)
                    return date
                return MyDate(CleanText(TableCell('maturity_date')), default=NotAvailable)(self)

            def obj_last_payment_date(self):
                xpath = '//div[@class="bloc Tmargin"]/div[@class="formline"][2]/span'
                if 'dont le dernier' in CleanText(xpath)(self):
                    return MyDate(Regexp(CleanText(xpath), ' (\d{2}/\d{2}/\d{4})', default=NotAvailable))(self)
                async_page = Async('details').loaded_page(self)
                return MyDate(CleanText('//div[@class="bloc Tmargin"]/dl[1]/dd[2]'), default=NotAvailable)(async_page.doc)

            obj_next_payment_date = MyDate(CleanText(TableCell('next_payment_date')), default=NotAvailable)

            def obj_url(self):
                url = Link(u'.//a', default=None)(self)
                if url:
                    return urljoin(self.page.url, url)
                return self.page.url

            obj__has_cards = False


class Advisor(LoggedPage, MyHTMLPage):
    @method
    class get_advisor(ItemElement):
        klass = Advisor

        obj_name = Env('name')
        obj_phone = Env('phone')
        obj_mobile = Env('mobile', default=NotAvailable)
        obj_agency = Env('agency', default=NotAvailable)
        obj_email = NotAvailable

        def obj_address(self):
            return CleanText('//div[h3[contains(text(), "Bureau")]]/div[not(@class)][position() > 1]')(self) or NotAvailable

        def parse(self, el):
            # we have two kinds of page and sometimes we don't have any advisor
            agency_phone = CleanText('//span/a[contains(@href, "rendezVous")]', replace=[(' ', '')], default=NotAvailable)(self) or \
                           CleanText('//div[has-class("lbp-numero")]/span', replace=[(' ', '')], default=NotAvailable)(self)
            advisor_phone = Regexp(CleanText('//div[h3[contains(text(), "conseil")]]//span[2]', replace=[(' ', '')], default=""), '(\d+)', default="")(self)
            if advisor_phone.startswith(("06", "07")):
                self.env['phone'] = agency_phone
                self.env['mobile'] = advisor_phone
            else:
                self.env['phone'] = advisor_phone or agency_phone

            agency = CleanText('//div[h3[contains(text(), "Bureau")]]/div[not(@class)][1]')(self) or NotAvailable
            name = CleanText('//div[h3[contains(text(), "conseil")]]//span[1]', default=None)(self) or \
                   CleanText('//div[@class="lbp-font-accueil"]/div[2]/div[1]/span[1]', default=None)(self)
            if name:
                self.env['name'] = name
                self.env['agency'] = agency
            else:
                self.env['name'] = agency


class AccountRIB(LoggedPage, RawPage):
    iban_regexp = r'[A-Z]{2}\d{12}[0-9A-Z]{11}\d{2}'

    def __init__(self, *args, **kwargs):
        super(AccountRIB, self).__init__(*args, **kwargs)

        self.parsed_text = b''

        try:
            try:
                from pdfminer.pdfdocument import PDFDocument
                from pdfminer.pdfpage import PDFPage
                newapi = True
            except ImportError:
                from pdfminer.pdfparser import PDFDocument
                newapi = False
            from pdfminer.pdfparser import PDFParser, PDFSyntaxError
            from pdfminer.converter import TextConverter
            from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
        except ImportError:
            self.logger.warning('Please install python-pdfminer to get IBANs')
        else:
            parser = PDFParser(BytesIO(self.doc))
            try:
                if newapi:
                    doc = PDFDocument(parser)
                else:
                    doc = PDFDocument()
                    parser.set_document(doc)
                    doc.set_parser(parser)
            except PDFSyntaxError:
                return

            rsrcmgr = PDFResourceManager()
            out = BytesIO()
            device = TextConverter(rsrcmgr, out)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            if newapi:
                pages = PDFPage.create_pages(doc)
            else:
                doc.initialize()
                pages = doc.get_pages()
            for page in pages:
                interpreter.process_page(page)

            self.parsed_text = out.getvalue()

    def get_iban(self):
        m = re.search(self.iban_regexp, self.parsed_text.decode('utf-8'))
        if m:
            return unicode(m.group(0))
        return None


class MarketLoginPage(LoggedPage, PartialHTMLPage):
    def on_load(self):
        self.get_form(id='autoSubmit').submit()


class UselessPage(LoggedPage, HTMLPage):
    pass
