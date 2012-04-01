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
from ircbot import SingleServerIRCBot

from weboob.core import Weboob
from weboob.tools.storage import StandardStorage

IRC_CHANNEL = '#weboob'
IRC_NICKNAME = 'boobot'
IRC_SERVER = 'irc.freenode.org'
STORAGE_FILE = 'boobot.storage'

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
        for word in ['weboob', 'videoob', 'havesex', 'havedate', u'sàt', u'salut à toi']:
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
        try:
            backend = self.weboob.backend_instances['dlfp']
        except KeyError:
            return

        with backend.browser:
            for msg in backend.browser.iter_new_board_messages():
                word = self.find_keywords(msg.message)
                if word is not None:
                    self.bot.send_message('[DLFP] %s talks about %s on the board' % (msg.login, word))

    def stop(self):
        self.weboob.want_stop()

class TestBot(SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname + "`")
        self.channel = channel
        self.joined = Event()
        self.weboob = None

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_join(self, c, e):
        self.joined.set()

    def send_message(self, msg):
        self.connection.privmsg(self.channel, msg.encode("UTF-8"))

    def on_pubmsg(self, channel, event):
        text = ' '.join(event.arguments())
        for m in re.findall('([\w\d_\-]+@\w+)', text):
            id, backend_name = m.split('@', 1)
            if backend_name in self.weboob.backend_instances:
                backend = self.weboob.backend_instances[backend_name]
                for cap in backend.iter_caps():
                    func = 'obj_info_%s' % cap.__name__[4:].lower()
                    if hasattr(self, func):
                        try:
                            getattr(self, func)(backend, id)
                        except Exception, e:
                            self.send_message('Oops: [%s] %s' % (type(e).__name__, e))
                        break

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
        bot.start();
    except KeyboardInterrupt:
        print "Stopped."

    thread.stop()

if __name__ == "__main__":
    sys.exit(main())
