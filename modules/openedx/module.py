# -*- coding: utf-8 -*-

# Copyright(C) 2016      Simon Lipp
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import dateutil.parser

from subprocess import Popen, PIPE

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.messages import CapMessages, Thread, Message

from .browser import OpenEDXBrowser

__all__ = ['OpenEDXModule']

class OpenEDXModule(Module, CapMessages):
    NAME = 'openedx'
    DESCRIPTION = u'Discussions on OpenEDX-powered coursewares'
    MAINTAINER = u'Simon Lipp'
    EMAIL = 'laiquo@hwold.net'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    CONFIG = BackendConfig(Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('url',                     label='Site URL', default='https://courses.edx.org/'),
                           Value('course',                  label='Course ID', default='edX/DemoX.1/2014'))

    BROWSER = OpenEDXBrowser

    STORAGE = {'seen': {}}

    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)

        def pandoc_formatter(text):
            return Popen(["pandoc", "-f", "markdown", "-t", "html", "--mathml", "-"],
                    stdin=PIPE, stdout=PIPE).communicate(text.encode('utf-8'))[0].decode('utf-8')

        try:
            from markdown import Markdown
        except ImportError:
            Markdown = None

        self.default_flags = Message.IS_HTML
        try:
            Popen(["pandoc", "-v"], stdout=PIPE, stderr=PIPE).communicate()
            self.formatter = pandoc_formatter
        except OSError:
            if Markdown:
                self.formatter = Markdown().convert
            else:
                self.formatter = (lambda text: text)
                self.default_flags = 0

    def create_default_browser(self):
        return self.create_browser(self.config['url'].get(), self.config['course'].get(),
                self.config['username'].get(), self.config['password'].get())

    def _build_thread(self, data):
        thread = Thread("%s.%s" % (data["commentable_id"], data["id"]))
        thread.title = data["title"]
        thread.date = dateutil.parser.parse(data["created_at"])
        thread.url = self.browser.thread.build(course=self.browser.course, topic=data["commentable_id"], id=data["id"])
        thread.root = self._build_message(data, thread)
        thread._messages_count = data["comments_count"] + 1
        return thread

    def _build_message(self, data, thread, parent = None):
        flags = self.default_flags
        if data["id"] not in self.storage.get("seen", thread.id, default=[]):
            flags |= Message.IS_UNREAD

        message = Message(thread = thread,
                id = data["id"],
                title = (parent and "Re: %s" or "%s") % thread.title,
                sender = data.get("username"),
                receivers = None,
                date = dateutil.parser.parse(data["created_at"]),
                content = self.formatter(data["body"]),
                flags = flags,
                parent = parent,
                url = thread.url)
        self._append_children(data, message, thread)
        return message

    def _append_children(self, data, message, thread):
        if "endorsed_responses" in data or "children" in data or "non_endorsed_responses" in data:
            message.children = []
            for child in data.get("endorsed_responses", []) + data.get("children", []) + data.get('non_endorsed_responses', []):
                message.children.append(self._build_message(child, thread, message))

    def fill_message(self, message, fields):
        # The only unfilled messages are the root messages of threads returned
        # by iter_threads(). Only `children` in unfilled.

        if 'children' in fields and message.thread.root.id == message.id:
            message.children = self.get_thread(message.id).root.children

        return message

    #### CapMessages ##############################################

    def get_thread(self, id):
        topic, id = id.rsplit(".", 1)
        thread = None
        skip = 0

        while True:
            data = self.browser.get_thread(topic, id, skip).doc["content"]
            if thread is None:
                thread = self._build_thread(data)
            else:
                self._append_children(data, thread.root, thread)

            if data["resp_skip"] + data["resp_limit"] >= data["resp_total"]:
                return thread
            else:
                skip += 100

    def iter_threads(self):
        page = 1
        while True:
            tlist = self.browser.get_threads(page).doc
            for data in tlist["discussion_data"]:
                yield self._build_thread(data)

            if tlist["page"] < tlist["num_pages"]:
                page += 1
            else:
                break

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            if thread._messages_count > len(self.storage.get('seen', thread.id, default=[])):
                thread = self.get_thread(thread.id)
                for m in thread.iter_all_messages():
                    if m.flags & m.IS_UNREAD:
                        yield m

    def set_message_read(self, message):
        thread_seen = self.storage.get('seen', message.thread.id, default=[])
        thread_seen.append(message.id)
        self.storage.set('seen', message.thread.id, thread_seen)
        self.storage.save()

    OBJECTS = {Message: fill_message}
