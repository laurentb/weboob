# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import BPBrowser


__all__ = ['BPBackend']


class BPBackend(BaseBackend, ICapBank):
    NAME = 'bp'
    MAINTAINER = u'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.e'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'La Banque Postale French bank website'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Account ID', masked=False),
                           ValueBackendPassword('password', label='Password', regexp='^(\d{6}|)$'))
    BROWSER = BPBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        for history in self.browser.get_history(account):
            yield history

    def transfer(self, id_from, id_to, amount, reason=None):
        from_account = self.get_account(id_from)
        to_account = self.get_account(id_to)

        #TODO: retourner le numero du virement
        #TODO: support the 'reason' parameter
        return self.browser.make_transfer(from_account, to_account, amount)

# XXX This hack is useful to workaround a bug in OpenSSL 1.0.1c-4 in Debian Wheezy.
# See https://symlink.me/issues/863 and
# http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=666051
import ssl
def mywrap_socket(sock, *args, **kwargs):
    kwargs['ssl_version'] = kwargs.get('ssl_version', ssl.PROTOCOL_TLSv1)
    return ssl.wrap_socketold(sock, *args, **kwargs)
ssl.wrap_socketold=ssl.wrap_socket
ssl.wrap_socket=mywrap_socket
