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


from datetime import datetime
import logging
import re
import os
import sys
import codecs
from threading import Thread, Event
from math import log
import urlparse
import urllib
from random import randint, choice

from irc.bot import SingleServerIRCBot
import mechanize
from mechanize import _headersutil as headersutil
from mechanize._html import EncodingFinder

from weboob.core import Weboob
from weboob.tools.browser import StandardBrowser, BrowserUnavailable
from weboob.tools.misc import get_backtrace
from weboob.tools.misc import to_unicode
from weboob.tools.storage import StandardStorage
from weboob.tools.application.base import ApplicationStorage

IRC_CHANNELS = os.getenv('BOOBOT_CHANNELS', '#weboob').split(',')
IRC_NICKNAME = os.getenv('BOOBOT_NICKNAME', 'boobot')
IRC_SERVER = os.getenv('BOOBOT_SERVER', 'chat.freenode.net')
IRC_IGNORE = [re.compile(i) for i in os.getenv('BOOBOT_IGNORE', '!~?irker@').split(',')]
STORAGE_FILE = os.getenv('BOOBOT_STORAGE', 'boobot.storage')


def fixurl(url):
    url = to_unicode(url)

    # remove javascript crap
    url = url.replace('/#!/', '/')

    # parse it
    parsed = urlparse.urlsplit(url)

    # divide the netloc further
    userpass, at, hostport = parsed.netloc.rpartition('@')
    user, colon1, pass_ = userpass.partition(':')
    host, colon2, port = hostport.partition(':')

    # encode each component
    scheme = parsed.scheme.encode('utf8')
    user = urllib.quote(user.encode('utf8'))
    colon1 = colon1.encode('utf8')
    pass_ = urllib.quote(pass_.encode('utf8'))
    at = at.encode('utf8')
    host = host.encode('idna')
    colon2 = colon2.encode('utf8')
    port = port.encode('utf8')
    path = '/'.join(pce.encode('utf8') for pce in parsed.path.split('/'))
    # while valid, it is most likely an error
    path = path.replace('//', '/')
    query = parsed.query.encode('utf8')
    fragment = parsed.fragment.encode('utf8')

    # put it back together
    netloc = ''.join((user, colon1, pass_, at, host, colon2, port))
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


class HeadRequest(mechanize.Request):
    def get_method(self):
        return "HEAD"


