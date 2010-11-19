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


import sys

from weboob.core import CallErrors
from weboob.capabilities.messages import CantSendMessage, ICapMessagesPost, Message
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Boobmsg']


class Boobmsg(ReplApplication):
    APPNAME = 'boobmsg'
    VERSION = '0.4'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz'
    CAPS = ICapMessagesPost

    def do_post(self, line):
        """
        post TO

        Post a message to the specified receiver.
        The receiver can have multiple comma-separated values.
        The content of message is read on stdin.
        """
        if not line:
            print >>sys.stderr, 'You must give a receiver.'
            return
        receiver, backend_name = self.parse_id(line.strip())
        names = (backend_name,) if backend_name is not None else None
        if self.interactive:
            print 'Reading message content from stdin... Type ctrl-D from an empty line to post message.'
        content = sys.stdin.read()
        message = Message(thread=None, id=None, content=content, receiver=receiver)
        try:
            self.do('post_message', message, backends=names).wait()
        except CallErrors, errors:
            for backend, error, backtrace in errors:
                if isinstance(error, CantSendMessage):
                    print >>sys.stderr, 'Error: %s' % error
                else:
                    self.bcall_error_handler(backend, error, backtrace)
        if self.interactive:
            print 'Message sucessfully sent.'
