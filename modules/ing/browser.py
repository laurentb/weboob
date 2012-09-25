# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
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
import hashlib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.bank import Account, TransferError
from .pages import AccountsList, LoginPage, LoginPage2, \
                   AccountHistory, TransferPage, TransferConfirmPage


__all__ = ['Ing']


class Ing(BaseBrowser):
    DOMAIN = 'secure.ingdirect.fr'
    PROTOCOL = 'https'
    DEBUG_HTTP = False
    #DEBUG_HTTP = True
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*displayTRAccountSummary.*':    AccountsList,
             '.*displayLogin.jsf':             LoginPage,
             '.*displayLogin.jsf.*':           LoginPage2,
             '.*accountDetail.jsf.*':          AccountHistory,
             '.*displayTRHistoriqueLA.*':      AccountHistory,
             '.*transferManagement.jsf':       TransferPage,
             '.*DisplayDoTransferCommand.*':   TransferPage,
             '.*transferCreateValidation.jsf': TransferConfirmPage
            }
    CERTHASH = "fba557b387cccc3d71ba038f9ef1de4d71541d7954744c79f6a7ff5f3cd4dc12"

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday', None)
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://secure.ingdirect.fr/public/displayLogin.jsf')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.birthday, basestring)
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://secure.ingdirect.fr/\
                           public/displayLogin.jsf')

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)
        if self.page.error():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/general?command=displayTRAccountSummary')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/general?command=displayTRAccountSummary')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def viewing_html(self):
        # To prevent unknown mimetypes sent by server, we assume we
        # are always on a HTML document.
        return True

    def get_history(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        # The first and the second letter of the label are the account type
        if account.label[0:2] == "CC":
            self.location('https://secure.ingdirect.fr/protected/pages/cc/accountDetail.jsf')
        elif account.label[0:2] == "LA":
            # we want "displayTRHistoriqueLA" but this fucking page
            # is not directly available...
            self.location('https://secure.ingdirect.fr/general?command=goToAccount&account=%d&zone=COMPTE' % int(account._index))
        else:
            raise NotImplementedError()
        while 1:
            hashlist = []
            for transaction in self.page.get_transactions():
                while transaction.id in hashlist:
                    transaction.id = hashlib.md5(transaction.id + "1")
                hashlist.append(transaction.id)
                yield transaction
            if self.page.islast():
                return

            # XXX server sends an unknown mimetype, we overload viewing_html() above to
            # prevent this issue.
            self.page.next_page()

    def get_recipients(self, account):
        if not self.is_on_page(TransferPage):
            self.location('https://secure.ingdirect.fr/protected/pages/cc/transfer/transferManagement.jsf')
        if self.page.ischecked(account):
            return self.page.get_recipients()
        else:
            # It is hard to check the box and to get the real list. We try an alternative way like normal users
            self.get_history(account.id).next()
            self.location('https://secure.ingdirect.fr/general?command=DisplayDoTransferCommand')
            return self.page.get_recipients()

    def transfer(self, account, recipient, amount, reason):
        found = False
        # Automatically get the good transfer page
        self.logger.debug('Search %s' % recipient)
        for destination in self.get_recipients(account):
            self.logger.debug('Found %s ' % destination.id)
            if destination.id == recipient:
                found = True
                recipient = destination
                break
        if found:
            self.openurl('/protected/pages/cc/transfer/transferManagement.jsf', self.page.buildonclick(recipient, account))
            self.page.transfer(recipient, amount, reason)
            self.location('/protected/pages/cc/transfer/create/transferCreateValidation.jsf')
            if not self.is_on_page(TransferConfirmPage):
                raise TransferError("Invalid transfer (no confirmation page)")
            else:
                self.page.confirm(self.password)
                self.location('/protected/pages/cc/transfer/create/transferCreateValidation.jsf')
                return self.page.recap()
        else:
            raise TransferError('Recipient not found')
