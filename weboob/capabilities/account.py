# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from .base import IBaseCap, CapBaseObject


__all__ = ['ICapAccount']


class AccountRegisterError(Exception):
    pass

class Account(CapBaseObject):
    def __init__(self, id=None):
        CapBaseObject.__init__(self, id)
        self.add_field('login', basestring)
        self.add_field('password', basestring)
        self.add_field('properties', dict)

class ICapAccount(IBaseCap):
    ACCOUNT_REGISTER_PROPERTIES = []

    @staticmethod
    def register_account(account):
        """
        Register an account on website

        This is a static method, it would be called even if the backend is
        instancied.

        @param account  an Account object which describe the account to create
        """
        raise NotImplementedError()

    def get_account(self):
        """
        Get the current account.
        """
        raise NotImplementedError()

    def update_account(self, account):
        """
        Update the current account.
        """
        raise NotImplementedError()
