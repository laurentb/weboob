# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Florent Fourcot
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from .accounts_list import (
    AccountsList, TitreDetails, ASVInvest, DetailFondsPage, IbanPage,
    ProfilePage, LoanTokenPage, LoanDetailPage,
)
from .login import LoginPage, StopPage, ActionNeededPage, ReturnPage
from .transfer import TransferPage
from .bills import BillsPage
from .titre import NetissimaPage, TitrePage, TitreHistory, TitreValuePage, ASVHistory


class AccountPrelevement(AccountsList):
    pass


__all__ = ['AccountsList', 'LoginPage', 'NetissimaPage','TitreDetails',
           'AccountPrelevement', 'TransferPage',
           'BillsPage', 'StopPage', 'TitrePage', 'TitreHistory', 'IbanPage',
           'TitreValuePage', 'ASVHistory', 'ASVInvest','DetailFondsPage',
           'ActionNeededPage', 'ReturnPage', 'ProfilePage', 'LoanTokenPage',
           'LoanDetailPage']
