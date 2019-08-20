# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from .login import LoginPage
from .accounts_page import AccountsPage, HistoryPage, ComingPage
from .transfer_page import (
    DebitAccountsPage, CreditAccountsPage, TransferPage, AddRecipientPage,
    OtpChannelsPage, ConfirmOtpPage,
)
from .profile_page import ProfilePage


__all__ = ['LoginPage', 'AccountsPage',
           'HistoryPage', 'ComingPage',
           'DebitAccountsPage', 'CreditAccountsPage', 'TransferPage',
           'AddRecipientPage', 'OtpChannelsPage', 'ConfirmOtpPage',
           'ProfilePage']
