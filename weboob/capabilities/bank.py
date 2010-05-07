# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from .cap import ICap

class AccountNotFound(Exception): pass

class Account(object):
    def __init__(self):
        self.id = 0
        self.label = ''
        self.balance = 0.0
        self.coming = 0.0
        self.link_id = ''

    def setID(self, id):
        assert isinstance(id, (int,long))
        self.id = id

    def setLabel(self, label): self.label = label

    def setBalance(self, balance):
        assert isinstance(balance, float)
        self.balance = balance

    def setComing(self, coming):
        assert isinstance(coming, float)
        self.coming = coming

    def setLinkID(self, link):
        self.link_id = link

    def __repr__(self):
        return u"<Account id='%s' label='%s'>" % (self.id, self.label)


class Operation(object):
    def __init__(self):
        self.date = None
        self.label = u''
        self.amount = 0.0

    def __repr__(self):
        return "<Operation date='%s' label='%s' amount=%s>" % (self.date, self.label, self.amount)

    def setDate(self, date):
        #assert isinstance(date, datetime.datetime)
        self.date = date

    def setLabel(self, label):
        self.label = str(label)

    def setAmount(self, amount):
        assert isinstance(amount, float)
        self.amount = amount


class ICapBank(ICap):
    def iter_accounts(self):
        raise NotImplementedError()

    def get_account(self, _id):
        raise NotImplementedError()

    def iter_operations(self, account):
        raise NotImplementedError()
