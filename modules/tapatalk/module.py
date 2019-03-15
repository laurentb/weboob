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
import datetime
import requests
import re
import xmlrpclib

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.messages import CapMessages, Thread, Message
from weboob.exceptions import BrowserIncorrectPassword

__all__ = ['TapatalkModule']

class TapatalkError(Exception):
    pass

class RequestsTransport(object):
    def __init__(self, uri):
        self._uri = uri
        self._session = requests.Session()

    def request(self, host, handler, request, verbose):
        response = self._session.post(self._uri, data = request,
                headers={"Content-Type": "text/xml; charset=UTF-8"})
        p, u = xmlrpclib.getparser()
        p.feed(response.content)
        p.close()
        response.close()
        return u.close()

class TapatalkServerProxy(xmlrpclib.ServerProxy):
    def __init__(self, uri):
        transport = RequestsTransport(uri)
        xmlrpclib.ServerProxy.__init__(self, uri, transport)

    def __getattr__(self, name):
        method = xmlrpclib.ServerProxy.__getattr__(self, name)
        return self._wrap(method)

    def _wrap(self, method):
        def call(*args, **kwargs):
            res = method(*args, **kwargs)
            if 'result' in res and not res['result']:
                raise TapatalkError(str(res.get('result_text')))
            return res
        return call

class TapatalkModule(Module, CapMessages):
    NAME = 'tapatalk'
    DESCRIPTION = u'Tapatalk-compatible sites'
    MAINTAINER = u'Simon Lipp'
    EMAIL = 'laiquo@hwold.net'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'

    CONFIG = BackendConfig(Value('username',                label='Username',  default=''),
                           ValueBackendPassword('password', label='Password',  default=''),
                           Value('url',                     label='Site URL', default="https://support.tapatalk.com/mobiquo/mobiquo.php"))

    def __init__(self, *args, **kwargs):
        super(TapatalkModule, self).__init__(*args, **kwargs)
        self._xmlrpc_client = None

    @property
    def _conn(self):
        if self._xmlrpc_client is None:
            url = self.config['url'].get().rstrip('/')
            username = self.config['username'].get()
            password = self.config['password'].get()
            self._xmlrpc_client = TapatalkServerProxy(url)
            try:
                self._xmlrpc_client.login(xmlrpclib.Binary(username), xmlrpclib.Binary(password))
            except TapatalkError as e:
                raise BrowserIncorrectPassword(e.message)
        return self._xmlrpc_client

    def _get_time(self, post):
        if 'post_time' in post:
            return dateutil.parser.parse(str(post['post_time']))
        else:
            return datetime.datetime.now()

    def _format_content(self, post):
        msg = unicode(str(post['post_content']), 'utf-8')
        msg = re.sub(r'\[url=(.+?)\](.*?)\[/url\]', r'<a href="\1">\2</a>', msg)
        msg = re.sub(r'\[quote\s?.*\](.*?)\[/quote\]', r'<blockquote><p>\1</p></blockquote>', msg)
        msg = re.sub(r'\[img\](.*?)\[/img\]', r'<img src="\1">', msg)
        if post.get('icon_url'):
            return u'<img style="float:right;position:relative" src="%s"> %s' % (post['icon_url'], msg)
        else:
            return msg

    def _process_post(self, thread, post, is_root):
        # Tapatalk app seems to have hardcoded this construction... I don't think we can do better :(
        url = u'%s/index.php?/topic/%s-%s#entry%s' % (
                self.config["url"].get().rstrip('/'),
                thread.id,
                re.sub(r'[^a-zA-Z0-9-]', '', re.sub(r'\s+', '-', thread.title)),
                post['post_id']
            )

        message = Message(
            id = is_root and "0" or str(post['post_id']),
            thread = thread,
            sender = unicode(str(post.get('post_author_name', 'Anonymous')), 'utf-8'),
            title = is_root and thread.title or u"Re: %s"%thread.title,
            url = url,
            receivers = None,
            date = self._get_time(post),
            content = self._format_content(post),#bbcode(),
            signature = None,
            parent = thread.root or None,
            children = [],
            flags = Message.IS_HTML)

        if thread.root:
            thread.root.children.append(message)
        elif is_root:
            thread.root = message
        else:
            # First message in the thread is not the root message,
            # because we asked only for unread messages. Create a non-loaded root
            # message to allow monboob to fill correctly the References: header
            thread.root = Message(id="0", parent=None, children=[message], thread=thread)
            message.parent = thread.root

        return message

    def fill_thread(self, thread, fields, unread=False):
        def fill_root(thread, start, count, first_unread):
            while True:
                topic = self._conn.get_thread(thread.id, start, start+count-1, True)
                for i, post in enumerate(topic['posts']):
                    message = self._process_post(thread, post, start*count+i == 0)
                    if start+i >= first_unread:
                        message.flags |= Message.IS_UNREAD

                start += count
                if start >= topic['total_post_num']:
                    return thread

        count = 50
        topic = self._conn.get_thread_by_unread(thread.id, count)
        if 'title' in fields:
            thread.title = unicode(str(topic['topic_title']), 'utf-8')
        if 'date' in fields:
            thread.date = self._get_time(topic)
        if 'root' in fields:
            # "position" starts at 1, whereas the "start" argument of get_thread starts at 0
            pos = topic['position']-1
            if unread:
                # start must be on a page boundary, or various (unpleasant) things will happen,
                # like get_threads returning nothing
                start = (pos//count)*count
                thread = fill_root(thread, start, count, pos)
            else:
                thread = fill_root(thread, 0, count, pos)

        return thread

    #### CapMessages ##############################################

    def get_thread(self, id):
        return self.fill_thread(Thread(id), ['title', 'root', 'date'])

    def iter_threads(self, unread=False):
        def browse_forum_mode(forum, prefix, mode):
            start = 0
            count = 50
            while True:
                if mode:
                    topics = self._conn.get_topic(forum['forum_id'], start, start+count-1, mode)
                else:
                    topics = self._conn.get_topic(forum['forum_id'], start, start+count-1)

                all_ignored = True
                for topic in topics['topics']:
                    t = Thread(topic['topic_id'])
                    t.title = unicode(str(topic['topic_title']), 'utf-8')
                    t.date = self._get_time(topic)
                    if not unread or topic.get('new_post'):
                        all_ignored = False
                        yield t
                start += count
                if start >= topics['total_topic_num'] or all_ignored:
                    break

        def process_forum(forum, prefix):
            if (not unread or forum.get('new_post', True)) and not forum['sub_only']:
                for mode in ('TOP', 'ANN', None):
                    for thread in browse_forum_mode(forum, prefix, mode):
                        yield thread

            for child in forum.get('child', []):
                for thread in process_forum(child, "%s.%s" % (prefix, child['forum_name'])):
                    yield thread

        for forum in self._conn.get_forum():
            for thread in process_forum(forum, "%s" % forum['forum_name']):
                yield thread

    def iter_unread_messages(self):
        for thread in self.iter_threads(unread=True):
            self.fill_thread(thread, ['root'], unread=True)
            for message in thread.iter_all_messages():
                if message.flags & Message.IS_UNREAD:
                    yield message


    def set_message_read(self, message):
        # No-op: the underlying forum will mark topics as read as we read them
        pass

    OBJECTS = {Thread: fill_thread}
