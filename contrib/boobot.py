#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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


import logging
import re
import sys
from threading import Thread, Event
from math import log

from irc.bot import SingleServerIRCBot
import mechanize
from mechanize import _headersutil as headersutil
import lxml.html

from weboob.core import Weboob
from weboob.tools.browser import StandardBrowser, BrowserUnavailable
from weboob.tools.misc import get_backtrace
from weboob.tools.misc import to_unicode
from weboob.tools.storage import StandardStorage

IRC_CHANNEL = '#weboob'
IRC_NICKNAME = 'booboot'
IRC_SERVER = 'chat.freenode.net'
STORAGE_FILE = 'boobot.storage'


class HeadRequest(mechanize.Request):
    def get_method(self):
        return "HEAD"


class BoobotBrowser(StandardBrowser):
    def urlinfo(self, url):
        b = StandardBrowser()
        r = b.openurl(HeadRequest(url))
        headers = r.info()
        content_type = headers.get('Content-Type')
        try:
            size = int(headers.get('Content-Length'))
            hsize = self.human_size(size)
        except TypeError:
            size = None
            hsize = None
        is_html = headersutil.is_html([content_type], url, True)
        title = None
        if is_html:
            h = lxml.html.fromstring(self.readurl(url))
            for title in h.xpath('//head/title'):
                title = to_unicode(title.text_content())
        return content_type, hsize, title

    def human_size(self, size):
        if size:
            units = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
            exponent = int(log(size, 1024))
            return "%.1f %s" % (float(size) / pow(1024, exponent), units[exponent])
        return '0 B'


class MyThread(Thread):
    def __init__(self, bot):
        Thread.__init__(self)
        self.weboob = Weboob(storage=StandardStorage(STORAGE_FILE))
        self.weboob.load_backends()
        self.bot = bot
        self.bot.weboob = self.weboob

    def run(self):
        self.bot.joined.wait()

        self.weboob.repeat(300, self.check_board)
        self.weboob.repeat(600, self.check_dlfp)

        self.weboob.loop()

    def find_keywords(self, text):
        for word in ['weboob', 'videoob', 'havesex', 'havedate', 'monboob', 'boobmsg',
                     'flatboob', 'boobill', 'pastoob', 'radioob', 'translaboob', 'traveloob',
                     'boobathon', 'boobank', 'boobtracker', 'comparoob', 'wetboobs',
                     'webcontentedit', 'weboorrents', u'sàt', u'salut à toi', 'ass2m',
                     'budget insight', 'budget-insight', 'budgetinsight', 'budgea']:
            if word in text.lower():
                return word
        return None

    def check_dlfp(self):
        for backend, msg in self.weboob.do('iter_unread_messages', backends=['dlfp']):
            word = self.find_keywords(msg.content)
            if word is not None:
                url = msg.signature[msg.signature.find('https://linuxfr'):]
                self.bot.send_message('[DLFP] %s talks about %s: %s' % (msg.sender, word, url))
            backend.set_message_read(msg)

    def check_board(self):
        def iter_messages(backend):
            with backend.browser:
                return backend.browser.iter_new_board_messages()

        for backend, msg in self.weboob.do(iter_messages, backends=['dlfp']):
            word = self.find_keywords(msg.message)
            if word is not None and msg.login != 'moules':
                message = msg.message.replace(word, '\002%s\002' % word)
                self.bot.send_message('[DLFP] <%s> %s' % (msg.login, message))

    def stop(self):
        self.weboob.want_stop()


class TestBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        #self.connection.add_global_handler('pubmsg', self.on_pubmsg)
        self.connection.add_global_handler('join', self.on_join)
        self.connection.add_global_handler('welcome', self.on_welcome)

        self.channel = channel
        self.joined = Event()
        self.weboob = None

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_join(self, c, e):
        self.joined.set()

    def send_message(self, msg):
        self.connection.privmsg(self.channel, msg)

    def on_pubmsg(self, c, event):
        # irclib 5.0 compatibility
        if callable(event.arguments):
            text = ' '.join(event.arguments())
        else:
            text = ' '.join(event.arguments)
        for m in re.findall('([\w\d_\-]+@\w+)', text):
            self.on_boobid(m)
        for m in re.findall('(https?://\S+)', text):
            self.on_url(m)

    def on_boobid(self, boobid):
        _id, backend_name = boobid.split('@', 1)
        if backend_name in self.weboob.backend_instances:
            backend = self.weboob.backend_instances[backend_name]
            for cap in backend.iter_caps():
                func = 'obj_info_%s' % cap.__name__[4:].lower()
                if hasattr(self, func):
                    try:
                        getattr(self, func)(backend, _id)
                    except Exception, e:
                        print get_backtrace()
                        self.send_message('Oops: [%s] %s' % (type(e).__name__, e))
                    break

    def on_url(self, url):
        try:
            content_type, hsize, title = BoobotBrowser().urlinfo(url)
            if title:
                self.send_message(u'URL: %s' % title)
            elif hsize:
                self.send_message(u'URL (file): %s, %s' % (content_type, hsize))
            else:
                self.send_message(u'URL (file): %s' % content_type)
        except BrowserUnavailable as e:
            self.send_message(u'URL (error): %s' % e)

    def obj_info_video(self, backend, id):
        v = backend.get_video(id)
        if v:
            self.send_message(u'Video: %s (%s)' % (v.title, v.duration))

    def obj_info_housing(self, backend, id):
        h = backend.get_housing(id)
        if h:
            self.send_message(u'Housing: %s (%sm² / %s%s)' % (h.title, h.area, h.cost, h.currency))


def main():
    logging.basicConfig(level=logging.DEBUG)
    bot = TestBot(IRC_CHANNEL, IRC_NICKNAME, IRC_SERVER)

    thread = MyThread(bot)
    thread.start()

    try:
        bot.start()
    except KeyboardInterrupt:
        print "Stopped."

    thread.stop()

if __name__ == "__main__":
    sys.exit(main())
