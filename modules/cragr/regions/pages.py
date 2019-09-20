# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from __future__ import unicode_literals


from decimal import Decimal
import re

from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, BrowserPasswordExpired
from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage, FormNotFound, pagination
from weboob.browser.elements import ListElement, TableElement, DictElement, ItemElement, method

from weboob.capabilities import NotAvailable
from weboob.capabilities.profile import Person
from weboob.capabilities.bank import Account, Loan, Investment
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.tools.date import LinearDateGuesser, parse_french_date

from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Format, Regexp, Map, Field, Currency,
    Date, DateGuesser, Eval, Env, Lower, Coalesce,
)
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import (
    TableCell, Link, Attr,
)


def float_to_decimal(f):
    return Decimal(str(f))


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile('^Retrait Au Distributeur.*'), FrenchTransaction.TYPE_WITHDRAWAL),
        (re.compile('^Virement.*((?P<dd>\d{2})/(?P<mm>\d{2})/(?P<y>\d+))?$'), FrenchTransaction.TYPE_TRANSFER),
        (re.compile('^Cheque.*'), FrenchTransaction.TYPE_CHECK),
        (re.compile('^Remise De Cheque.*'), FrenchTransaction.TYPE_DEPOSIT),
        (re.compile('^Frais.*'), FrenchTransaction.TYPE_BANK),
        (re.compile('^Interets Crediteurs.*'), FrenchTransaction.TYPE_BANK),
        (re.compile('^Cotisation.*'), FrenchTransaction.TYPE_BANK),
        (re.compile('^Prelevt.*'), FrenchTransaction.TYPE_ORDER),
        (re.compile('^Prelevmnt.*'), FrenchTransaction.TYPE_ORDER),
        (re.compile('^Prelevement.*'), FrenchTransaction.TYPE_ORDER),
        (re.compile('^Prelevement Carte.*(?P<dd>\d{2})/(?P<mm>\d{2})$', re.IGNORECASE), FrenchTransaction.TYPE_CARD_SUMMARY),
        (re.compile('^Remise Carte.*'), FrenchTransaction.TYPE_CARD),
        (re.compile('^Paiement Par Carte.*(?P<dd>\d{2})/(?P<mm>\d{2})$'), FrenchTransaction.TYPE_CARD),
        (re.compile('^Remboursement De Pret.*'), FrenchTransaction.TYPE_LOAN_PAYMENT),
    ]

class CragrPage(HTMLPage):
    ENCODING = 'iso8859-15'
    '''
    The on_load() automatically updates the session_value for all Cragr pages
    to avoid being logged out by doing requests with an expired session_value.
    This is essential for example when coming back from the Netfinca space.
    '''
    def on_load(self):
        new_session_value = Regexp(
            CleanText('//script[@language="JavaScript"][contains(text(), "idSessionSag")]'),
            r'idSessionSag = "([^"]+)', default=None)(self.doc)
        if new_session_value:
            self.browser.session_value = new_session_value

    def get_perimeter_name(self):
        return Lower(CleanText('//div[@id="libPerimetre_2"]//span[@class="textePerimetre_2"]', default=''))(self.doc)

    def get_rib_url(self):
        rib_nodes = self.doc.xpath('//a[text()="Edition de RIB"]/@href')
        if rib_nodes:
            m = re.search(r"javascript:ouvrePOPUP\('(.*)',", rib_nodes[0])
            if m:
                return m.group(1)
        return None

    def get_account_balance(self):
        return CleanDecimal.French('//tr[td[contains(text(), "Solde")]]//td[2]', default=NotAvailable)(self.doc)


class HomePage(CragrPage):
    '''
    This page depends on the selected region. It is the first
    visited page, from which we fetch the login URL from the
    JavaScript in order to access LoginPage.
    '''
    def get_login_url(self):
        login_script = CleanText('//script[contains(text(), "acces_aux_comptes")]')(self.doc)
        url_search = re.search(r'([^"]+)" \|\|', login_script)
        if url_search:
            return url_search.group(1)
        return None


class LoginPage(CragrPage):
    def submit_password(self, username, password):
        # If there is no login_form on the page, it means the submitted login is incorrect
        try:
            login_form = self.get_form(name='formulaire')
        except FormNotFound:
            raise BrowserIncorrectPassword()

        # The 'CCCRYC2' value should always be '000000' or shorter
        login_form['CCCRYC2'] = '0' * len(password)
        login_form['CCCRYC'] = self.get_positions(password)
        login_form.submit()

    def get_positions(self, password):
        positions = {}
        for position in self.doc.xpath('//table[@id="pave-saisie-code"]//td'):
            value = CleanText('.')(position)
            if value:
                tab_index = CleanDecimal('./a/@tabindex')(position) - 1
                # Add '0' in front of single digits ('7' becomes '07', but '17' remains '17')
                tab_index = str(tab_index).zfill(2)
                positions[value] = tab_index

        password_positions = [positions[digit] for digit in password]

        # Submitted string has the format '17,01,15,06,10,03'
        return ','.join(password_positions)

    def get_accounts_url(self):
        return CleanText('//body')(self.doc)


