# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.bank import AccountNotFound, Transfer, TransferError
from weboob.backends.cragr import pages
import mechanize
from datetime import datetime

# Browser
class Cragr(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']

    is_logging = False

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.PAGES = {'https://%s/'              % website:   pages.LoginPage,
                      'https://%s/.*\.c.*'       % website:   pages.AccountsList,
                      'https://%s/login/process' % website:   pages.AccountsList,
                      'https://%s/accounting/listAccounts' % website: pages.AccountsList,
                      'https://%s/accounting/listOperations' % website: pages.AccountsList,
                     }
        BaseBrowser.__init__(self, *args, **kwargs)

    def viewing_html(self):
        """
        As the fucking HTTP server returns a document in unknown mimetype
        'application/vnd.wap.xhtml+xml' it is not recognized by mechanize.

        So this is a fucking hack.
        """
        return True

    def is_logged(self):
        return self.page and self.page.is_logged() or self.is_logging

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.is_logging = True
        if not self.is_on_page(pages.LoginPage):
            self.home()

        self.page.login(self.username, self.password)
        self.is_logging = False

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList) or self.page.is_account_page():
            self.home()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    def get_history(self, account):
        page_url = account.link_id
        operations_count = 0
        while (page_url):
            self.location('https://%s%s' % (self.DOMAIN, page_url))
            for page_operation in self.page.get_history(operations_count):
                operations_count += 1
                yield page_operation
            page_url = self.page.next_page_url()

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
        if not account in source_accounts.values():
            raise TransferError('You cannot use account %s as a source account.' % account)

        # check that the given source account can be used
        if not to in target_accounts.values():
            raise TransferError('You cannot use account %s as a target account.' % to)

        # separate euros from cents
        amount_euros = int(amount)
        amount_cents = int((amount - amount_euros) * 100)

        # let's circumvent https://github.com/jjlee/mechanize/issues/closed#issue/17
        # using http://wwwsearch.sourceforge.net/mechanize/faq.html#usage
        adjusted_response = self.response().get_data().replace('<br/>', '<br />')
        response = mechanize.make_response(adjusted_response, [('Content-Type', 'text/html')], abs_transfer_url, 200, 'OK')
        self.set_response(response)

        # fill the form
        self.select_form(nr=0)
        self['numCompteEmetteur']     = ['%s' % self.dict_find_value(source_accounts, account)]
        self['numCompteBeneficiaire'] = ['%s' % self.dict_find_value(target_accounts, to)]
        self['montantPartieEntiere']  = '%s' % amount_euros
        self['montantPartieDecimale'] = '%s' % amount_cents
        self['libelle']               = reason
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
    #    if not self.is_on_page(pages.AccountComing) or self.page.account.id != account.id:
    #        self.location('/NS_AVEEC?ch4=%s' % account.link_id)
    #    return self.page.get_operations()
