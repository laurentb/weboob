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


from datetime import datetime

from .base import IBaseCap, CapBaseObject


__all__ = ['Account', 'AccountNotFound', 'NotEnoughMoney', 'ICapBank', 'Operation']


class AccountNotFound(Exception):
    pass

class NotEnoughMoney(Exception):
    pass


class Account(CapBaseObject):
    def __init__(self):
        CapBaseObject.__init__(self, 0)
        self.add_field('label', basestring)
        self.add_field('balance', float)
        self.add_field('coming', float)
        self.add_field('link_id', basestring)

    def __repr__(self):
        return u"<Account id='%s' label='%s'>" % (self.id, self.label)


class Operation(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('date', (basestring,datetime))
        self.add_field('label', unicode)
        self.add_field('amount', float)

    def __repr__(self):
        return "<Operation date='%s' label='%s' amount=%s>" % (self.date, self.label, self.amount)

class ICapBank(IBaseCap):
    def iter_accounts(self):
        raise NotImplementedError()

    def get_account(self, _id):
        raise NotImplementedError()

    def iter_operations(self, account):
        raise NotImplementedError()

    def iter_history(self, id):
        raise NotImplementedError()

    def transfer(self, id_from, id_to, amount):
		raise NotImplementedError()
