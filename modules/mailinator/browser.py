# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.browser import BaseBrowser, BrowserBanned
from weboob.tools.date import datetime
from weboob.tools.parsers.jsonparser import json
import lxml.html
import time


__all__ = ['MailinatorBrowser']


class MailinatorBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'mailinator.com'
    ENCODING = 'utf-8'

    def __init__(self, *args, **kw):
        kw['parser'] = 'raw'
        BaseBrowser.__init__(self, *args, **kw)

    def _get_unicode(self, url):
        return self.get_document(self.openurl(url)).decode(self.ENCODING, 'replace')

    def _get_json(self, url):
        j = json.loads(self._get_unicode(url))
        if 'rate' in j:
            # shit, we've been banned...
            raise BrowserBanned('Flood - Banned for today')
        return j

    def get_mails(self, boxid, after=None):
        box = self._get_json('http://mailinator.com/useit?box=%s&time=%s' % (boxid, millis()))
        address = box['address']

        mails = self._get_json('http://mailinator.com/grab?inbox=%s&address=%s' % (boxid, address))
        for mail in mails['maildir']:
            d = {'id': mail['id'], 'from': mail['fromfull'], 'to': mail['to'], 'from_name': mail['from'], 'datetime': frommillis(mail['time']), 'subject': mail['subject'], 'read': mail['been_read'], 'box': (boxid, address)}
            yield d

    def get_mail_content(self, mailid):
        frame = self._get_unicode('http://mailinator.com/rendermail.jsp?msgid=%s&time=%s' % (mailid, millis())).strip()
        if not len(frame):
            # likely we're banned
            return ''
        doc = lxml.html.fromstring(frame)
        divs = doc.cssselect('.mailview')
        return divs[0].text_content().strip()

def millis():
    return int(time.time() * 1000)

def frommillis(millis):
    return datetime.fromtimestamp(millis / 1000)
