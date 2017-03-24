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


import hashlib
import time

from requests.exceptions import SSLError

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ParseError
from weboob.browser.exceptions import ServerError
from weboob.capabilities.bank import Account, TransferError, AccountNotFound
from weboob.capabilities.base import find_object

from .pages import AccountsList, LoginPage, NetissimaPage, TitrePage, TitreHistory,\
    TransferPage, TransferConfirmPage, BillsPage, StopPage, TitreDetails, TitreValuePage, ASVHistory,\
    ASVInvest, DetailFondsPage, IbanPage, ActionNeededPage, ReturnPage, ProfilePage


__all__ = ['IngBrowser']


def start_with_main_site(f):
    def wrapper(*args, **kwargs):
        browser = args[0]

        if browser.url and browser.url.startswith('https://bourse.ingdirect.fr/'):
            for i in xrange(3):
                try:
                    browser.location('https://bourse.ingdirect.fr/priv/redirectIng.php?pageIng=COMPTE')
                except ServerError:
                    pass
                else:
                    break
            browser.where = 'start'
        elif browser.url and browser.url.startswith('https://ingdirectvie.ingdirect.fr/'):
            browser.lifeback.go()
            browser.where = 'start'

        return f(*args, **kwargs)
    return wrapper


class IngBrowser(LoginBrowser):
    BASEURL = 'https://secure.ingdirect.fr'
    TIMEOUT = 60.0

    # avoid relogin every time
    lifeback = URL(r'https://ingdirectvie.ingdirect.fr/b2b2c/entreesite/EntAccExit', ReturnPage)

    # Login and error
    loginpage = URL('/public/displayLogin.jsf.*', LoginPage)
    errorpage = URL('.*displayCoordonneesCommand.*', StopPage)
    actioneeded = URL('/general\?command=displayTRAlertMessage', ActionNeededPage)

    # CapBank
    accountspage = URL('/protected/pages/index.jsf',
                       '/protected/pages/asv/contract/(?P<asvpage>.*).jsf', AccountsList)
    transferpage = URL('/protected/pages/cc/transfer/transferManagement.jsf', TransferPage)
    dotransferpage = URL('/general\?command=DisplayDoTransferCommand', TransferPage)
    valtransferpage = URL('/protected/pages/cc/transfer/create/transferCreateValidation.jsf', TransferConfirmPage)
    titredetails = URL('/general\?command=display.*', TitreDetails)
    ibanpage = URL('/protected/pages/common/rib/initialRib.jsf', IbanPage)
    # CapBank-Market
    netissima = URL('/data/asv/fiches-fonds/fonds-netissima.html', NetissimaPage)
    starttitre = URL('/general\?command=goToAccount&zone=COMPTE', TitrePage)
    titrepage = URL('https://bourse.ingdirect.fr/priv/portefeuille-TR.php', TitrePage)
    titrehistory = URL('https://bourse.ingdirect.fr/priv/compte.php\?ong=3', TitreHistory)
    titrerealtime = URL('https://bourse.ingdirect.fr/streaming/compteTempsReelCK.php', TitrePage)
    titrevalue = URL('https://bourse.ingdirect.fr/priv/fiche-valeur.php\?val=(?P<val>.*)&pl=(?P<pl>.*)&popup=1', TitreValuePage)
    asv_history = URL('https://ingdirectvie.ingdirect.fr/b2b2c/epargne/CoeLisMvt',
                      'https://ingdirectvie.ingdirect.fr/b2b2c/epargne/CoeDetMvt', ASVHistory)
    asv_invest = URL('https://ingdirectvie.ingdirect.fr/b2b2c/epargne/CoeDetCon', ASVInvest)
    detailfonds = URL('https://ingdirectvie.ingdirect.fr/b2b2c/fonds/PerDesFac\?codeFonds=(.*)', DetailFondsPage)
    # CapDocument
    billpage = URL('/protected/pages/common/estatement/eStatement.jsf', BillsPage)
    # CapProfile
    profile = URL('/protected/pages/common/profil/(?P<page>\w+).jsf', ProfilePage)

    __states__ = ['where']

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday')
        self.where = None
        LoginBrowser.__init__(self, *args, **kwargs)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.birthday, basestring)
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        self.do_logout()
        self.loginpage.go()

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)
        if self.page.error():
            raise BrowserIncorrectPassword()
        if self.errorpage.is_here():
            raise BrowserIncorrectPassword('Please login on website to fill the form and retry')
        self.page.check_for_action_needed()

    @need_login
    @start_with_main_site
    def get_accounts_list(self, get_iban=True):
        self.accountspage.go()
        self.where = "start"
        for acc in self.page.get_list():
            if get_iban and acc.type in [Account.TYPE_CHECKING, Account.TYPE_SAVINGS]:
                self.go_account_page(acc)
                acc.iban = self.ibanpage.go().get_iban()
            yield acc

    def get_account(self, _id):
        return find_object(self.get_accounts_list(get_iban=False), id=_id, error=AccountNotFound)

    def go_account_page(self, account):
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

    @need_login
    @start_with_main_site
    def get_coming(self, account):
        if account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()
        account = self.get_account(account.id)
        self.go_account_page(account)
        jid = self.page.get_history_jid()
        if jid is None:
            self.logger.info('There is no history for this account')
            return

        return self.page.get_coming()

    @need_login
    @start_with_main_site
    def get_history(self, account):
        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            for result in self.get_history_titre(account):
                yield result
            return

        elif account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()

        account = self.get_account(account.id)
        self.go_account_page(account)
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
    @start_with_main_site
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

    @start_with_main_site
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

    def go_on_asv_detail(self, account, link):
        try:
            if self.page.asv_is_other:
                jid = self.page.get_asv_jid()
                data = {'index': "index", 'javax.faces.ViewState': jid, 'index:j_idcl': "index:asvInclude:goToAsvPartner"}
                self.accountspage.go(data=data)
            else:
                self.accountspage.go(asvpage="manageASVContract")
                self.page.submit()
            self.page.submit()
            self.location(link)

            return True
        except SSLError:
            return False

    def go_investments(self, account):
        account = self.get_account(account.id)
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
                    account = self.get_account(account.id)
                    data['cptnbr'] = account._id
                    data['javax.faces.ViewState'] = account._jid

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
    @start_with_main_site
    def get_investments(self, account):
        if account.type not in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            raise NotImplementedError()
        self.go_investments(account)

        if self.where == u'titre':
            self.titrerealtime.go()
        elif self.page.asv_has_detail or account._jid:
            if self.go_on_asv_detail(account, '/b2b2c/epargne/CoeDetCon') is False:
                return iter([])

            self.where = u"asv"
        return self.page.iter_investments()

    def get_history_titre(self, account):
        self.go_investments(account)

        if self.where == u'titre':
            self.titrehistory.go()
        elif self.page.asv_has_detail or account._jid:
            if self.go_on_asv_detail(account, '/b2b2c/epargne/CoeLisMvt') is False:
                return iter([])
        else:
            return iter([])

        transactions = list()
        for tr in self.page.iter_history():
            transactions.append(tr)
        if self.asv_history.is_here():
            for tr in transactions:
                page = tr._detail.result().page if tr._detail else None
                tr.investments = list(page.get_investments()) if page and 'numMvt' in page.url else []
            self.lifeback.go()
        return iter(transactions)

    ############# CapDocument #############
    @start_with_main_site
    @need_login
    def get_subscriptions(self):
        self.billpage.go()
        if self.loginpage.is_here():
            self.do_login()
            return self.billpage.go().iter_account()
        else:
            return self.page.iter_account()

    @need_login
    def get_documents(self, subscription):
        self.billpage.go()
        data = {"AJAXREQUEST": "_viewRoot",
                "accountsel_form": "accountsel_form",
                subscription._formid: subscription._formid,
                "autoScroll": "",
                "javax.faces.ViewState": subscription._javax,
                "transfer_issuer_radio": subscription.id
                }
        self.billpage.go(data=data)
        return self.page.iter_documents(subid=subscription.id)

    def predownload(self, bill):
        self.page.postpredown(bill._localid)

    ############# CapProfile #############
    @start_with_main_site
    @need_login
    def get_profile(self):
        profile = self.profile.go(page='coordonnees').get_profile()
        self.profile.go(page='infosperso').update_profile(profile)
        return profile