class BoobotBrowser(StandardBrowser):
    ENCODING = None
    DEFAULT_TIMEOUT = 3

    def urlinfo(self, url, maxback=2):
        if urlparse.urlsplit(url).netloc == 'mobile.twitter.com':
            url = url.replace('mobile.twitter.com', 'twitter.com', 1)
        try:
            r = self.openurl(HeadRequest(url), _tries=2, _delay=0.2)
            body = False
        except BrowserUnavailable as e:
            if u'HTTP Error 501' in unicode(e) or u'HTTP Error 405' in unicode(e):
                r = self.openurl(url, _tries=2, _delay=0.2)
                body = True
            elif u'HTTP Error 404' in unicode(e) \
                    and maxback and not url[-1].isalnum():
                return self.urlinfo(url[:-1], maxback-1)
            else:
                raise e
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
            if not body:
                r = self.openurl(url, _tries=2, _delay=0.2)
            # update size has we might not have it from headers
            size = len(r.read())
            hsize = self.human_size(size)
            r.seek(0)

            encoding = EncodingFinder('windows-1252').encoding(r).lower()
            try:
                h = self.get_document(r, parser='lxml', encoding=encoding)
                for meta in h.xpath('//head/meta'):
                    # meta http-equiv=content-type content=...
                    if meta.attrib.get('http-equiv', '').lower() == 'content-type':
                        for k, v in headersutil.split_header_words([meta.attrib.get('content', '')]):
                            if k == 'charset':
                                encoding = v
                    # meta charset=...
                    encoding = meta.attrib.get('charset', encoding).lower()
            except Exception as e:
                print e
            finally:
                r.seek(0)
            if encoding == 'iso-8859-1' or not encoding:
                encoding = 'windows-1252'
            try:
                codecs.lookup(encoding)
            except LookupError:
                encoding = 'windows-1252'

            try:
                h = self.get_document(r, parser='lxml', encoding=encoding)
                for title in h.xpath('//head/title'):
                    title = to_unicode(title.text_content()).strip()
                    title = ' '.join(title.split())
                if urlparse.urlsplit(url).netloc.endswith('twitter.com'):
                    for title in h.getroot().cssselect('.permalink-tweet .tweet-text'):
                        title = to_unicode(title.text_content()).strip()
                        title = ' '.join(title.splitlines())
            except AssertionError as e:
                # invalid HTML
                print e

        return content_type, hsize, title

    def human_size(self, size):
        if size:
            units = ('B', 'KiB', 'MiB', 'GiB',
                     'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
            exponent = int(log(size, 1024))
            return "%.1f %s" % (float(size) / pow(1024, exponent), units[exponent])
        return '0 B'


class MyThread(Thread):
    daemon = True

    def __init__(self, bot):
        Thread.__init__(self)
        self.weboob = Weboob(storage=StandardStorage(STORAGE_FILE))
        self.weboob.load_backends()
        self.bot = bot
        self.bot.set_weboob(self.weboob)

    def run(self):
        for ev in self.bot.joined.itervalues():
            ev.wait()

        self.weboob.repeat(300, self.check_board)
        self.weboob.repeat(600, self.check_dlfp)

        self.weboob.loop()

    def find_keywords(self, text):
        for word in [
            'weboob', 'videoob', 'havesex', 'havedate', 'monboob', 'boobmsg',
            'flatboob', 'boobill', 'pastoob', 'radioob', 'translaboob', 'traveloob', 'handjoob',
            'boobathon', 'boobank', 'boobtracker', 'comparoob', 'wetboobs',
            'webcontentedit', 'weboorrents', u'sàt', u'salut à toi', 'assnet',
                'budget insight', 'budget-insight', 'budgetinsight', 'budgea']:
            if word in text.lower():
                return word
        return None

    def check_dlfp(self):
        for backend, msg in self.weboob.do('iter_unread_messages', backends=['dlfp']):
            word = self.find_keywords(msg.content)
            if word is not None:
                url = msg.signature[msg.signature.find('https://linuxfr'):]
                self.bot.send_message('[DLFP] %s talks about %s: %s' % (
                    msg.sender, word, url))
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
        self.weboob.deinit()


class Boobot(SingleServerIRCBot):
    def __init__(self, channels, nickname, server, port=6667):
        SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        # self.connection.add_global_handler('pubmsg', self.on_pubmsg)
        self.connection.add_global_handler('join', self.on_join)
        self.connection.add_global_handler('welcome', self.on_welcome)

        self.mainchannel = channels[0]
        self.joined = dict()
        for channel in channels:
            self.joined[channel] = Event()
        self.weboob = None
        self.storage = None

    def set_weboob(self, weboob):
        self.weboob = weboob
        self.storage = ApplicationStorage('boobot', weboob.storage)
        self.storage.load({})

    def on_welcome(self, c, event):
        for channel in self.joined.keys():
            c.join(channel)

    def on_join(self, c, event):
        # irclib 5.0 compatibility
        if callable(event.target):
            channel = event.target()
        else:
            channel = event.target
        self.joined[channel].set()

    def send_message(self, msg, channel=None):
        for m in msg.splitlines():
            self.connection.privmsg(to_unicode(channel or self.mainchannel), to_unicode(m)[:450])

    def on_pubmsg(self, c, event):
        # irclib 5.0 compatibility
        if callable(event.arguments):
            text = ' '.join(event.arguments())
            channel = event.target()
            nick = event.source()
        else:
            text = ' '.join(event.arguments)
            channel = event.target
            nick = event.source
        for ignore in IRC_IGNORE:
            if ignore.search(nick):
                return
        for m in re.findall('([\w\d_\-]+@\w+)', text):
            for msg in self.on_boobid(m):
                self.send_message(msg, channel)
        for m in re.findall(u'(https?://[^\s\xa0+]+)', text):
            for msg in self.on_url(m):
                self.send_message(msg, channel)

        m = re.match('^%(?P<cmd>\w+)(?P<args>.*)$', text)
        if m and hasattr(self, 'cmd_%s' % m.groupdict()['cmd']):
            getattr(self, 'cmd_%s' %  m.groupdict()['cmd'])(nick, channel, m.groupdict()['args'].strip())

    def cmd_addquote(self, nick, channel, text):
        quotes = self.storage.get(channel, 'quotes', default=[])
        quotes.append({'author': nick, 'timestamp': datetime.now(), 'text': text})
        self.storage.set(channel, 'quotes', quotes)
        self.storage.save()

    def cmd_searchquote(self, nick, channel, text):
        try:
            pattern = re.compile(text, re.IGNORECASE)
        except Exception as e:
            self.send_message(str(e), channel)
            return

        quotes = []
        for quote in self.storage.get(channel, 'quotes', default=[]):
            if pattern.search(quote['text']):
                quotes.append(quote)

        try:
            quote = choice(quotes)
        except IndexError:
            self.send_message('No match', channel)
        else:
            self.send_message('%s' % quote['text'], channel)

    def cmd_getquote(self, nick, channel, text):
        quotes = self.storage.get(channel, 'quotes', default=[])
        if len(quotes) == 0:
            return

        try:
            n = int(text)
        except ValueError:
            n = randint(0, len(quotes)-1)

        try:
            quote = quotes[n]
        except IndexError:
            self.send_message('Unable to find quote #%s' % n, channel)
        else:
            self.send_message('[%s] %s' % (n, quote['text']), channel)

    def on_boobid(self, boobid):
        _id, backend_name = boobid.split('@', 1)
        if backend_name in self.weboob.backend_instances:
            backend = self.weboob.backend_instances[backend_name]
            for cap in backend.iter_caps():
                func = 'obj_info_%s' % cap.__name__[4:].lower()
                if hasattr(self, func):
                    try:
                        for msg in getattr(self, func)(backend, _id):
                            yield msg
                    except Exception as e:
                        print get_backtrace()
                        yield u'Oops: [%s] %s' % (type(e).__name__, e)
                    break

    def on_url(self, url):
        url = fixurl(url)
        try:
            content_type, hsize, title = BoobotBrowser().urlinfo(url)
            if title:
                yield u'URL: %s' % title
            elif hsize:
                yield u'URL (file): %s, %s' % (content_type, hsize)
            else:
                yield u'URL (file): %s' % content_type
        except BrowserUnavailable as e:
            yield u'URL (error): %s' % e
        except Exception as e:
            print get_backtrace()
            yield u'Oops: [%s] %s' % (type(e).__name__, e)

    def obj_info_video(self, backend, id):
        v = backend.get_video(id)
        if v:
            yield u'Video: %s (%s)' % (v.title, v.duration)

    def obj_info_housing(self, backend, id):
        h = backend.get_housing(id)
        if h:
            yield u'Housing: %s (%sm² / %s%s)' % (h.title, h.area, h.cost, h.currency)


def main():
    logging.basicConfig(level=logging.DEBUG)
    bot = Boobot(IRC_CHANNELS, IRC_NICKNAME, IRC_SERVER)

    thread = MyThread(bot)
    thread.start()

    try:
        bot.start()
    except KeyboardInterrupt:
        print "Stopped."

    thread.stop()

if __name__ == "__main__":
    sys.exit(main())