class LoggedOutPage(CragrPage):
    def is_here(self):
        return CleanText('//form[@class="ca-forms"]//h1[text()="Fin de connexion"]')(self.doc)


class PasswordExpiredPage(CragrPage):
    def on_load(self):
        error_msg = CleanText('//fieldset//font[1]/text()', default='')(self.doc)
        if 'Le code personnel que vous allez choisir' in error_msg:
            raise BrowserPasswordExpired()
        assert False, 'Unhandled error on PasswordExpiredPage: %s' % error_msg


class PerimeterDetailsPage(LoggedPage, CragrPage):
    def has_two_perimeters(self):
        # This message appears when there are only two perimeters.
        return CleanText('//div[@id="e-doc" and contains(text(), "Périmètre en cours de chargement")]')(self.doc)

    def get_multiple_perimeters(self):
        perimeters = []
        for perimeter in self.doc.xpath('//tr[@class="ca-forms"]//label[@class="gauche"]'):
            perimeters.append(CleanText(perimeter)(self))
        return perimeters

    def get_perimeter_url(self, perimeter):
        # We need to search for the perimeter name in the list of perimeters,
        # However we must put the strings to lowercase and remove multiple spaces.
        return Link('//p[label[contains(normalize-space(lower-case(text())), "%s")]]//a' % perimeter.lower(), default=None)(self.doc)


class PerimeterPage(LoggedPage, CragrPage):
    def on_load(self):
        if self.doc.xpath('//div[@class="validation"]'):
            # There is no complete message to fetch on the website but this node appears
            # when we land on a perimeter that has never been visited before.
            raise ActionNeeded("Certains de vos périmètres n'ont encore jamais été visités.\
                                Merci de parcourir tous les périmètres disponibles sur le site \
                                Crédit Agricole et de réaliser les réglages requis pour chaque périmètre.")

    def broken_perimeter(self):
        error_msg = CleanText('//h1[@class="h1-erreur"]')(self.doc)
        if error_msg:
            return 'Connexion Indisponible' in error_msg


class RibPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//b[contains(text(), "IDENTITÉ BANCAIRE")]')(self.doc)

    def get_iban(self):
        return CleanText('//div[@id="trPagePu"]//table[2]//td[font[b[contains(text(), "IBAN")]]]//tr//b/text()',
                         replace=[(' ', '')],
                         default=NotAvailable)(self.doc)


