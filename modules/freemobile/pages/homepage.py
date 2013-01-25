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
        for divglobal in self.document.xpath('//div[@class="abonne"]'):
            for link in divglobal.xpath('.//div[@class="acceuil_btn"]/a'):
                login = link.attrib['href'].split('=').pop()
                if login.isdigit():
                    break
            divabo = divglobal.xpath('div[@class="idAbonne pointer"]')[0]
            owner = unicode(divabo.xpath('p')[0].text.replace(' - ', ''))
            phone = unicode(divabo.xpath('p/span')[0].text)
            self.browser.logger.debug('Found ' + login + ' as subscription identifier')
            self.browser.logger.debug('Found ' + owner + ' as subscriber')
            self.browser.logger.debug('Found ' + phone + ' as phone number')
            phoneplan = unicode(self.document.xpath('//div[@class="forfaitChoisi"]')[0].text.lstrip().rstrip())
            self.browser.logger.debug('Found ' + phoneplan + ' as subscription type')

            subscription = Subscription(phone)
            subscription.label = phone + ' - ' + phoneplan
            subscription.subscriber = owner
            subscription._login = login

            yield subscription
