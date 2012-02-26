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


from .accounts_list import AccountsList
from .transactions import AccountHistory, AccountComing
from .transfer import TransferPage, TransferConfirmPage, TransferCompletePage
from .login import LoginPage, ConfirmPage, ChangePasswordPage, MessagePage

class AccountPrelevement(AccountsList): pass

__all__ = ['AccountsList', 'AccountComing', 'AccountHistory', 'LoginPage',
           'ConfirmPage', 'MessagePage', 'AccountPrelevement', 'ChangePasswordPage',
           'TransferPage', 'TransferConfirmPage', 'TransferCompletePage']
