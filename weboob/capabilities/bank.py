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


import sys
if sys.version_info[:2] <= (2, 5):
    import weboob.tools.property


from .cap import ICap


__all__ = ['Account', 'AccountNotFound', 'ICapBank', 'Operation']


class AccountNotFound(Exception):
    pass


class Account(object):
    def __init__(self):
        self.id = 0
        self.label = ''
        self._balance = 0.0
        self._coming = 0.0
        self.link_id = ''

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        self._balance = float(value)

    @property
    def coming(self):
        return self._coming

    @coming.setter
    def coming(self, value):
        self._coming = float(value)

    def __repr__(self):
        return u"<Account id='%s' label='%s'>" % (self.id, self.label)


class Operation(object):
    def __init__(self):
        self.date = None
        self._label = u''
        self._amount = 0.0

    def __repr__(self):
        return "<Operation date='%s' label='%s' amount=%s>" % (self.date, self.label, self.amount)

    @property
    def label(self):
        return self._label

    @label.setter
    def label_set(self, value):
        self._label = str(value)

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount_set(self, value):
        self._amount = float(value)


class ICapBank(ICap):
    def iter_accounts(self):
        raise NotImplementedError()

    def get_account(self, _id):
        raise NotImplementedError()

    def iter_operations(self, account):
        raise NotImplementedError()