ACCOUNT_TYPES = {
    'CCHQ': Account.TYPE_CHECKING,
    'CCOU': Account.TYPE_CHECKING,
    'AUTO ENTRP': Account.TYPE_CHECKING,
    'AUTO ENTRS': Account.TYPE_CHECKING,
    'DEVISE USD': Account.TYPE_CHECKING,
    'EKO': Account.TYPE_CHECKING,
    'DEVISE CHF': Account.TYPE_CHECKING,
    'DAV NANTI': Account.TYPE_SAVINGS,
    'LIV A': Account.TYPE_SAVINGS,
    'LIV A ASS': Account.TYPE_SAVINGS,
    'LIVCR': Account.TYPE_SAVINGS,
    'LDD': Account.TYPE_SAVINGS,
    'PEL': Account.TYPE_SAVINGS,
    'CEL': Account.TYPE_SAVINGS,
    'CODEBIS': Account.TYPE_SAVINGS,
    'LJMO': Account.TYPE_SAVINGS,
    'CSL': Account.TYPE_SAVINGS,
    'LEP': Account.TYPE_SAVINGS,
    'LEF': Account.TYPE_SAVINGS,
    'TIWI': Account.TYPE_SAVINGS,
    'CSL LSO': Account.TYPE_SAVINGS,
    'CSL CSP': Account.TYPE_SAVINGS,
    'ESPE INTEG': Account.TYPE_SAVINGS,
    'DAV TIGERE': Account.TYPE_SAVINGS,
    'CPTEXCPRO': Account.TYPE_SAVINGS,
    'CPTEXCENT': Account.TYPE_SAVINGS,
    'DAT': Account.TYPE_DEPOSIT,
    'DATG': Account.TYPE_DEPOSIT,
    'LIS': Account.TYPE_SAVINGS,
    'PRET PERSO': Account.TYPE_LOAN,
    'P. ENTREPR': Account.TYPE_LOAN,
    'P. HABITAT': Account.TYPE_LOAN,
    'P. CONV.': Account.TYPE_LOAN,
    'PRET 0%': Account.TYPE_LOAN,
    'INV PRO': Account.TYPE_LOAN,
    'TRES. PRO': Account.TYPE_LOAN,
    'CT ATT HAB': Account.TYPE_LOAN,
    'PRET CEL': Account.TYPE_LOAN,
    'PRET PEL': Account.TYPE_LOAN,
    'PEA': Account.TYPE_PEA,
    'PEAP': Account.TYPE_PEA,
    'DAV PEA': Account.TYPE_PEA,
    'CPS': Account.TYPE_MARKET,
    'TITR': Account.TYPE_MARKET,
    'TITR CTD': Account.TYPE_MARKET,
    'PVERT VITA': Account.TYPE_PERP,
    'réserves de crédit': Account.TYPE_CHECKING,
    'prêts personnels': Account.TYPE_LOAN,
    'crédits immobiliers': Account.TYPE_LOAN,
    'ESC COM.': Account.TYPE_LOAN,
    'LIM TRESO': Account.TYPE_LOAN,
    'P.ETUDIANT': Account.TYPE_LOAN,
    'épargne disponible': Account.TYPE_SAVINGS,
    'épargne à terme': Account.TYPE_DEPOSIT,
    'épargne boursière': Account.TYPE_MARKET,
    'assurance vie et capitalisation': Account.TYPE_LIFE_INSURANCE,
    'PRED': Account.TYPE_LIFE_INSURANCE,
    'PREDI9 S2': Account.TYPE_LIFE_INSURANCE,
    'V.AVENIR': Account.TYPE_LIFE_INSURANCE,
    'FLORIA': Account.TYPE_LIFE_INSURANCE,
    'FLORIANE 2': Account.TYPE_LIFE_INSURANCE,
    'CAP DECOUV': Account.TYPE_LIFE_INSURANCE,
    'ESPACE LIB': Account.TYPE_LIFE_INSURANCE,
    'ESP LIB 2': Account.TYPE_LIFE_INSURANCE,
    'AST SELEC': Account.TYPE_LIFE_INSURANCE,
    'PRGE': Account.TYPE_LIFE_INSURANCE,
    'CONF': Account.TYPE_LIFE_INSURANCE,
    'ESPGESTCAP': Account.TYPE_CAPITALISATION,
    'ATOUT LIB': Account.TYPE_REVOLVING_CREDIT,
    'SUPPLETIS': Account.TYPE_REVOLVING_CREDIT,
    'PAGR': Account.TYPE_MADELIN,
    'ACCOR MULT': Account.TYPE_MADELIN,
}


class AccountsPage(LoggedPage, CragrPage):
    def no_other_perimeter(self):
        return not CleanText('//a[@title="Espace Autres Comptes"]')(self.doc)

    def set_cragr_code(self):
        # This security code enables access to Netfinca account details
        raw_text = self.doc.xpath('//script[contains(text(), "var codeCaisse =")]')[0].text
        m = re.search(r'var +codeCaisse *= *"(\d+)"', raw_text)
        if m:
            self.browser.cragr_code = m.group(1)

    @pagination
    @method
    class iter_accounts(TableElement):
        head_xpath = '//table[@class="ca-table"]//tr[@class="tr-thead"]/th'
        item_xpath = '''//table[@class="ca-table"]//tr[contains(@class, "autre-devise")
                                                    or contains(@class, "colcelligne")
                                                    or contains(@class, "ligne-connexe")]'''
        next_page = Link('//a[@class="btnsuiteliste"]', default=None)

        col_id = 'N° de compte'
        col_label = 'Type de compte'
        col_value_balance = 'En valeur'
        col_operation_balance = 'En opération'
        col_currency = 'Devise'

        class item(ItemElement):
            klass = Account

            def condition(self):
                # Skip card coming lines
                return 'Encours carte' not in CleanText(TableCell('label', colspan=True))(self)

            obj_id = CleanText(TableCell('id', colspan=True))
            obj_number = Field('id')
            obj_label = CleanText(TableCell('label', colspan=True))
            obj_type = Map(Field('label'), ACCOUNT_TYPES, Account.TYPE_UNKNOWN)
            obj_currency = Currency(TableCell('currency', colspan=True))
            obj_url = None

            # Accounts may have an 'Operations' balance or a 'Value' balance
            def obj_balance(self):
                value_balance = CleanText(TableCell('value_balance', default='', colspan=True))(self)
                # Skip invalid balance values in the 'Value' column (for example for Revolving credits)
                if value_balance not in ('', 'Montant disponible'):
                    return CleanDecimal.French().filter(value_balance)
                return CleanDecimal.French(CleanText(TableCell('operation_balance', default='', colspan=True)))(self)

            def obj__form(self):
                # Account forms look like 'javascript:fwkPUAvancerForm('Releves','frm1')'
                # From this we extract the name (frm1) and fetch the form name on the page.
                script = Link('.//a', default='')(TableCell('id', colspan=True)(self)[0])
                if 'javascript' in script:
                    form_search = re.search(r'frm\d+', script)
                    if form_search:
                        account_form = self.page.get_form(name=form_search.group(0))
                        return self.page.fill_form(account_form, card=False)
                return None

    def fill_form(self, form, card):
        form['fwkaction'] = 'Cartes' if card else 'Releves'
        form['fwkcodeaction'] = 'Executer'
        return form

    def get_cards_parameters(self):
        '''
        The only way to get all deferred cards is to check for
        the presence of 'coming' lines within the accounts table.
        However, there might several 'coming' lines for the same card,
        for example if there are summaries for next month and the month after.
        The 'cards_parameters' set contains pairs of (card_link, card_parent) values.
        '''
        cards_parameters = set()
        for coming in self.doc.xpath('//table[@class="ca-table"]//tr[contains(@class, "ligne-connexe")]'):
            if coming.xpath('./preceding-sibling::tr/@class')[-1] == 'ligne-connexe':
                # The preceding line was already a 'coming' so we skip this one.
                continue
            raw_link = Link(coming.xpath('.//a'), default=None)(self)
            if not raw_link:
                # Ignore coming lines without a link
                continue

            assert 'javascript' in raw_link, 'No form associated'
            # We extract the form name (e.g. 'frmc6') from a pattern
            # such as "javascript:fwkPUAvancerForm('Cartes','frmc6')"
            form_search = re.search(r"\('Cartes','(.*)'\)", raw_link)
            if form_search:
                card_link = form_search.group(1)
            else:
                # This link does not correspond to a card
                continue

            # The id of the card parent account is the closest
            # upper node containing an account id:
            coming_info = coming.xpath('./preceding-sibling::tr')
            assert coming_info, "Couldn't find card info"
            parent_id = None
            for regex in (r'> (\d+) ', r'\s(\d+)\s'):
                m = re.search(regex, CleanText('.')(coming_info[-1]))
                if m:
                    parent_id = m.group(1)
                    break
            assert parent_id is not None, "Couldn't find the id of current card's parent account"
            cards_parameters.add((card_link, parent_id))
        return cards_parameters

    def go_to_card(self, card_link):
        try:
            card_form = self.get_form(name=card_link)
            self.fill_form(card_form, card=True).submit()
        except FormNotFound:
            assert False, 'This card has no form, please check if there is an available link.'


class CardsPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//div[@class="boutons-act"]//h1[contains(text(), "Cartes - détail")]')(self.doc)

    def has_unique_card(self):
        return not CleanText('//table[@summary]//caption[@class="ca-table caption"or @class="caption tdb-cartes-caption"]')(self.doc)

    @method
    class get_unique_card(ItemElement):
        item_xpath = '//table[@class="ca-table"][@summary]'

        klass = Account

        # Transform 'n° 4999 78xx xxxx xx72' into '499978xxxxxxxx72'
        obj_number = CleanText('//table[@class="ca-table"][@summary]//tr[@class="ligne-impaire"]/td[@class="cel-texte"][1]',
                               replace=[(' ', ''), ('n°', '')])

        # Card ID is formatted as '499978xxxxxxxx72MrFirstnameLastname-'
        obj_id = Format('%s%s',
                        Field('number'),
                        CleanText('//table[@class="ca-table"][@summary]//caption[@class="caption"]//b',
                        replace=[(' ', '')]))

        # Card label is formatted as 'Carte VISA Premier - Mr M Lastname'
        obj_label = Format('%s - %s',
                           CleanText('//table[@class="ca-table"][@summary]//tr[@class="ligne-impaire ligne-bleu"]/th[@id="compte-1"]'),
                           CleanText('//table[@class="ca-table"][@summary]//caption[@class="caption"]//b'))

        obj_balance = CleanDecimal(0)
        obj_coming = CleanDecimal.French('//table[@class="ca-table"][@summary]//tr[@class="ligne-paire"]//td[@class="cel-num"]', default=0)
        obj_currency = Currency(Regexp(CleanText('//th[contains(text(), "Montant en")]'), r'^Montant en (.*)'))
        obj_type = Account.TYPE_CARD
        obj__form = None

    def get_next_page(self):
        return Link('//a[@class="liennavigationcorpspage" and text()="[>]"]', default=None)(self.doc)

    def get_ongoing_coming(self):
        # The title of the coming is usually 'Opérations débitées' but if
        # the coming is positive, it will become 'Opérations créditées'
        raw_date = Regexp(
            CleanText('//table[@class="ca-table"]//tr[1]//b[contains(text(), "Opérations débitées") or contains(text(), "Opérations créditées")]'),
            r'le (.*) :', default=None
        )(self.doc)
        if not raw_date:
            return None
        return parse_french_date(raw_date).date()

    def get_card_transactions(self, latest_date, ongoing_coming):
        for item in self.doc.xpath('//table[@class="ca-table"][2]//tr[td]'):
            if CleanText('./td[2]/b')(item):
                # This node is a summary containing the 'date' for all following transactions.
                raw_date = Regexp(CleanText('./td[2]/b/text()'), r'le (.*) :')(item)
                if latest_date and parse_french_date(raw_date).date() > latest_date:
                    # This summary has already been fetched
                    continue
                latest_date = parse_french_date(raw_date).date()
                if latest_date < ongoing_coming:
                    # This summary is anterior to the ongoing_coming so we create a transaction from it
                    tr = FrenchTransaction()
                    tr.date = tr.rdate = latest_date
                    tr.raw = tr.label = CleanText('./td[2]/b/text()')(item)
                    tr.amount = -CleanDecimal.French('./td[position()=last()]')(item)
                    tr.type = FrenchTransaction.TYPE_CARD_SUMMARY
                    yield tr
            else:
                # This node is a real transaction.
                # Its 'date' is the date of the most recently encountered summary node.
                tr = FrenchTransaction()
                tr.date = latest_date
                date_guesser = LinearDateGuesser(latest_date)
                tr.rdate = tr.bdate = DateGuesser(CleanText('./td[1]//text()'), date_guesser=date_guesser)(item)
                tr.label = tr.raw = CleanText('./td[2]')(item)
                tr.amount = CleanDecimal.French('./td[last()]')(item)
                tr.type = FrenchTransaction.TYPE_DEFERRED_CARD
                yield tr


