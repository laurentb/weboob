# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon, Florent Fourcot
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


from .base import BaseObject, StringField, DecimalField, UserError
from .date import DateField
from .collection import CapCollection


__all__ = ['SubscriptionNotFound', 'BillNotFound', 'Detail', 'Bill', 'Subscription', 'CapBill']


class SubscriptionNotFound(UserError):
    """
    Raised when a subscription is not found.
    """

    def __init__(self, msg='Subscription not found'):
        UserError.__init__(self, msg)


class BillNotFound(UserError):
    """
    Raised when a bill is not found.
    """

    def __init__(self, msg='Bill not found'):
        UserError.__init__(self, msg)


class Detail(BaseObject):
    """
    Detail of a subscription
    """
    label =     StringField('label of the detail line')
    infos =     StringField('information')
    datetime =  DateField('date information')
    price =     DecimalField('Total price, taxes included')
    vat =       DecimalField('Value added Tax')
    currency =  StringField('Currency', default=None)
    quantity =  DecimalField('Number of units consumed')
    unit =      StringField('Unit of the consumption')

    def __init__(self):
        BaseObject.__init__(self, 0)


class Bill(BaseObject):
    """
    Bill.
    """
    date =          DateField('The day the bill has been sent to the subscriber')
    format =        StringField('file format of the bill')
    label =         StringField('label of bill')
    idparent =      StringField('id of the parent subscription')
    price =         DecimalField('Price to pay')
    currency =      StringField('Currency', default=None)
    deadline =      DateField('The latest day to pay')
    startdate =     DateField('The first day the bill applies to')
    finishdate =    DateField('The last day the bill applies to')

    def __init__(self):
        BaseObject.__init__(self, 0)


class Subscription(BaseObject):
    """
    Subscription to a service.
    """
    label =         StringField('label of subscription')
    subscriber =    StringField('whe has subscribed')
    validity =      DateField('End validity date of the subscription')
    renewdate =     DateField('Reset date of consumption')


class CapBill(CapCollection):
    def iter_resources(self, objs, split_path):
        """
        Iter resources. Will return :func:`iter_subscriptions`.
        """
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

    def iter_subscription(self):
        """
        Iter subscriptions.

        :rtype: iter[:class:`Subscription`]
        """
        raise NotImplementedError()

    def get_subscription(self, _id):
        """
        Get a subscription.

        :param _id: ID of subscription
        :rtype: :class:`Subscription`
        :raises: :class:`SubscriptionNotFound`
        """
        raise NotImplementedError()

    def iter_bills_history(self, subscription):
        """
        Iter history of a subscription.

        :param subscription: subscription to get history
        :type subscription: :class:`Subscription`
        :rtype: iter[:class:`Detail`]
        """
        raise NotImplementedError()

    def get_bill(self, id):
        """
        Get a bill.

        :param id: ID of bill
        :rtype: :class:`Bill`
        :raises: :class:`BillNotFound`
        """
        raise NotImplementedError()

    def download_bill(self, id):
        """
        Download a bill.

        :param id: ID of bill
        :rtype: str
        :raises: :class:`BillNotFound`
        """
        raise NotImplementedError()

    def iter_bills(self, subscription):
        """
        Iter bills.

        :param subscription: subscription to get bills
        :type subscription: :class:`Subscription`
        :rtype: iter[:class:`Bill`]
        """
        raise NotImplementedError()

    def get_details(self, subscription):
        """
        Get details of a subscription.

        :param subscription: subscription to get details
        :type subscription: :class:`Subscription`
        :rtype: iter[:class:`Detail`]
        """
        raise NotImplementedError()

    def get_balance(self, subscription):
        """
        Get the balance of a subscription.

        :param subscription: subscription to get balance
        :type subscription: :class:`Subscription`
        :rtype: class:`Detail`
        """
        raise NotImplementedError()
