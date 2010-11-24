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
from weboob.capabilities.messages import CantSendMessage, ICapMessages, Message
from weboob.capabilities.account import ICapAccount
from weboob.tools.application.repl import ReplApplication
from weboob.tools.misc import html2text


__all__ = ['Boobmsg']


class Boobmsg(ReplApplication):
    APPNAME = 'boobmsg'
    VERSION = '0.4'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz'
    CAPS = ICapMessages

    def add_application_options(self, group):
        group.add_option('-e', '--skip-empty', action='store_true', help='Don\'t send messages with an empty body.')

    def do_status(self, line):
        """
        status

        Display status information about a backend.
        """
        if len(line) > 0:
            backend_name = line
        else:
            backend_name = None

        results = {}
        for backend, field in self.do('get_account_status', backends=backend_name, caps=ICapAccount):
            if backend.name in results:
                results[backend.name].append(field)
            else:
                results[backend.name] = [field]

        for name, fields in results.iteritems():
            print ':: %s ::' % name
            for f in fields:
                if f.flags & f.FIELD_HTML:
                    value = html2text(f.value)
                else:
                    value = f.value
                print '%s: %s' % (f.label, value)
            print ''

    def do_post(self, line):
        """
        post TO...

        Post a message to the specified receivers.
        Multiple receivers are separated by a comma.
        The content of message is read on stdin.
        """
        def post_message(receivers, backends=None):
            message = Message(thread=None, id=None, content=content, receivers=receivers)
            try:
                self.do('post_message', message, backends=backends).wait()
            except CallErrors, errors:
                for backend, error, backtrace in errors:
                    if isinstance(error, CantSendMessage):
                        print >>sys.stderr, 'Error: %s' % error
                        self.logger.debug(backtrace)
                    else:
                        self.bcall_error_handler(backend, error, backtrace)
            if self.interactive:
                print 'Message sent sucessfully to %s' % ','.join(receivers)

        if not line:
            print >>sys.stderr, 'You must give at least a receiver.'
            return
        receivers_by_backend = {}
        receivers_without_backend = []
        for receiver in [receiver.strip() for receiver in line.strip().split(',')]:
            receiver, backend_name = self.parse_id(receiver)
            if backend_name:
                if backend_name in receivers_by_backend:
                    receivers_by_backend[backend_name].append(receiver)
                else:
                    receivers_by_backend[backend_name] = [receiver]
            else:
                receivers_without_backend.append(receiver)
        if self.interactive:
            print 'Reading message content from stdin... Type ctrl-D from an empty line to post message.'
        content = sys.stdin.read()
        if self.options.skip_empty and not content.strip():
            return
        for backend_name, receivers in receivers_by_backend.iteritems():
            post_message(receivers, [backend_name])
        post_message(receivers_without_backend)