class MultipleCardsPage(CardsPage):
    def is_here(self):
        return CleanText('//div[@class="boutons-act"]//h1[contains(text(), "Cartes")]')(self.doc)

    @method
    class iter_multiple_cards(ListElement):
        item_xpath = '//table[@summary][caption[@class="ca-table caption"or @class="caption tdb-cartes-caption"]]'

        class item(ItemElement):
            klass = Account

            def condition(self):
                # Ignore cards that do not have a coming
                return CleanText('.//tr[1]/td[@class="cel-num"]')(self)

            # Transform 'n° 4999 78xx xxxx xx72' into '499978xxxxxxxx72'
            obj_number = CleanText('.//caption/span[@class="tdb-cartes-num"]', replace=[(' ', ''), ('n°', '')])
            # The raw number is used to access multiple cards details
            obj__raw_number = CleanText('.//caption/span[@class="tdb-cartes-num"]')

            # Multiple card IDs are formatted as '499978xxxxxxxx72MrFirstnameLastname'
            obj_id = Format('%s%s',
                            Field('number'),
                            CleanText('.//caption/span[@class="tdb-cartes-prop"]', replace=[(' ', '')]))

            # Card label is formatted as 'Carte VISA Premier - Mr M Lastname'
            obj_label = Format(
                '%s - %s',
                CleanText('.//caption/span[has-class("tdb-cartes-carte")]'),
                CleanText('.//caption/span[has-class("tdb-cartes-prop")]')
            )

            obj_type = Account.TYPE_CARD
            obj_balance = CleanDecimal(0)
            obj_coming = CleanDecimal.French('.//tr[1]/td[position() = last()]', default=0)
            obj_currency = Currency(Regexp(CleanText('//span[contains(text(), "Montants en")]'), r'^Montants en (.*)'))
            obj__form = None


    def get_transactions_link(self, raw_number):
        # We cannot use Link() because the @href attribute contains line breaks and spaces.
        if len(self.doc.xpath('//table[@class="ca-table"][caption[span[text()="%s"]]]//tr' % raw_number)) == 1:
            # There is only one coming line (no card information link)
            return CleanText('//table[@class="ca-table"][caption[span[text()="%s"]]]//tr[position()=last()]/th/a/@href'
                             % raw_number, replace=[(' ', '')])(self.doc)
        elif self.doc.xpath('//table[@class="ca-table"][caption[span[text()="%s"]]]//tr//a[contains(text(), "Infos carte")]' % raw_number):
            # There is a card information line, select the <tr> before the last
            return CleanText('//table[@class="ca-table"][caption[span[text()="%s"]]]//tr[position()=last()-1]/th/a/@href'
                             % raw_number, replace=[(' ', '')])(self.doc)
        else:
            # There is no information line, return the last <tr>
            return CleanText('//table[@class="ca-table"][caption[span[text()="%s"]]]//tr[position()=last()]/th/a/@href'
                             % raw_number, replace=[(' ', '')])(self.doc)


