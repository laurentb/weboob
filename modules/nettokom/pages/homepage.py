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
from weboob.tools.browser import BasePage


__all__ = ['HomePage']


class HomePage(BasePage):
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
        self.browser.logger.debug('Found ' + owner + ' has subscriber')
        self.browser.logger.debug('Found ' + phone + ' has phone number')
        self.browser.logger.debug('Found ' + credit + ' has available credit')
        self.browser.logger.debug('Found ' + expiredate + 'has expire date ')
        self.browser.logger.debug('Found ' + phoneplan + ' has subscription type')

        subscription = Subscription(phone)
        subscription.label = unicode(phone + u' - ' + credit + u' - ' + expiredate + u' - ' + phoneplan)
        subscription.owner = owner

        l.append(subscription)

        return l
