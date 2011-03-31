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


import logging

from weboob.tools.application.repl import ReplApplication
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.contact import ICapContact, Contact


__all__ = ['Chatoob']


class Chatoob(ReplApplication):
    APPNAME = 'chatoob'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz'
    DESCRIPTION = 'Console application allowing to chat with contacts on various websites.'
    CAPS = ICapChat

    def on_new_chat_message(self, message):
        print 'on_new_chat_message: %s' % message

    def do_list(self, line):
        """
        list

        List all contacts.
        """
        for backend, contact in self.do('iter_contacts', status=Contact.STATUS_ONLINE, caps=ICapContact):
            self.format(contact)
        self.flush()

    def do_messages(self, line):
        """
        messages

        Get messages.
        """
        for backend, message in self.do('iter_chat_messages'):
            self.format(message)
        self.flush()

    def do_send(self, line):
        """
        send CONTACT MESSAGE

        Send a message to the specified contact.
        """
        _id, message = self.parse_command_args(line, 2, 2)
        for backend, result in self.do('send_chat_message', _id, message):
            if not result:
                logging.error(u'Failed to send message to contact id="%s" on backend "%s"' % (_id, backend.name))
