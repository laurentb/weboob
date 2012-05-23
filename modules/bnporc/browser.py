# -*- coding: utf-8 -*-

# Copyright(C) 2009-2012  Romain Bignon
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
from datetime import datetime
from logging import warning

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BrowserPasswordExpired
from weboob.capabilities.bank import TransferError, Transfer
from .pages import AccountsList, AccountHistory, ChangePasswordPage, \
                   AccountComing, AccountPrelevement, TransferPage, \
                   TransferConfirmPage, TransferCompletePage, \
                   LoginPage, ConfirmPage, InfoMessagePage, \
                   MessagePage, MessagesPage


__all__ = ['BNPorc']


class BNPorc(BaseBrowser):
    DOMAIN = 'www.secure.bnpparibas.net'
    PROTOCOL = 'https'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*pageId=unedescomptes.*':                    AccountsList,
             '.*pageId=releveoperations.*':                 AccountHistory,
             '.*FicheA':                                    AccountHistory,
             '.*Action=SAF_CHM.*':                          ChangePasswordPage,
             '.*pageId=mouvementsavenir.*':                 AccountComing,
             '.*NS_AVEDP.*':                                AccountPrelevement,
             '.*NS_VIRDF.*':                                TransferPage,
             '.*NS_VIRDC.*':                                TransferConfirmPage,
             '.*/NS_VIRDA\?stp=(?P<id>\d+).*':              TransferCompletePage,
             '.*type=homeconnex.*':                         LoginPage,
             '.*layout=HomeConnexion.*':                    ConfirmPage,
             '.*SAF_CHM_VALID.*':                           ConfirmPage,
             '.*Action=DSP_MSG.*':                          InfoMessagePage,
             '.*MessagesRecus.*':                           MessagesPage,
             '.*BmmFicheLireMessage.*':                     MessagePage,
            }

    def __init__(self, *args, **kwargs):
        self.rotating_password = kwargs.pop('rotating_password', None)
        self.password_changed_cb = kwargs.pop('password_changed_cb', None)
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/HomeConnexion?type=homeconnex')

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

        #self.readurl('/SAF_SOA?Action=6')

    def change_password(self, new_password):
        assert new_password.isdigit() and len(new_password) == 6

        buf = self.readurl('https://www.secure.bnpparibas.net/NSFR?Action=SAF_CHM', if_fail='raise')
        buf = buf[buf.find('/SAF_CHM?Action=SAF_CHM'):]
        buf = buf[:buf.find('"')]
        self.location(buf)
        assert self.is_on_page(ChangePasswordPage)

        #self.readurl('/banque/portail/particulier/bandeau')
        #self.readurl('/common/vide.htm')

        self.page.change_password(self.password, new_password)

        if not self.is_on_page(ConfirmPage) or self.page.get_error() is not None:
            self.logger.error('Oops, unable to change password (%s)'
                % (self.page.get_error() if self.is_on_page(ConfirmPage) else 'unknown'))
            return

        self.password, self.rotating_password = (new_password, self.password)

        if self.password_changed_cb:
            self.password_changed_cb(self.rotating_password, self.password)

    def check_expired_password(func):
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except BrowserPasswordExpired:
                if self.rotating_password is not None:
                    warning('[%s] Your password has expired. Switching...' % self.username)
                    self.change_password(self.rotating_password)
                    return func(self, *args, **kwargs)
                else:
                    raise
        return inner

    @check_expired_password
    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def iter_history(self, id):
        if id is None:
            return iter([])

        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        execution = self.page.document.xpath('//form[@name="goToApplication"]/input[@name="execution"]')[0].attrib['value']
        data = {'gt':           'homepage:basic-theme',
                'externalIAId': 'IAStatements',
                'cboFlowName':  'flow/iastatement',
                'contractId':   id,
                'groupId':      '-2',
                'pastOrPendingOperations': 1,
                'groupSelected':'-2',
                'step':         'STAMENTS',
                'pageId':       'releveoperations',
                'operationsPerPage': 100,
                '_eventId':     'changeOperationsPerPage',
                'sendEUD':      'true',
                'execution':    execution,
               }

        self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/FicheA', urllib.urlencode(data))

        execution = self.page.document.xpath('//form[@name="displayStatementForm"]/input[@name="_flowExecutionKey"]')[0].attrib['value']
        data = {'_eventId':             'changeOperationsPerPage',
                'categoryId':           '',
                'contractId':           '',
                '_flowExecutionKey':    execution,
                'groupId':              '',
                'listCheckedOp':        '',
                'myPage':               1,
                'operationId':          '',
                'operationsPerPage':    100,
                'pageId':               'releveoperations',
               }
        self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/FicheA', urllib.urlencode(data))

        return self.page.iter_operations()

    def iter_coming_operations(self, id):
        if id is None:
            return iter([])

        if not self.is_on_page(AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')
        execution = self.page.get_execution_id()
        self.location('/banque/portail/particulier/FicheA?externalIAId=IAStatements&contractId=%d&pastOrPendingOperations=2&pageId=mouvementsavenir&_flowExecutionKey=%s' % (int(id), execution))
        return self.page.iter_operations()

    @check_expired_password
    def get_transfer_accounts(self):
        if not self.is_on_page(TransferPage):
            self.location('/NS_VIRDF')

        assert self.is_on_page(TransferPage)
        return self.page.get_accounts()

    @check_expired_password
    def transfer(self, from_id, to_id, amount, reason=None):
        if not self.is_on_page(TransferPage):
            self.location('/NS_VIRDF')

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
            self['idMessage'] = thread.id
        # the JS does this, but it makes us unable to read unread messages
        #if unread:
        #    self['newMsg'] = thread.id
        self.submit()
        assert self.is_on_page(MessagePage)
        thread.root.content = self.page.get_content()
        return thread
