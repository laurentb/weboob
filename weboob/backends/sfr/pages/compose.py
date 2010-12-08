# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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
from weboob.tools.parsers.lxmlparser import select


__all__ = ['ClosePage', 'ComposePage', 'ConfirmPage', 'SentPage']


class ClosePage(BasePage):
    pass


class ComposePage(BasePage):
    phone_regex = re.compile('^(\+33|0033|0)(6|7)(\d{8})$')

    def get_nb_remaining_free_sms(self):
        remaining_regex = re.compile(u'Il vous reste (?P<nb>.+) Texto gratuits vers les numéros SFR à envoyer aujourd\'hui')
        text = select(self.document.getroot(), '#smsReminder', 1).text.strip()
        return remaining_regex.match(text).groupdict().get('nb')

    def post_message(self, message):
        receiver = message.thread.id
        if self.phone_regex.match(receiver) is None:
            raise CantSendMessage(u'Invalid receiver: %s' % receiver)
        self.browser.select_form(nr=0)
        self.browser['msisdns'] = receiver
        self.browser['textMessage'] = message.content
        self.browser.submit()


class ConfirmPage(BasePage):
    def confirm(self):
        self.browser.select_form(nr=0)
        self.browser.submit()


class SentPage(BasePage):
    pass
