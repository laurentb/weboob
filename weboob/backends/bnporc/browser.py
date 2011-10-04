# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon
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


from datetime import datetime
from logging import warning

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.bank import TransferError, Transfer
from weboob.backends.bnporc import pages
from .errors import PasswordExpired


__all__ = ['BNPorc']


class BNPorc(BaseBrowser):
    DOMAIN = 'www.secure.bnpparibas.net'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {'.*identifiant=DOSSIER_Releves_D_Operation.*': pages.AccountsList,
             '.*SAF_ROP.*':                                 pages.AccountHistory,
             '.*Action=SAF_CHM.*':                          pages.ChangePasswordPage,
             '.*NS_AVEDT.*':                                pages.AccountComing,
             '.*NS_AVEDP.*':                                pages.AccountPrelevement,
             '.*NS_VIRDF.*':                                pages.TransferPage,
             '.*NS_VIRDC.*':                                pages.TransferConfirmPage,
             '.*/NS_VIRDA\?stp=(?P<id>\d+).*':              pages.TransferCompletePage,
             '.*Action=DSP_VGLOBALE.*':                     pages.LoginPage,
             '.*type=homeconnex.*':                         pages.LoginPage,
             '.*layout=HomeConnexion.*':                    pages.ConfirmPage,
             '.*SAF_CHM_VALID.*':                           pages.ConfirmPage,
            }

    def __init__(self, *args, **kwargs):
        self.rotating_password = kwargs.pop('rotating_password', None)
        self.password_changed_cb = kwargs.pop('password_changed_cb', None)
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/HomeConnexion?type=homeconnex')

    def is_logged(self):
        return not self.is_on_page(pages.LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(pages.LoginPage):
            self.location('https://www.secure.bnpparibas.net/banque/portail/particulier/HomeConnexion?type=homeconnex')

        self.page.login(self.username, self.password)
        self.location('/NSFR?Action=DSP_VGLOBALE', no_login=True)

        if self.is_on_page(pages.LoginPage):
            raise BrowserIncorrectPassword()

    def change_password(self, new_password):
        assert new_password.isdigit() and len(new_password) == 6

        self.location('https://www.secure.bnpparibas.net/SAF_CHM?Action=SAF_CHM')
        assert self.is_on_page(pages.ChangePasswordPage)

        self.page.change_password(self.password, new_password)

        if not self.is_on_page(pages.ConfirmPage):
            self.logger.error('Oops, unable to change password')
            return

        self.password, self.rotating_password = (new_password, self.password)

        if self.password_changed_cb:
            self.password_changed_cb(self.rotating_password, self.password)

    def check_expired_password(func):
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except PasswordExpired:
                if self.rotating_password is not None:
                    warning('[%s] Your password has expired. Switching...' % self.username)
                    self.change_password(self.rotating_password)
                    return func(self, *args, **kwargs)
                else:
                    raise
        return inner

    @check_expired_password
    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(pages.AccountsList):
            self.location('/NSFR?Action=DSP_VGLOBALE')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if not self.is_on_page(pages.AccountHistory) or self.page.account.id != account.id:
            self.location('/SAF_ROP?ch4=%s' % account.link_id)
        return self.page.get_operations()

    def get_coming_operations(self, account):
        if not self.is_on_page(pages.AccountComing) or self.page.account.id != account.id:
            self.location('/NS_AVEDT?ch4=%s' % account.link_id)
        return self.page.get_operations()

    def get_transfer_accounts(self):
        if not self.is_on_page(pages.TransferPage):
            self.location('/NS_VIRDF')

        assert self.is_on_page(pages.TransferPage)
        return self.page.get_accounts()

    def transfer(self, from_id, to_id, amount, reason=None):
        if not self.is_on_page(pages.TransferPage):
            self.location('/NS_VIRDF')

        accounts = self.page.get_accounts()
        self.page.transfer(from_id, to_id, amount, reason)

        if not self.is_on_page(pages.TransferCompletePage):
            raise TransferError('An error occured during transfer')

        transfer = Transfer(self.page.get_id())
        transfer.amount = amount
        transfer.origin = accounts[from_id].label
        transfer.recipient = accounts[to_id].label
        transfer.date = datetime.now()
        return transfer
