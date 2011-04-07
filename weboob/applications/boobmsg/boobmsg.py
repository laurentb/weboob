# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Christophe Benz
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


import sys

from weboob.core import CallErrors
from weboob.capabilities.messages import ICapMessages, Message, Thread
from weboob.capabilities.account import ICapAccount
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter
from weboob.tools.misc import html2text

__all__ = ['Boobmsg']


class XHtmlFormatter(IFormatter):
    def flush(self):
        pass

    def format_dict(self, item):
        result  = "<div>\n"
        result += "<h1>%s</h1>" % (item['title'])
        result += "<dl>"
        result += "<dt>Date</dt><dd>%s</dd>" % (item['date'])
        result += "<dt>Sender</dt><dd>%s</dd>" % (item['sender'])
        result += "<dt>Signature</dt><dd>%s</dd>" % (item['signature'])
        result += "</dl>"
        result += "<div>%s</div>" % (item['content'])
        result += "</div>\n"
        return result


class MessageFormatter(IFormatter):
    def flush(self):
        pass

    def format_dict(self, item):
        result = u'%sTitle:%s %s\n' % (self.BOLD,
                                       self.NC, item['title'])
        result += u'%sDate:%s %s\n' % (self.BOLD,
                                       self.NC, item['date'])
        result += u'%sFrom:%s %s\n' % (self.BOLD,
                                       self.NC, item['sender'])
        if item['receivers']:
            result += u'%sTo:%s %s\n' % (self.BOLD,
                                         self.NC,
                                         ', '.join(item['receivers']))

        if item['flags'] & Message.IS_HTML:
            content = html2text(item['content'])
        else:
            content = item['content']

        result += '\n%s' % content
        return result


class MessagesListFormatter(IFormatter):
    MANDATORY_FIELDS = ()
    count = 0
    _list_messages = False

    def flush(self):
        self.count = 0

    def format_dict(self, item):
        if not self._list_messages:
            return self.format_dict_thread(item)
        else:
            return self.format_dict_messages(item)

    def format_dict_thread(self, item):
        self.count += 1
        if item['nb_unread'] and item['nb_unread'] > 0:
            unread = '[N]'
        else:
            unread = '   '
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s %s (%s)%s' % (self.BOLD,
                                                 self.count, unread,
                                                 item['title'], backend,
                                                 self.NC)
        else:
            result = u'%s* (%s) %s %s%s' % (self.BOLD, item['id'],
                                            unread, item['title'],
                                            self.NC)
        if item['date']:
            result += u'\n             %s' % item['date']
        return result

    def format_dict_messages(self, item):
        backend = item['id'].split('@', 1)[1]
        if item['flags'] == Thread.IS_THREADS:
            depth = 0
        else:
            depth = -1

        result = self.format_message(backend, item['root'], depth)
        return result

    def format_message(self, backend, message, depth=0):
        if not message:
            return u''
        self.count += 1

        flags = '['
        if message.flags & message.IS_UNREAD:
            flags += 'N'
        else:
            flags += '-'
        if message.flags & message.IS_NOT_ACCUSED:
            flags += 'U'
        elif message.flags & message.IS_ACCUSED:
            flags += 'R'
        else:
            flags += '-'
        flags += ']'

        if self.interactive:
            result = u'%s%s* (%d)%s %s <%s> %s (%s)\n' % (depth * '  ',
                                                          self.BOLD,
                                                          self.count,
                                                          self.NC,
                                                          flags,
                                                          message.sender,
                                                          message.title,
                                                          backend)
        else:
            result = u'%s%s* (%s.%s@%s)%s %s <%s> %s\n' % (depth * '  ',
                                                           self.BOLD,
                                                           message.thread.id,
                                                           message.id,
                                                           backend,
                                                           flags,
                                                           self.NC,
                                                           message.sender,
                                                           message.title)
        if message.children:
            if depth >= 0:
                depth += 1
            for m in message.children:
                result += self.format_message(backend, m, depth)
        return result