class WealthPage(LoggedPage, CragrPage):
    @pagination
    @method
    class iter_wealth_accounts(ListElement):
        # The <table> is divided in many sub-heads and sub-tables so
        # it is easier to point directly to accounts and use ListElement

        item_xpath = '//tr[contains(@class, "colcelligne")][td]'
        next_page = Link('//a[@class="btnsuiteliste"]', default=None)

        class item(ItemElement):
            klass = Account

            obj_id = CleanText('./td[2]')
            obj_number = Field('id')
            obj_label = CleanText('./td/span[@class="gras"]')
            obj_type = Map(Field('label'), ACCOUNT_TYPES, Account.TYPE_UNKNOWN)
            # Accounts without balance will be skipped later on
            obj_balance = CleanDecimal.French('./td//*[@class="montant3"]', default=NotAvailable)
            obj_currency = Currency('./td[@class="cel-devise"]')
            obj_iban = None
            obj__form = None

            def obj_url(self):
                url = Link('./td[2]/a', default=None)(self)
                if url and 'BGPI' in url:
                    # This URL is just the BGPI home page, not the account itself.
                    # The real account URL will be set by get_account_details() in BGPISpace.
                    return 'BGPI'
                return url


class LoansPage(LoggedPage, CragrPage):
    @pagination
    @method
    class iter_loans(ListElement):
        # The <table> is divided in many sub-heads and sub-tables so
        # it is easier to point directly to accounts and use ListElement
        item_xpath = '//tr[contains(@class, "colcelligne")][td]'
        next_page = Link('//a[@class="btnsuiteliste"]', default=None)

        class item(ItemElement):
            klass = Loan

            def condition(self):
                return 'Billet financier' not in CleanText('./td[1]')(self)

            obj_id = CleanText('./td[2]')
            obj_number = Field('id')
            obj_label = CleanText('./td[1]')
            obj_type = Map(Field('label'), ACCOUNT_TYPES, Account.TYPE_LOAN)
            obj_next_payment_amount = Env('next_payment_amount')
            obj_total_amount = Env('total_amount')
            obj_currency = Currency('./td[@class="cel-devise"]')
            obj_url = Link('./td[2]/a', default=None)
            obj_iban = None
            obj__form = None

            def obj_balance(self):
                balance = Env('balance')(self)
                return -abs(balance)

            def parse(self, obj):
                # We must handle Loan tables with 5 or 6 columns
                if CleanText('//tr[contains(@class, "colcelligne")][count(td) = 5]')(self):
                    # History table with 4 columns (no loan details)
                    self.env['next_payment_amount'] = NotAvailable
                    self.env['total_amount'] = NotAvailable
                    self.env['balance'] = CleanDecimal.French('./td[4]//*[@class="montant3" or @class="montant4"]', default=NotAvailable)(self)
                elif CleanText('//tr[contains(@class, "colcelligne")][count(td) = 6]')(self):
                    # History table with 5 columns (contains next_payment_amount & total_amount)
                    self.env['next_payment_amount'] = CleanDecimal.French('./td[3]//*[@class="montant3"]', default=NotAvailable)(self)
                    self.env['total_amount'] = CleanDecimal.French('./td[4]//*[@class="montant3"]', default=NotAvailable)(self)
                    self.env['balance'] = CleanDecimal.French('./td[5]//*[@class="montant3"]', default=NotAvailable)(self)


class CheckingHistoryPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]')(self.doc)

    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//tr[contains(@class, "ligne-")]'
        next_page = Link('//a[@class="liennavigationcorpspage"][img[@alt="Page suivante"]]', default=None)

        class item(ItemElement):
            klass = Transaction

            obj_date = Env('date')
            obj_vdate = Env('vdate')
            obj_raw = Transaction.Raw(Env('raw'))
            obj_amount = Env('amount')

            def parse(self, obj):
                self.env['date'] = DateGuesser(CleanText('./td[1]'), Env('date_guesser'))(self)
                self.env['vdate'] = NotAvailable
                if CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//tr[count(td) = 4]')(self):
                    # History table with 4 columns
                    self.env['raw'] = CleanText('./td[2]')(self)
                    self.env['amount'] = CleanDecimal.French('./td[last()]')(self)

                elif CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//tr[count(td) = 5]')(self):
                    # History table with 5 columns
                    self.env['raw'] = CleanText('./td[3]')(self)
                    self.env['amount'] = CleanDecimal.French('./td[last()]')(self)

                elif CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//tr[count(td) = 6]')(self):
                    # History table with 6 columns (contains vdate)
                    self.env['raw'] = CleanText('./td[4]')(self)
                    self.env['vdate'] = DateGuesser(CleanText('./td[2]'), Env('date_guesser'))(self)
                    self.env['amount'] = CleanDecimal.French('./td[last()]')(self)

                elif CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//tr[count(td) = 7]')(self):
                    # History table with 7 columns
                    self.env['amount'] = Coalesce(
                        CleanDecimal.French('./td[6]', sign=lambda x: -1, default=None),
                        CleanDecimal.French('./td[7]', default=None)
                    )(self)
                    if CleanText('//table[@class="ca-table"][caption[span[b[text()="Historique des opérations"]]]]//th[a[contains(text(), "Valeur")]]')(self):
                        # With vdate column ('Valeur')
                        self.env['raw'] = CleanText('./td[4]')(self)
                        self.env['vdate'] = DateGuesser(CleanText('./td[2]'), Env('date_guesser'))(self)
                    else:
                        # Without any vdate column
                        self.env['raw'] = CleanText('./td[3]')(self)
                else:
                    assert False, 'This type of history table is not handled yet!'


class SavingsHistoryPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//span[@class="tdb-cartes-prop"]/b[contains(text(), "HISTORIQUE DES VERSEMENTS")]')(self.doc)

    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '''//table[@class="ca-table"][caption[span[b[contains(text(), "HISTORIQUE DES VERSEMENTS")]]]]
                        //tr[contains(@class, "ligne-")]'''
        next_page = Link('//a[@class="liennavigationcorpspage"][img[@alt="Page suivante"]]', default=None)

        class item(ItemElement):
            klass = Transaction

            def obj_date(self):
                date = CleanText('./td[1]/font//text()')(self)
                if len(date) == 10:
                    return Date(CleanText('./td[1]/font//text()'), dayfirst=True)(self)
                elif len(date) == 5:
                    # Date has no indicated year.
                    return DateGuesser(CleanText('./td[1]//text()'), Env('date_guesser'))(self)

            obj_raw = Transaction.Raw(CleanText('./td[2]/font//text()'))
            obj_amount = CleanDecimal.French('./td[3]/font//text()')
            obj_rdate = Field('date')


class OtherSavingsHistoryPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//span[@class="tdb-cartes-prop"]/b[contains(text(), "HISTORIQUE DES OPERATIONS")]')(self.doc)

    @pagination
    @method
    class iter_history(ListElement):
        item_xpath = '''//table[@class="ca-table"][caption[span[b[contains(text(), "HISTORIQUE DES OPERATIONS")]]]]
                        //tr[contains(@class, "ligne-")]'''
        next_page = Link('//a[@class="liennavigationcorpspage"][img[@alt="Page suivante"]]', default=None)

        class item(ItemElement):
            klass = Transaction

            def obj_date(self):
                # Dates in the first column may appear as '12/01/2019' or '12/01'
                date = CleanText('./td[1]/font//text()')(self)
                if len(date) == 10:
                    return Date(CleanText('./td[1]/font//text()'), dayfirst=True)(self)
                elif len(date) == 5:
                    # Date has no indicated year.
                    return DateGuesser(CleanText('./td[1]//text()'), Env('date_guesser'))(self)

            obj_raw = Transaction.Raw(CleanText('./td[2]/font//text()'))
            obj_amount = CleanDecimal.French('./td[3]/font//text()')
            obj_rdate = Field('date')


class FailedHistoryPage(LoggedPage, CragrPage):
    def is_here(self):
        return CleanText('//form[@class="ca-forms"]//h1[contains(text(), "Service indisponible")]')(self.doc)


class PredicaRedirectionPage(LoggedPage, CragrPage):
    def on_load(self):
        form = self.get_form()
        form.submit()


class PredicaInvestmentsPage(LoggedPage, JsonPage):
    @method
    class iter_investments(DictElement):
        item_xpath = 'listeSupports/support'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(Dict('lcspt'))
            obj_valuation = Eval(float_to_decimal, Dict('mtvalspt'))

            def obj_portfolio_share(self):
                portfolio_share = Dict('txrpaspt', default=None)(self)
                if portfolio_share:
                    return Eval(lambda x: float_to_decimal(x / 100), portfolio_share)(self)
                return NotAvailable

            def obj_unitvalue(self):
                unit_value = Dict('mtliqpaaspt', default=None)(self)
                if unit_value:
                    return Eval(float_to_decimal, unit_value)(self)
                return NotAvailable

            def obj_quantity(self):
                quantity = Dict('qtpaaspt', default=None)(self)
                if quantity:
                    return Eval(float_to_decimal, quantity)(self)
                return NotAvailable

            def obj_code(self):
                code = Dict('cdsptisn')(self)
                if is_isin_valid(code):
                    return code
                return NotAvailable

            def obj_code_type(self):
                if Field('code')(self) == NotAvailable:
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN


class NetfincaRedirectionPage(LoggedPage, HTMLPage):
    def no_netfinca_access(self):
        return CleanText('//p[@class="gras" and contains(text(), "service CA-Titres est actuellement indisponible")]')(self.doc)

    def get_url(self):
        return Regexp(Attr('//body', 'onload', default=None), r'document.location="([^"]+)"')(self.doc)


class NetfincaLanding(LoggedPage, HTMLPage):
    pass


class NetfincaDetailsPage(LoggedPage, HTMLPage):
    def get_balance(self):
        # This method returns the PEA balance without the liquidities
        return CleanDecimal.French('//tr[td[contains(text(), "Valorisation titres")]]/td[2]/span')(self.doc)


