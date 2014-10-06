# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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

import re

from weboob.capabilities.messages import CantSendMessage
from weboob.deprecated.browser import Page


class ConfirmPage(Page):
    def on_loaded(self):
        pass


class ComposePage(Page):
    phone_regex = re.compile('^(\+33|0033|0)(6|7)(\d{8})$')

    def on_loaded(self):
        # Deal with bad encoding... for ie6...
        response = self.browser.response()
        response.set_data(response.get_data().decode('utf-8', 'ignore'))
        self.browser.set_response(response)

    def get_nb_remaining_free_sms(self):
        return "0"

    def post_message(self, message, sender):
        receiver = message.thread.id
        if self.phone_regex.match(receiver) is None:
            raise CantSendMessage(u'Invalid receiver: %s' % receiver)

        listetel = ",," + receiver

        #Fill the form
        self.browser.select_form(name="formulaire")
        self.browser.new_control("hidden", "autorize", {'value': ''})

        self.browser.set_all_readonly(False)

        self.browser["corpsms"] = message.content.encode('utf-8')
        self.browser["pays"] = "33"
        self.browser["listetel"] = listetel
        self.browser["reply"] = "2"
        self.browser["typesms"] = "2"
        self.browser["produit"] = "1000"
        self.browser["destToKeep"] = listetel
        self.browser["NUMTEL"] = sender
        self.browser["autorize"] = "1"
        self.browser["msg"] = message.content.encode('utf-8')
        self.browser.submit()
