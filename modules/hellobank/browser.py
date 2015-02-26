# -*- coding: utf-8 -*-

# Copyright(C) 2009-2012 Romain Bignon
# Copyright(C) 2013-2015 Christophe Lampin
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
import mechanize
from datetime import datetime

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.capabilities.bank import TransferError, Transfer

from .perso.accounts_list import AccountsList, AccountPrelevement
from .perso.transactions import AccountHistory, AccountComing
from .perso.transfer import TransferPage, TransferConfirmPage, TransferCompletePage
from .perso.login import LoginPage, ConfirmPage, InfoMessagePage
from .perso.messages import MessagePage, MessagesPage

__all__ = ['HelloBank']


class HelloBank(Browser):
    DOMAIN = 'client.hellobank.fr'
    PROTOCOL = 'https'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*TableauBord.*':                             AccountsList,
             '.*type=folder.*':                             AccountHistory,
             '.*pageId=mouvementsavenir.*':                 AccountComing,
             '.*NS_AVEDP.*':                                AccountPrelevement,
             '.*NS_VIRDF.*':                                TransferPage,
             '.*NS_VIRDC.*':                                TransferConfirmPage,
             '.*/NS_VIRDA\?stp=(?P<id>\d+).*':              TransferCompletePage,
             '.*type=homeconnex.*':                         LoginPage,
             '.*layout=HomeConnexion.*':                    ConfirmPage,
             '.*SAF_CHM_VALID.*':                           ConfirmPage,
             '.*Action=DSP_MSG.*':                          InfoMessagePage,
             '.*Messages_recus.*':                          MessagesPage,
             '.*Lire_Message.*':                            MessagePage,
            }

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://client.hellobank.fr/banque/portail/digitale/HomeConnexion?type=homeconnex')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.home()

        self.page.login(self.username, self.password)
        self.location('/NSFR?Action=DSP_VGLOBALE', no_login=True)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        # We have to parse transfer page to get the IBAN numbers
        if not self.is_on_page(TransferPage):
            now = datetime.now()
            self.location('/NS_VIRDF?Origine=DSP_VIR&stp=%s' % now.strftime("%Y%m%d%H%M%S"))

        accounts = self.page.get_accounts()
        if len(accounts) == 0:
            self.logger.warning('no accounts')
            # oops, no accounts? check if we have not exhausted the allowed use
            # of this password
            for img in self.document.getroot().cssselect('img[align="middle"]'):
                if img.attrib.get('alt', '') == 'Changez votre code secret':
                    raise BrowserPasswordExpired('Your password has expired')
        self.location('/NSFR?Action=DSP_VGLOBALE')
        return self.page.get_list(accounts)

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_IBAN_from_account(self, account):
        self.go_to_history_page(account)
        return self.page.get_IBAN()

    def go_to_history_page(self,account):
        if account._link_id is None:
            raise NotImplementedError()

        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        data = {'gt': 'homepage:basic-theme',
                'externalIAId': 'IAStatements',
                'cboFlowName': 'flow/iastatement',
                'contractId': account._link_id,
                'groupId': '-2',
                'pastOrPendingOperations': 1,
                'groupSelected':'-2',
                'step': 'STAMENTS',
                'pageId': 'releveoperations',
                'sendEUD': 'true',
                }
        self.location('/udc', urllib.urlencode(data))

    def go_to_coming_operations_page(self,account):
        if account._link_id is None:
            raise NotImplementedError()

        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        data = {'gt': 'homepage:basic-theme',
                'externalIAId': 'IAStatements',
                'cboFlowName': 'flow/iastatement',
                'contractId': account._link_id,
                'groupId': '-2',
                'pastOrPendingOperations': 2,
                'groupSelected':'-2',
                'step': 'STAMENTS',
                'pageId': 'mouvementsavenir',
                'sendEUD': 'true',
               }
        self.location('/udc', urllib.urlencode(data))

    def iter_history(self, account):
        self.go_to_history_page(account)
        return self.page.iter_operations()

    def iter_coming_operations(self, account):
        self.go_to_coming_operations_page(account)
        return self.page.iter_coming_operations()

    def get_transfer_accounts(self):
        if not self.is_on_page(TransferPage):
            self.location('/NS_VIRDF')

        assert self.is_on_page(TransferPage)
        return self.page.get_accounts()

    def transfer(self, from_id, to_id, amount, reason=None):
        if not self.is_on_page(TransferPage):
            self.location('/NS_VIRDF')

        # Need to clean HTML before parse it
        html = self.response().get_data().replace("<!input", "<input")
        response = mechanize.make_response(
        html, [("Content-Type", "text/html")],
        "https://client.hellobank.fr/NS_VIRDF", 200, "OK")
        self.set_response(response)

        accounts = self.page.get_accounts()
        self.page.transfer(from_id, to_id, amount, reason)

        if not self.is_on_page(TransferCompletePage):
            raise TransferError('An error occured during transfer')

        transfer = Transfer(self.page.get_id())
        transfer.amount = amount
        transfer.origin = accounts[from_id].label
        transfer.recipient = accounts[to_id].label
        transfer.date = datetime.now()
        return transfer

    def messages_page(self):
        if not self.is_on_page(MessagesPage):
            if not self.is_on_page(AccountsList):
                self.location('/NSFR?Action=DSP_VGLOBALE')
            self.location(self.page.get_messages_link())
        assert self.is_on_page(MessagesPage)

    def iter_threads(self):
        self.messages_page()
        for thread in self.page.iter_threads():
            yield thread

    def get_thread(self, thread):
        self.messages_page()
        if not hasattr(thread, '_link_id') or not thread._link_id:
            for t in self.iter_threads():
                if t.id == thread.id:
                    thread = t
                    break
        # mimic validerFormulaire() javascript
        # yes, it makes no sense
        page_id, unread = thread._link_id
        self.select_form('listerMessages')
        self.form.set_all_readonly(False)
        self['identifiant'] = page_id
        if len(thread.id):
            self['idMessage'] = thread.id.encode('utf-8')
        # the JS does this, but it makes us unable to read unread messages
        #if unread:
        #    self['newMsg'] = thread.id
        self.submit()
        assert self.is_on_page(MessagePage)
        thread.root.content = self.page.get_content()
        return thread