class NetfincaReturnPage(LoggedPage, HTMLPage):
    def return_from_netfinca(self):
        return_form = self.get_form(name='formulaire')
        return_form.submit()


class NetfincaToCragr(LoggedPage, CragrPage):
    def on_load(self):
        new_session_value = Regexp(
            CleanText('//script[@language="JavaScript"][contains(text(), "idSessionSag")]'),
            r'idSessionSag = "([^"]+)', default=None)(self.doc)
        if new_session_value:
            self.browser.session_value = new_session_value
        # Automatically go back to the accounts page
        self.browser.accounts.go()


class BGPIRedirectionPage(LoggedPage, HTMLPage):
    def get_bgpi_url(self):
        # The HTML is broken so we cannot use a regular Attr('xpath')
        m = re.search(r'document.location="([^"]+)"', self.text)
        if m:
            return m.group(1)


class BGPISpace(LoggedPage, HTMLPage):
    def get_account_details(self, account_id):
        balance = CleanDecimal.French('//a[div[div[span[span[contains(text(), "%s")]]]]]/div[1]/div[2]/span/span'
                                      % account_id, default=NotAvailable)(self.doc)

        currency = Currency('//a[div[div[span[span[contains(text(), "%s")]]]]]/div[1]/div[2]/span/span'
                                      % account_id, default=NotAvailable)(self.doc)

        label = CleanText('//a[div[div[span[span[contains(text(), "%s")]]]]]/div[1]/div[1]/span/span'
                                      % account_id, default=NotAvailable)(self.doc)

        url = Link('//a[div[div[span[span[contains(text(), "%s")]]]]]' % account_id, default=None)(self.doc)
        if url:
            account_url = 'https://bgpi-gestionprivee.credit-agricole.fr' + url
        else:
            account_url = None

        return balance, currency, label, account_url


class BGPIInvestmentPage(LoggedPage, HTMLPage):
    @method
    class iter_investments(ListElement):
        item_xpath = '//div[div[ul[count(li) > 5]]]'

        class item(ItemElement):

            klass = Investment

            obj_label = CleanText('.//span[@class="uppercase"]')
            obj_valuation = CleanDecimal.French('.//span[@class="box"][span[span[text()="Montant estimé"]]]/span[2]/span')
            obj_quantity = CleanDecimal.French('.//span[@class="box"][span[span[text()="Nombre de part"]]]/span[2]/span')
            obj_unitvalue = CleanDecimal.French('.//span[@class="box"][span[span[text()="Valeur liquidative"]]]/span[2]/span')
            obj_unitprice = CleanDecimal.French('.//span[@class="box"][span[span[text()="Prix de revient"]]]/span[2]/span', default=NotAvailable)
            obj_portfolio_share = Eval(
                lambda x: x / 100,
                CleanDecimal.French('.//span[@class="box"][span[span[text()="Répartition"]]]/span[2]/span')
            )

            def obj_diff_ratio(self):
                # Euro funds have '-' instead of a diff_ratio value
                if CleanText('.//span[@class="box"][span[span[text()="+/- value latente (%)"]]]/span[2]/span')(self) == '-':
                    return NotAvailable
                return Eval(
                    lambda x: x / 100,
                    CleanDecimal.French('.//span[@class="box"][span[span[text()="+/- value latente (%)"]]]/span[2]/span')
                )(self)

            def obj_diff(self):
                if Field('diff_ratio')(self) == NotAvailable:
                    return NotAvailable
                return CleanDecimal.French('.//span[@class="box"][span[span[text()="+/- value latente"]]]/span[2]/span')(self)

            def obj_code(self):
                code = CleanText('.//span[@class="cl-secondary"]')(self)
                if is_isin_valid(code):
                    return code
                return NotAvailable

            def obj_code_type(self):
                if Field('code')(self) == NotAvailable:
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN


class ProfilePage(LoggedPage, CragrPage):
    @method
    class get_profile(ItemElement):
        klass = Person

        obj_email = Regexp(CleanText('//font/b/script', default=""), r'formatMail\(\'(.*)\'\)', default=NotAvailable)
        obj_job = CleanText('//td[contains(text(), "Type de profession")]/following::td[1]', default=NotAvailable)
        obj_name = Format('%s %s',
                          CleanText('//td[contains(text(), "Prénom")]/following::td[1]', default=NotAvailable),
                          CleanText('//td[contains(text(), "Nom")]/following::td[1]', default=NotAvailable))

        def obj_address(self):
            # The address is spread accross several <tr>/<td[3]>
            # So we must fetch them all and reconstitute it
            address_items = []
            for item in self.page.doc.xpath('//table[tr[td[contains(text(), "Adresse")]]]/tr[position()>3 and position()<8]/td[3]'):
                if CleanText(item)(self):
                    address_items.append(CleanText(item)(self))
            return ' '.join(address_items) or NotAvailable
