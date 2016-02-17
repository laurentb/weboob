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


from .accounts_list import AccountsList, TitreDetails
from .login import LoginPage, StopPage
from .transfer import TransferPage, TransferConfirmPage
from .bills import BillsPage
from .titre import NetissimaPage, TitrePage, TitreHistory, TitreValuePage, ASVHistory


class AccountPrelevement(AccountsList):
    pass

__all__ = ['AccountsList', 'LoginPage', 'NetissimaPage','TitreDetails',
           'AccountPrelevement', 'TransferPage', 'TransferConfirmPage',
           'BillsPage', 'StopPage', 'TitrePage', 'TitreHistory',
           'TitreValuePage', 'ASVHistory']
