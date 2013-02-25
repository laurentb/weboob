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
import urllib
import hashlib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.bank import Account, TransferError
from .pages import AccountsList, LoginPage, \
                   TransferPage, TransferConfirmPage, \
                   BillsPage, StopPage


__all__ = ['Ing']


class Ing(BaseBrowser):
    DOMAIN = 'secure.ingdirect.fr'
    PROTOCOL = 'https'
    DEBUG_HTTP = False
    #DEBUG_HTTP = True
    ENCODING = "utf-8"
    PAGES = {'.*pages/index.jsf.*':            AccountsList,
             '.*displayLogin.jsf.*':           LoginPage,
             '.*transferManagement.jsf':       TransferPage,
             '.*onHoldTransferManagement.jsf': TransferPage,
             '.*DisplayDoTransferCommand.*':   TransferPage,
             '.*transferCreateValidation.jsf': TransferConfirmPage,
             '.*eStatement.jsf':               BillsPage,
             '.*displayCoordonneesCommand.*':  StopPage,
            }
    CERTHASH = "fba557b387cccc3d71ba038f9ef1de4d71541d7954744c79f6a7ff5f3cd4dc12"

    loginpage = '/public/displayLogin.jsf'
    accountspage = '/protected/pages/index.jsf'
    transferpage = '/protected/pages/cc/transfer/transferManagement.jsf'
    dotransferpage = '/general?command=DisplayDoTransferCommand'
    valtransferpage = '/protected/pages/cc/transfer/create/transferCreateValidation.jsf'
    where = None

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday', None)
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location(self.loginpage)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.birthday, basestring)
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        if not self.is_on_page(LoginPage):
            self.location(self.loginpage)

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)
        if self.page.error():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList) or self.where != "start":
            self.location(self.accountspage)
        self.where = "start"
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList) or self.where != "start":
            self.location(self.accountspage)
        self.where = "start"

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
        if self.where != "start":
            self.location(self.accountspage)
        data = {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }
        self.location(self.accountspage, urllib.urlencode(data))
        self.where = "history"
        jid = self.page.get_history_jid()
        index = 0 # index, we get always the same page, but with more informations
        while 1:
            hashlist = []
            i = index
            for transaction in self.page.get_transactions(index):
                while transaction.id in hashlist:
                    transaction.id = hashlib.md5(transaction.id + "1").hexdigest()
                hashlist.append(transaction.id)
                i += 1
                yield transaction
            # if there is no more transactions, it is useless to continue
            if i == index or self.page.islast():
                return
            index = i
            data = {"AJAX:EVENTS_COUNT": 1,
                    "AJAXREQUEST": "_viewRoot",
                    "autoScroll": "",
                    "index": "index",
                    "index:%s:moreTransactions" % jid: "index:%s:moreTransactions" % jid,
                    "javax.faces.ViewState": account._jid
                    }
            self.location(self.accountspage, urllib.urlencode(data))

    def get_recipients(self, account):
        if not self.is_on_page(TransferPage):
            self.location(self.transferpage)
        if self.page.ischecked(account):
            return self.page.get_recipients()
        else:
            # It is hard to check the box and to get the real list.
            # We try an alternative way like normal users
            self.get_history(account.id).next()
            self.location(self.dotransferpage)
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
            self.openurl(self.transferpage,
                    self.page.buildonclick(recipient, account))
            self.page.transfer(recipient, amount, reason)
            self.location(self.valtransferpage)
            if not self.is_on_page(TransferConfirmPage):
                raise TransferError("Invalid transfer (no confirmation page)")
            else:
                self.page.confirm(self.password)
                self.location(self.valtransferpage)
                return self.page.recap()
        else:
            raise TransferError('Recipient not found')

    def get_subscriptions(self):
        self.location('/protected/pages/common/estatement/eStatement.jsf')
        return self.page.iter_account()

    def get_bills(self, subscription):
        if not self.is_on_page(BillsPage):
            self.location('/protected/pages/common/estatement/eStatement.jsf')
        self.page.selectyear(subscription._localid)
        while 1:
            for bill in self.page.iter_bills(subscription.id):
                yield bill
            if self.page.islast():
                return

            self.page.next_page()

    def predownload(self, bill):
        self.page.postpredown(bill._localid)
