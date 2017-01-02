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


from cStringIO import StringIO
import re
from decimal import Decimal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account
from weboob.capabilities.contact import Advisor
from weboob.browser.elements import ItemElement, method
from weboob.browser.pages import LoggedPage, RawPage
from weboob.browser.filters.html import Link
from weboob.browser.filters.standard import CleanText, Regexp, Env
from weboob.exceptions import BrowserUnavailable, NoAccountsException
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.ordereddict import OrderedDict

from .base import MyHTMLPage


class AccountList(LoggedPage, MyHTMLPage):
    def on_load(self):
        MyHTMLPage.on_load(self)
        if self.doc.xpath(u'//h2[text()="%s"]' % u'ERREUR'):
            self.browser.location('https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/securite/authentification/initialiser-identif.ea')
            raise BrowserUnavailable()
        self.accounts = OrderedDict()
        self.parse_table('comptes',         Account.TYPE_CHECKING)
        self.parse_table('comptesEpargne',  Account.TYPE_SAVINGS)
        self.parse_table('comptesTitres',   Account.TYPE_MARKET)
        self.parse_table('comptesVie',      Account.TYPE_LIFE_INSURANCE)
        self.parse_table('encoursprets',    Account.TYPE_LOAN)
        # FIXME for loans, the balance may be the loan total, not the loan due??
        self.parse_table('comptesRetraireEuros')
        self.parse_table('comptesRetrairePoints')
        self.parse_table('comptesAssurancePrevoyance')

    def get_accounts_list(self):
        if not self.accounts:
            raise NoAccountsException()
        return self.accounts.itervalues()

    def parse_table(self, what, actype=Account.TYPE_UNKNOWN):
        tables = self.doc.xpath("//table[@id='%s']" % what, smart_strings=False)
        if len(tables) < 1:
            return

        lines = tables[0].xpath(".//tbody/tr")
        for line in lines:
            account = Account()
            account.label = CleanText('./td[1]')(line)
            account.type = actype
            account._link_id = Link('./td[1]//a', default=NotAvailable)(line)
            if not account._link_id:
                continue

            if 'BourseEnLigne' in account._link_id:
                account.type = Account.TYPE_MARKET

            account.id = CleanText('./td[2]')(line)
            tmp_balance = CleanText('./td[3]')(line)

            account.currency = account.get_currency(tmp_balance)
            if not account.currency:
                account.currency = u'EUR'

            if tmp_balance:
                if any(w in tmp_balance for w in ['non disponible', u'Remboursé intégralement']):
                    continue

                account.balance = Decimal(FrenchTransaction.clean_amount(tmp_balance))
            else:
                # empty balance info should only be for fully-reimbursed loans
                assert actype == Account.TYPE_LOAN
                account.balance = Decimal(0)

            if actype == Account.TYPE_LOAN:
                account.balance = -account.balance

            if account.id in self.accounts:
                a = self.accounts[account.id]
                a._card_links.append(account._link_id)
                if not a.coming:
                    a.coming = Decimal('0.0')
                a.coming += account.balance
            else:
                account._card_links = []
                self.accounts[account.id] = account

                response = self.browser.open('/voscomptes/canalXHTML/comptesCommun/imprimerRIB/init-imprimer_rib.ea?compte.numero=%s' % account.id)
                account.iban = response.page.get_iban()


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
    iban_regexp = r'BankIdentiferCode(\w+)PSS'

    def __init__(self, *args, **kwargs):
        super(AccountRIB, self).__init__(*args, **kwargs)

        self.parsed_text = ''

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
            parser = PDFParser(StringIO(self.doc))
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
            out = StringIO()
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
        m = re.search(self.iban_regexp, self.parsed_text)
        if m:
            return unicode(m.group(1))
        return None
