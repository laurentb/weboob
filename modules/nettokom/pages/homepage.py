# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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

from weboob.capabilities.bill import Subscription
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.deprecated.browser import Page
from datetime import date
from decimal import Decimal


class HomePage(Page):
    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        divabo = self.document.xpath('//div[@id="accountSummary"]')[0]
        owner = divabo.xpath('a/h3')[0].text
        phone = divabo.xpath('dl/dd')[0].text
        credit = divabo.xpath('dl/dd')[1].text
        expiredate = divabo.xpath('dl/dd')[2].text
        phoneplan = divabo.xpath('dl/dd')[3].text
        self.browser.logger.debug('Found ' + owner + ' as subscriber')
        self.browser.logger.debug('Found ' + phone + ' as phone number')
        self.browser.logger.debug('Found ' + credit + ' as available credit')
        self.browser.logger.debug('Found ' + expiredate + ' as expire date ')
        self.browser.logger.debug('Found %s as subscription type', phoneplan)

        subscription = Subscription(phone)
        subscription.label = unicode(u'%s - %s - %s - %s' %
                (phone, credit, phoneplan, expiredate))
        subscription.subscriber = unicode(owner)
        expiredate = date(*reversed([int(x) for x in expiredate.split(".")]))
        subscription.validity = expiredate
        subscription._balance = Decimal(FrenchTransaction.clean_amount(credit))

        l.append(subscription)

        return l
