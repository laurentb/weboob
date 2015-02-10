# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot
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
import hashlib
import time

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.capabilities.bank import Account, TransferError

from .pages import AccountsList, LoginPage, TitrePage, TitreHistory,\
    TransferPage, TransferConfirmPage, BillsPage, StopPage, TitreDetails


__all__ = ['IngBrowser']


def check_bourse(f):
    def wrapper(*args):
        browser = args[0]
        if browser.where == u"titre":
            browser.location("https://bourse.ingdirect.fr/priv/redirectIng.php?pageIng=COMPTE")
            browser.where = u"start"
        return f(*args)
    return wrapper


class IngBrowser(LoginBrowser):
    BASEURL = 'https://secure.ingdirect.fr'

    # Login and error
    loginpage = URL('/public/displayLogin.jsf.*', LoginPage)
    errorpage = URL('.*displayCoordonneesCommand.*', StopPage)

    # CapBank
    accountspage = URL('/protected/pages/index.jsf', AccountsList)
    transferpage = URL('/protected/pages/cc/transfer/transferManagement.jsf', TransferPage)
    dotransferpage = URL('/general\?command=DisplayDoTransferCommand', TransferPage)
    valtransferpage = URL('/protected/pages/cc/transfer/create/transferCreateValidation.jsf', TransferConfirmPage)
    titredetails = URL('/general\?command=display.*', TitreDetails)
    # CapBank-Market
    starttitre = URL('/general\?command=goToAccount&zone=COMPTE', TitrePage)
    titrepage = URL('https://bourse.ingdirect.fr/priv/portefeuille-TR.php', TitrePage)
    titrehistory = URL('https://bourse.ingdirect.fr/priv/compte.php\?ong=3', TitreHistory)
    titrerealtime = URL('https://bourse.ingdirect.fr/streaming/compteTempsReelCK.php', TitrePage)
    # CapBill
    billpage = URL('/protected/pages/common/estatement/eStatement.jsf', BillsPage)

    def __init__(self, *args, **kwargs):
        self.birthday = re.sub(r'[^\d]', '', kwargs.pop('birthday'))
        self.where = None
        LoginBrowser.__init__(self, *args, **kwargs)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.birthday, basestring)
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        self.do_logout()
        self.loginpage.stay_or_go()

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)
        if self.page.error():
            raise BrowserIncorrectPassword()
        if self.errorpage.is_here():
            raise BrowserIncorrectPassword('Please login on website to fill the form and retry')

    @need_login
    @check_bourse
    def get_accounts_list(self):
        self.accountspage.go()
        self.where = "start"
        return self.page.get_list()

    @need_login
    @check_bourse
    def get_coming(self, account):
        if account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()
        if self.where != "start":
            self.accountspage.go()
        data = {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }
        self.accountspage.go(data=data)
        self.where = "history"
        jid = self.page.get_history_jid()
        if jid is None:
            self.logger.info('There is no history for this account')
            return

        return self.page.get_coming()

    @need_login
    @check_bourse
    def get_history(self, account):
        if account.type in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE):
            for result in self.get_history_titre(account):
                yield result
            return
        elif account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()

        if self.where != "start":
            self.accountspage.go()
        data = {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }
        self.accountspage.go(data=data)
        self.where = "history"
        jid = self.page.get_history_jid()
        if jid is None:
            self.logger.info('There is no history for this account')
            return

        if account.type == Account.TYPE_CHECKING:
            history_function = AccountsList.get_transactions_cc
            index = -1  # disable the index. It works without it on CC
        else:
            history_function = AccountsList.get_transactions_others
            index = 0
        hashlist = []
        while True:
            i = index
            for transaction in history_function(self.page, index=index):
                transaction.id = hashlib.md5(transaction._hash).hexdigest()
                while transaction.id in hashlist:
                    transaction.id = hashlib.md5(transaction.id + "1").hexdigest()
                hashlist.append(transaction.id)
                i += 1
                yield transaction
            # if there is no more transactions, it is useless to continue
            if self.page.islast() or i == index:
                return
            if index >= 0:
                index = i
            data = {"AJAX:EVENTS_COUNT": 1,
                    "AJAXREQUEST": "_viewRoot",
                    "autoScroll": "",
                    "index": "index",
                    "index:%s:moreTransactions" % jid: "index:%s:moreTransactions" % jid,
                    "javax.faces.ViewState": account._jid
                    }
            self.accountspage.go(data=data)

    @need_login
    @check_bourse
    def get_recipients(self, account):
        self.transferpage.stay_or_go()
        if self.page.ischecked(account.id):
            return self.page.get_recipients()
        else:
            # It is hard to check the box and to get the real list.
            # We try an alternative way like normal users
            self.get_history(account).next()
            self.transferpage.stay_or_go()
            return self.page.get_recipients()

    @check_bourse
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
            self.transferpage.open(data=self.page.buildonclick(recipient, account))
            self.page.transfer(recipient, amount, reason)
            self.valtransferpage.go()
            if not self.valtransferpage.is_here():
                raise TransferError("Invalid transfer (no confirmation page)")
            else:
                self.page.confirm(self.password)
                self.valtransferpage.go()
                recap = self.page.recap()
                if len(list(recap)) == 0:
                    raise ParseError('Unable to find confirmation')
                return self.page.recap()
        else:
            raise TransferError('Recipient not found')


    def go_investments(self, account):
        if self.where != "start":
            self.accountspage.go()
        data = {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }

        # On ASV pages, data maybe not available.
        for i in range(5):
            if i > 0:
                self.logger.debug('Investments list empty, retrying in %s seconds...', (2**i))
                time.sleep(2**i)

                if i > 1:
                    self.do_logout()
                    self.do_login()
                    self.accountspage.go()

            self.accountspage.go(data=data)

            if not self.page.has_error():
                break

        else:
            self.logger.warning("Unable to get investments list...")

        if self.page.is_asv:
            return

        self.starttitre.go()
        self.where = u"titre"
        self.titrepage.go()

    @need_login
    @check_bourse
    def get_investments(self, account):
        if account.type not in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE):
            raise NotImplementedError()
        self.go_investments(account)

        if self.where == u'titre':
            self.titrerealtime.go()
        return self.page.iter_investments()

    def get_history_titre(self, account):
        self.go_investments(account)

        if self.where == u'titre':
            self.titrehistory.go()
            return self.page.iter_history()
        else:
            # No history for ASV accounts.
            raise NotImplementedError()

    ############# CapBill #############
    @need_login
    def get_subscriptions(self):
        return self.billpage.go().iter_account()

    @need_login
    def get_bills(self, subscription):
        self.billpage.go()
        data = {"AJAXREQUEST": "_viewRoot",
                "accountsel_form": "accountsel_form",
                subscription._formid: subscription._formid,
                "autoScroll": "",
                "javax.faces.ViewState": subscription._javax,
                "transfer_issuer_radio": subscription.id
                }
        self.billpage.go(data=data)
        return self.page.iter_bills(subid=subscription.id)

    def predownload(self, bill):
        self.page.postpredown(bill._localid)