class Boobmsg(ReplApplication):
    APPNAME = 'boobmsg'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Christophe Benz'
    DESCRIPTION = "Console application allowing to send messages on various websites and " \
                  "to display message threads and contents."
    CAPS = ICapMessages
    EXTRA_FORMATTERS = {'msglist': MessagesListFormatter,
                        'msg':     MessageFormatter,
                        'xhtml':     XHtmlFormatter,
                       }
    COMMANDS_FORMATTERS = {'list':      'msglist',
                           'show':      'msg',
                           'export_thread': 'msg',
                           'export_all': 'msg'
                          }


    def add_application_options(self, group):
        group.add_option('-e', '--skip-empty',  action='store_true',
                         help='Don\'t send messages with an empty body.')
        group.add_option('-t', '--title', action='store',
                         help='For the "post" command, set a title to message',
                         type='string', dest='title')

    def load_default_backends(self):
        self.load_backends(ICapMessages, storage=self.create_storage())

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
        for backend, field in self.do('get_account_status',
                                      backends=backend_name,
                                      caps=ICapAccount):
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
        post RECEIVER@BACKEND[,RECEIVER@BACKEND[...]] [TEXT]

        Post a message to the specified receivers.
        Multiple receivers are separated by a comma.

        If no text is supplied on command line, the content of message is read on stdin.
        """
        receivers, text = self.parse_command_args(line, 2, 1)
        if text is None:
            if self.interactive:
                print 'Reading message content from stdin... Type ctrl-D ' \
                      'from an empty line to post message.'
            text = sys.stdin.read()
            if sys.stdin.encoding:
                text = text.decode(sys.stdin.encoding)

        if self.options.skip_empty and not text.strip():
            return

        for receiver in receivers.strip().split(','):
            receiver, backend_name = self.parse_id(receiver.strip(),
                                                   unique_backend=True)
            if not backend_name and len(self.enabled_backends) > 1:
                self.logger.warning(u'No backend specified for receiver "%s": message will be sent with all the '
                    'enabled backends (%s)' % (receiver,
                    ','.join(backend.name for backend in self.enabled_backends)))

            if '.' in receiver:
                # It's a reply
                thread_id, parent_id = receiver.rsplit('.', 1)
            else:
                # It's an original message
                thread_id = receiver
                parent_id = None


            thread = Thread(thread_id)
            message = Message(thread,
                              0,
                              title=self.options.title,
                              parent=Message(thread, parent_id) if parent_id else None,
                              content=text)

            try:
                self.do('post_message', message, backends=backend_name).wait()
            except CallErrors, errors:
                self.bcall_errors_handler(errors)
            else:
                if self.interactive:
                    print 'Message sent sucessfully to %s' % receiver

    threads = []
    messages = []

    def do_list(self, arg):
        """
        list

        Display all threads.
        """
        if len(arg) > 0:
            try:
                thread = self.threads[int(arg) - 1]
            except (IndexError, ValueError):
                id, backend_name = self.parse_id(arg)
            else:
                id = thread.id
                backend_name = thread.backend

            self.messages = []
            cmd = self.do('get_thread', id, backends=backend_name)
            self.formatter._list_messages = True
        else:
            self.threads = []
            cmd = self.do('iter_threads')
            self.formatter._list_messages = False

        for backend, thread in cmd:
            if len(arg) > 0:
                for m in thread.iter_all_messages():
                    if not m.backend:
                        m.backend = thread.backend
                    self.messages.append(m)
            else:
                self.threads.append(thread)
            self.format(thread)
        self.flush()

    def do_export_all(self, arg):
        """
        export_all

        Export All threads
        """

        cmd = self.do('iter_threads')
        for backend, thread in cmd:
            t  = backend.get_thread(thread.id)
            for msg in t.iter_all_messages():
                self.format(msg)

    def do_export_thread(self, arg):
        """
        export_thread

        Export a thread
        """
        _id, backend_name = self.parse_id(arg)
        cmd = self.do('get_thread', _id, backends=backend_name)
        for backend, thread in cmd:
            if thread is not None :
                for msg in thread.iter_all_messages():
                    self.format(msg)

    def do_show(self, arg):
        """
        show MESSAGE

        Read a message
        """
        if len(arg) == 0:
            print 'Please give a message ID.'
            return

        try:
            message = self.messages[int(arg) - 1]
        except (IndexError, ValueError):
            id, backend_name = self.parse_id(arg)
        else:
            self.format(message)
            self.weboob.do('set_message_read', message, backends=message.backend)
            return

        if not self.interactive:
            print 'Oops, you need to be in interactive mode to read messages'
        else:
            print 'Message not found'
