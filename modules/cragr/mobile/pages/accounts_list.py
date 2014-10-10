# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
from datetime import date
from weboob.capabilities.bank import Account
from .base import CragrBasePage
from .tokenextractor import TokenExtractor
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [
        (re.compile('^(Vp|Vt|Vrt|Virt|Vir(ement)?)\s*(?P<text>.*)', re.IGNORECASE),         FrenchTransaction.TYPE_TRANSFER),
        (re.compile('^(?P<text>(Tip|Plt|Prlv|PRELEVT|Prelevement)\s*.*)', re.IGNORECASE),   FrenchTransaction.TYPE_ORDER),
        (re.compile('^Cheque\s*(?P<text>(No)?.*)', re.IGNORECASE),                             FrenchTransaction.TYPE_CHECK),
        (re.compile('^(?P<text>Rem\s*Chq\s*.*)', re.IGNORECASE),                            FrenchTransaction.TYPE_DEPOSIT),
        (re.compile('^Ret(rait)?\s*Dab\s*((?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2}))?\s*(?P<text>.*)', re.IGNORECASE),
                                                                                            FrenchTransaction.TYPE_WITHDRAWAL),
        (re.compile('^Paiement\s*Carte\s*(?P<dd>\d{2})(?P<mm>\d{2})(?P<yy>\d{2})\s*(?P<text>.*)', re.IGNORECASE),
                                                                                            FrenchTransaction.TYPE_CARD),
        (re.compile('^(?P<text>.*CAPITAL.*ECHEANCE.*)', re.IGNORECASE),                     FrenchTransaction.TYPE_LOAN_PAYMENT),
        (re.compile('^(\*\*)?(?P<text>(frais|cotis(ation)?)\s*.*)', re.IGNORECASE),            FrenchTransaction.TYPE_BANK),
        (re.compile('^(?P<text>Interets\s*.*)', re.IGNORECASE),                             FrenchTransaction.TYPE_BANK),
        (re.compile('^(?P<text>Prelev\.\s*(C\.r\.d\.s\.|R\.s\.a\.|C\.a\.p\.s\.|C\.s\.g|P\.s\.))', re.IGNORECASE),
                                                                                            FrenchTransaction.TYPE_BANK),
        (re.compile('^(ACH.)?CARTE (?P<text>.*)', re.IGNORECASE),                           FrenchTransaction.TYPE_CARD),
        (re.compile('^RET.CARTE (?P<text>.*)', re.IGNORECASE),                              FrenchTransaction.TYPE_WITHDRAWAL),
    ]


