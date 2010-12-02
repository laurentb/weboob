# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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

import re

from weboob.capabilities.messages import CantSendMessage
from weboob.tools.browser import BasePage

__all__ = ['ComposePage', 'ConfirmPage']

class ConfirmPage(BasePage):
    def on_loaded(self):
        pass


class ComposePage(BasePage):
    phone_regex = re.compile('^(\+33|0033|0)(6|7)(\d{8})$')

    def on_loaded(self):
        #Deal with bad encoding... for ie6 ...
        response = self.browser.response()
        response.set_data(response.get_data().decode('utf-8', 'ignore') )
        self.browser.set_response(response)

    def get_nb_remaining_free_sms(self):
        return "0"

    def post_message(self, message, sender):
        receiver_list = [re.sub(' +', '', receiver) for receiver in message.receivers]
        for receiver in receiver_list:
            if self.phone_regex.match(receiver) is None:
                raise CantSendMessage(u'Invalid receiver: %s' % receiver)

        listetel = ",,"+ "|,,".join(receiver_list)

        #Fill the form
        self.browser.select_form(name="formulaire")
        self.browser.new_control("hidden", "autorize",{'value':''})
        self.browser.new_control("textarea", "msg", {'value':''})

        self.browser.set_all_readonly(False)

        self.browser["corpsms"] = message.content
        self.browser["pays"] = "33"
        self.browser["listetel"] = listetel
        self.browser["reply"] = "2"
        self.browser["typesms"] = "2"
        self.browser["produit"] = "1000"
        self.browser["destToKeep"] = listetel
        self.browser["NUMTEL"] = sender
        self.browser["autorize"] = "1"
        self.browser["msg"] = message.content
        self.browser.submit()
