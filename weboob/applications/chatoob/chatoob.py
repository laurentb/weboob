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

from weboob.tools.application import ConsoleApplication
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.contact import ICapContact, Contact


__all__ = ['Chatoob']


class Chatoob(ConsoleApplication):
    APPNAME = 'chatoob'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz'

    def main(self, argv):
        self.load_backends(ICapChat)
        #for backend, result in self.weboob.do('start_chat_polling', self.on_new_chat_message):
            #logging.info(u'Polling chat messages for backend %s' % backend)
        return self.process_command(*argv[1:])

    def on_new_chat_message(self, message):
        print 'on_new_chat_message: %s' % message

    @ConsoleApplication.command('exit program')
    def command_exit(self):
        self.weboob.want_stop()

    @ConsoleApplication.command('list online contacts')
    def command_list(self):
        for backend, contact in self.weboob.do_caps(ICapContact, 'iter_contacts', status=Contact.STATUS_ONLINE):
            self.format(contact, backend.name)

    @ConsoleApplication.command('get messages')
    def command_messages(self):
        for backend, message in self.weboob.do('iter_chat_messages'):
            self.format(message, backend.name)

    @ConsoleApplication.command('send message to contact')
    def command_send(self, _id, message):
        for backend, result in self.weboob.do('send_chat_message', _id, message):
            if not result:
                logging.error(u'Failed to send message to contact id="%s" on backend "%s"' % (_id, backend.name))