class AccountsList(CragrBasePage):
    """
        Unlike most pages used with the Browser class, this class represents
        several pages, notably accounts list, history and transfer. This is due
        to the Credit Agricole not having a clear pattern to identify a page
        based on its URL.
    """

    def is_accounts_list(self):
        """
            Returns True if the current page appears to be the page dedicated to
            list the accounts.
        """
        # we check for the presence of a "mes comptes titres" link_id
        link = self.document.xpath('/html/body//a[contains(text(), "comptes titres")]')
        return bool(link)

    def is_account_page(self):
        """
            Returns True if the current page appears to be a page dedicated to list
            the history of a specific account.
        """
        # tested on CA Lorraine, Paris, Toulouse
        title_spans = self.document.xpath('/html/body//div[@class="dv"]/span')
        for title_span in title_spans:
            title_text = title_span.text_content().strip().replace("\n", '')
            if (re.match('.*Compte.*n.*[0-9]+', title_text, flags=re.IGNORECASE)):
                return True
        return False

    def is_transfer_page(self):
        """
            Returns True if the current page appears to be the page dedicated to
            order transfers between accounts.
        """
        source_account_select_field = self.document.xpath('/html/body//form//select[@name="numCompteEmetteur"]')
        target_account_select_field  = self.document.xpath('/html/body//form//select[@name="numCompteBeneficiaire"]')
        return bool(source_account_select_field) and bool(target_account_select_field)

    def get_list(self):
        """
            Returns the list of available bank accounts
        """
        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') in ('dv', 'headline') and div.getchildren()[0].tag in ('a', 'br'):
                self.logger.debug("Analyzing div %s" % div)
                # Step 1: extract text tokens
                tokens = []
                required_tokens = {}
                optional_tokens = {}
                token_extractor = TokenExtractor()
                for token in token_extractor.extract_tokens(div):
                    self.logger.debug('Extracted text token: "%s"' % token)
                    tokens.append(token)
                # Step 2: analyse tokens
                for token in tokens:
                    if self.look_like_account_number(token):
                        required_tokens['account_number'] = token
                    elif self.look_like_amount(token):
                        required_tokens['account_amount'] = token
                    elif self.look_like_account_name(token):
                        required_tokens['account_name'] = token
                    elif self.look_like_account_owner(token):
                        if 'account_owner' in optional_tokens and 'account_name' not in required_tokens:
                            required_tokens['account_name'] = optional_tokens['account_owner']
                        optional_tokens['account_owner'] = token
                # Step 3: create account objects
                if len(required_tokens) >= 3:
                    account = Account()
                    account.label = required_tokens['account_name']
                    account.id = required_tokens['account_number']
                    account.balance = FrenchTransaction.clean_amount(required_tokens['account_amount'])
                    account.currency = account.get_currency(required_tokens['account_amount'])
                    # we found almost all required information to create an account object
                    self.logger.debug('Found account %s with number %s and balance = %.2f' % (account.label, account.id, account.balance))
                    # we may have found the owner name too
                    if optional_tokens.get('account_owner') is not None:
                        # well, we could add it to the label, but is this really required?
                        self.logger.debug('  the owner appears to be %s' % optional_tokens['account_owner'])
                    # we simply lack the link to the account history... which remains optional
                    first_link = div.find('a')
                    if first_link is not None:
                        account._link_id = first_link.get('href')
                        self.logger.debug('  the history link appears to be %s' % account._link_id)
                    else:
                        account._link_id = None

                    yield account

    def get_history(self, date_guesser, start_index=0, start_offset=0):
        """
            Returns the history of a specific account. Note that this function
            expects the current page to be the one dedicated to this history.
            start_index is the id used for the first created operation.
            start_offset allows ignoring the `n' first Transactions on the page.
        """
        # tested on CA Lorraine, Paris, Toulouse
        # avoir parsing the page as an account-dedicated page if it is not the case
        if not self.is_account_page():
            return

        # Step 1: extract text tokens
        tokens = []
        token_extractor = TokenExtractor()
        for div in self.document.getiterator('div'):
            if div.attrib.get('class', '') in ('dv'):
                self.logger.debug("Analyzing div %s" % div)
                for token in token_extractor.extract_tokens(div):
                    self.logger.debug('Extracted text token: "%s"' % token)
                    tokens.append(token)

        # Step 2: convert tokens into operations
        # Notes:
        # * the code below expects pieces of information to be in the date-label-amount order;
        #   could we achieve a heuristic smart enough to guess this order?
        # * unlike the former code, we parse every operation
        operations = []
        current_operation = {}
        for token in tokens:
            self.logger.debug('Analyzing token: "%s"' % token)
            date_analysis = self.look_like_date_only(token)
            if date_analysis:
                current_operation = {}
                current_operation['date'] = date_analysis.groups()[0]
            else:
                date_desc_analysis = self.look_like_date_and_description(token)
                if date_desc_analysis:
                    current_operation = {}
                    current_operation['date'] = date_desc_analysis.groups()[0]
                    current_operation['label'] = date_desc_analysis.groups()[1]
                elif self.look_like_amount(token):
                    # we consider the amount is the last information we get for an operation
                    current_operation['amount'] = FrenchTransaction.clean_amount(token)
                    if current_operation.get('label') is not None and current_operation.get('date') is not None:
                        self.logger.debug('Parsed operation: %s: %s: %s' % (current_operation['date'], current_operation['label'], current_operation['amount']))
                        operations.append(current_operation)
                        current_operation = {}
                else:
                    if current_operation.get('label') is not None:
                        current_operation['label'] = u'%s %s' % (current_operation['label'], token)
                    else:
                        current_operation['label'] = token

        # Step 3: yield adequate transactions
        index = start_index
        for op in operations[start_offset:]:
            self.logger.debug('will yield the following transaction with index %d: %s: %s: %s' % (index, op['date'], op['label'], op['amount']))
            transaction = Transaction(index)
            index += 1
            transaction.amount = op['amount']
            transaction.parse(self.date_from_string(op['date'], date_guesser), re.sub('\s+', ' ', op['label']))
            yield transaction

    def get_transfer_accounts(self, select_name):
        """
            Returns the accounts proposed for a transfer in a select field.
            This method assumes the current page is the one dedicated to transfers.
            select_name is the name of the select field to analyze
        """
        if not self.is_transfer_page():
            return False
        source_accounts = {}
        source_account_options = self.document.xpath('/html/body//form//select[@name="%s"]/option' % select_name)
        for option in source_account_options:
            source_account_value = option.get('value', -1)
            if (source_account_value != -1):
                matches = re.findall('^[A-Z0-9]+.*([0-9]{11}).*$', self.extract_text(option))
                if matches:
                    source_accounts[source_account_value] = matches[0]
        return source_accounts

    def get_transfer_source_accounts(self):
        return self.get_transfer_accounts('numCompteEmetteur')

    def get_transfer_target_accounts(self):
        return self.get_transfer_accounts('numCompteBeneficiaire')

    def expand_history_page_url(self):
        """
            When on a page dedicated to list the history of a specific account (see
            is_account_page), returns the link to expand the history with 25 more results,
            or False if the link is not present.
        """
        # tested on CA centre france
        a = self.document.xpath('/html/body//div[@class="headline"]//a[contains(text(), "Voir les 25 suivants")]')
        if not a:
            return False
        else:
            return a[0].get('href', '')

    def next_page_url(self):
        """
            When on a page dedicated to list the history of a specific account (see
            is_account_page), returns the link to the next page, or False if the
            link is not present.
        """
        # tested on CA Lorraine, Paris, Toulouse
        a = self.document.xpath('/html/body//div[@class="navlink"]//a[contains(text(), "Suite")]')
        if not a:
            return False
        else:
            return a[0].get('href', '')

    def operations_page_url(self):
        """
            Returns the link to the "Opérations" page. This function assumes the
            current page is the accounts list (see is_accounts_list)
        """
        link = self.document.xpath(u'/html/body//a[contains(text(), "Opérations")]')
        return link[0].get('href')

    def transfer_page_url(self):
        """
            Returns the link to the "Virements" page. This function assumes the
            current page is the operations list (see operations_page_url)
        """
        link = self.document.xpath('/html/body//a[@accesskey=1]/@href')
        return link[0]

    def extract_text(self, xml_elmt):
        """
            Given an XML element, returns its inner text in a reasonably readable way
        """
        data = u''
        for text in xml_elmt.itertext():
            data = data + u'%s ' % text
        data = re.sub(' +', ' ', data.replace("\n", ' ').strip())
        return data

    def fallback_date(self):
        """ Returns a fallback, default date. """
        return date(date.today().year, 1, 1)

    def date_from_string(self, string, date_guesser):
        """
            Builds a date object from a 'DD/MM' string
        """
        matches = re.search('\s*([012]?[0-9]|3[01])\s*/\s*(0?[1-9]|1[012])\s*$', string)
        if matches is None:
            return self.fallback_date()
        return date_guesser.guess_date(int(matches.group(1)), int(matches.group(2)))

    def look_like_account_owner(self, string):
        """ Returns a date object built from a given day/month pair. """
        result = re.match('^\s*(M\.|Mr|Mme|Mlle|Mle|Monsieur|Madame|Mademoiselle)', string, re.IGNORECASE)
        self.logger.debug('Does "%s" look like an account owner? %s', string, ('yes' if result else 'no'))
        return result

    def look_like_account_name(self, string):
        """ Returns True of False depending whether string looks like an account name. """
        result = (len(string) >= 3 and not self.look_like_account_owner(string))
        self.logger.debug('Does "%s" look like an account name? %s', string, ('yes' if result else 'no'))
        return result

    def look_like_account_number(self, string):
        """ Returns either False or a SRE_Match object depending whether string looks like an account number. """
        # An account is a 11 digits number (no more, no less)
        result = re.match('[^\d]*\d{11}[^\d]*', string)
        self.logger.debug('Does "%s" look like an account number? %s', string, ('yes' if result else 'no'))
        return result

    def look_like_amount(self, string):
        """ Returns either False or a SRE_Match object depending whether string looks like an amount. """
        # It seems the Credit Agricole always mentions amounts using two decimals
        result = re.match('-?[\d ]+[\.,]\d{2}', string)
        self.logger.debug('Does "%s" look like an amount? %s', string, ('yes' if result else 'no'))
        return result

    def look_like_date_only(self, string):
        """ Returns either False or a SRE_Match object depending whether string looks like an isolated date. """
        result = re.search('^\s*((?:[012][0-9]|3[01])/(?:0[1-9]|1[012]))\s*$', string)
        self.logger.debug('Does "%s" look like a date (and only a date)? %s', string, ('yes' if result else 'no'))
        return result

    def look_like_date_and_description(self, string):
        """ Returns either False or a SRE_Match object depending on whether string looks like a date+description pair. """
        result = re.search('^\s*((?:[012][0-9]|3[01])/(?:0[1-9]|1[012]))\s+(.+)\s*$', string)
        self.logger.debug('Does "%s" look like a date+description pair? %s', string, ('yes' if result else 'no'))
        return result
