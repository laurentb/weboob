# -*- coding: utf-8 -*-

# Copyright(C) 2009-2013  Romain Bignon, Xavier Guerrin
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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser
from weboob.capabilities.bank import Transfer, TransferError
from .pages import LoginPage, AccountsList
import mechanize
from datetime import datetime
import re


__all__ = ['CragrMobile']


class CragrMobile(Browser):
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    # a session id that is sometimes added, and should be ignored when matching pages
    SESSION_REGEXP = '(?:|%s[A-Z0-9]+)' % re.escape(r';jsessionid=')

    is_logging = False

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.PAGES = {'https://[^/]+/':                               LoginPage,
                      'https://[^/]+/.*\.c.*':                        AccountsList,
                      'https://[^/]+/login/process%s' % self.SESSION_REGEXP:   AccountsList,
                      'https://[^/]+/accounting/listAccounts':        AccountsList,
                      'https://[^/]+/accounting/listOperations':      AccountsList,
                      'https://[^/]+/accounting/showAccountDetail.+': AccountsList,
                      'https://[^/]+/accounting/showMoreAccountOperations.*': AccountsList,
                     }
        Browser.__init__(self, *args, **kwargs)

    def viewing_html(self):
        """
        As the fucking HTTP server returns a document in unknown mimetype
        'application/vnd.wap.xhtml+xml' it is not recognized by mechanize.

        So this is a fucking hack.
        """
        return True

    def is_logged(self):
        logged = self.page and self.page.is_logged() or self.is_logging
        self.logger.debug('logged: %s' % (logged and 'yes' or 'no'))
        return logged

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        # Do we really need to login?
        if self.is_logged():
            self.logger.debug('already logged in')
            return

        self.is_logging = True
        # Are we on the good page?
        if not self.is_on_page(LoginPage):
            self.logger.debug('going to login page')
            Browser.home(self)
        self.logger.debug('attempting to log in')
        self.page.login(self.username, self.password)
        self.is_logging = False

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        self.addheaders = [
                ['User-agent', self.USER_AGENTS['desktop_firefox']]
            ]

    def get_accounts_list(self):
        self.logger.debug('accounts list required')
        self.home()
        return self.page.get_list()

    def home(self):
        """
        Ensure we are both logged and on the accounts list.
        """
        self.logger.debug('accounts list page required')
        if self.is_on_page(AccountsList) and self.page.is_accounts_list():
            self.logger.debug('already on accounts list')
            return

        # simply go to http(s)://the.doma.in/
        Browser.home(self)

        if self.is_on_page(LoginPage):
            if not self.is_logged():
                # So, we are not logged on the login page -- what about logging ourselves?
                self.login()
                # we assume we are logged in
            # for some regions, we may stay on the login page once we're
            # logged in, without being redirected...
            if self.is_on_page(LoginPage):
                # ... so we have to move by ourselves
                self.move_to_accounts_list()

    def move_to_accounts_list(self):
        """
        For regions where you can stay on http(s)://the.doma.in/ while you are
        logged in, move to the accounts list
        """
        self.location('%s://%s/accounting/listAccounts' % (self.PROTOCOL, self.DOMAIN))

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    def get_history(self, account):
        # some accounts may exist without a link to any history page
        if account._link_id is None:
            return
        history_url = account._link_id
        operations_count = 0

        # 1st, go on the account page
        self.logger.debug('going on: %s' % history_url)
        self.location('https://%s%s' % (self.DOMAIN, history_url))

        if self.page is None:
            return

        # Some regions have a "Show more" (well, actually "Voir les 25
        # suivants") link we have to use to get all the operations.
        # However, it does not show only the 25 next results, it *adds* them
        # to the current view. Therefore, we have to parse each new page using
        # an offset, in order to ignore all already-fetched operations.
        # This especially occurs on CA Centre.
        use_expand_url = bool(self.page.expand_history_page_url())
        date_guesser = LinearDateGuesser()
        while True:
            # we skip "operations_count" operations on each page if we are in the case described above
            operations_offset = operations_count if use_expand_url else 0
            for page_operation in self.page.get_history(date_guesser, operations_count, operations_offset):
                operations_count += 1
                yield page_operation
            history_url = self.page.expand_history_page_url() if use_expand_url else self.page.next_page_url()
            if not history_url:
                break
            self.logger.debug('going on: %s' % history_url)
            self.location('https://%s%s' % (self.DOMAIN, history_url))

    def dict_find_value(self, dictionary, value):
        """
            Returns the first key pointing on the given value, or None if none
            is found.
        """
        for k, v in dictionary.iteritems():
            if v == value:
                return k
        return None

    def do_transfer(self, account, to, amount, reason=None):
        """
            Transfer the given amount of money from an account to another,
            tagging the transfer with the given reason.
        """
        # access the transfer page
        transfer_page_unreachable_message = u'Could not reach the transfer page.'
        self.home()
        if not self.page.is_accounts_list():
            raise TransferError(transfer_page_unreachable_message)

        operations_url = self.page.operations_page_url()

        self.location('https://%s%s' % (self.DOMAIN, operations_url))
        transfer_url = self.page.transfer_page_url()

        abs_transfer_url = 'https://%s%s' % (self.DOMAIN, transfer_url)
        self.location(abs_transfer_url)
        if not self.page.is_transfer_page():
            raise TransferError(transfer_page_unreachable_message)

        source_accounts = self.page.get_transfer_source_accounts()
        target_accounts = self.page.get_transfer_target_accounts()

        # check that the given source account can be used
        if account not in source_accounts.values():
            raise TransferError('You cannot use account %s as a source account.' % account)

        # check that the given source account can be used
        if to not in target_accounts.values():
            raise TransferError('You cannot use account %s as a target account.' % to)

        # separate euros from cents
        amount_euros = int(amount)
        amount_cents = int((amount * 100) - (amount_euros * 100))

        # let's circumvent https://github.com/jjlee/mechanize/issues/closed#issue/17
        # using http://wwwsearch.sourceforge.net/mechanize/faq.html#usage
        adjusted_response = self.response().get_data().replace('<br/>', '<br />')
        response = mechanize.make_response(adjusted_response, [('Content-Type', 'text/html')], abs_transfer_url, 200, 'OK')
        self.set_response(response)

        # fill the form
        self.select_form(nr=0)
        self['numCompteEmetteur']     = ['%s' % self.dict_find_value(source_accounts, account)]
        self['numCompteBeneficiaire'] = ['%s' % self.dict_find_value(target_accounts, to)]
        self['montantPartieEntiere']  = '%s'   % amount_euros
        self['montantPartieDecimale'] = '%02d' % amount_cents
        if reason is not None:
            self['libelle'] = reason
        self.submit()

        # look for known errors
        content = unicode(self.response().get_data(), 'utf-8')
        insufficient_amount_message     = u'Montant insuffisant.'
        maximum_allowed_balance_message = u'Solde maximum autorisé dépassé.'

        if content.find(insufficient_amount_message) != -1:
            raise TransferError('The amount you tried to transfer is too low.')

        if content.find(maximum_allowed_balance_message) != -1:
            raise TransferError('The maximum allowed balance for the target account has been / would be reached.')

        # look for the known "all right" message
        ready_for_transfer_message = u'Vous allez effectuer un virement'
        if not content.find(ready_for_transfer_message):
            raise TransferError('The expected message "%s" was not found.' % ready_for_transfer_message)

        # submit the last form
        self.select_form(nr=0)
        submit_date = datetime.now()
        self.submit()

        # look for the known "everything went well" message
        content = unicode(self.response().get_data(), 'utf-8')
        transfer_ok_message = u'Vous venez d\'effectuer un virement du compte'
        if not content.find(transfer_ok_message):
            raise TransferError('The expected message "%s" was not found.' % transfer_ok_message)

        # We now have to return a Transfer object
        # the final page does not provide any transfer id, so we'll use the submit date
        transfer = Transfer(submit_date.strftime('%Y%m%d%H%M%S'))
        transfer.amount = amount
        transfer.origin = account
        transfer.recipient = to
        transfer.date = submit_date
        return transfer

    #def get_coming_operations(self, account):
    #    if not self.is_on_page(AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account._link_id)
    #    return self.page.get_operations()
