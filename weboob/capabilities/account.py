# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

class StatusField(object):
    FIELD_TEXT    = 0x001     # the value is a long text
    FIELD_HTML    = 0x002     # the value is HTML formated

    def __init__(self, key, label, value, flags=0):
        self.key = key
        self.label = label
        self.value = value
        self.flags = flags


class ICapAccount(IBaseCap):
    # This class constant may be a list of Value* objects. If the value remains
    # None, weboob considers that register_account() isn't supported.
    ACCOUNT_REGISTER_PROPERTIES = None

    @staticmethod
    def register_account(account):
        """
        Register an account on website

        This is a static method, it would be called even if the backend is
        instancied.

        @param account  an Account object which describe the account to create
        """
        raise NotImplementedError()

    def confirm_account(self, mail):
        """
        From an email go to the confirm link.
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

    def get_account_status(self):
        """
        Get status of the current account.

        @return a list of fields
        """
        raise NotImplementedError()
