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
from weboob.deprecated.browser import Page


class HomePage(Page):
    def on_loaded(self):
        pass

    def get_list(self):
        l = []
        phone = unicode(self.document.xpath('//span[@id="ctl00_ctl00_cMain_cEspCli_lblMsIsdn"]')[0].text.replace(' ', ''))
        self.browser.logger.debug('Found ' + phone + ' has phone number')
        phoneplan = unicode(self.document.xpath('//span[@id="ctl00_ctl00_cMain_cEspCli_aoaOffreActuelle_aooOffreEtOptions"]/dl/dd/span')[0].text)
        self.browser.logger.debug('Found ' + phoneplan + ' has subscription type')

        subscription = Subscription(phone)
        subscription.label = phone + ' - ' + phoneplan

        l.append(subscription)

        return l
