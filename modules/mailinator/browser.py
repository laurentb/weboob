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


from weboob.deprecated.browser import Browser, BrowserBanned
from weboob.tools.date import datetime
from weboob.deprecated.browser.parsers.jsonparser import json
import lxml.html
import time
import email


__all__ = ['MailinatorBrowser']


class MailinatorBrowser(Browser):
    PROTOCOL = 'http'
    DOMAIN = 'mailinator.com'
    ENCODING = 'utf-8'

    def __init__(self, *args, **kw):
        kw['parser'] = 'raw'
        Browser.__init__(self, *args, **kw)

    def _get_unicode(self, url):
        return self.get_document(self.openurl(url)).decode(self.ENCODING, 'replace')

    def _get_json(self, url):
        j = json.loads(self._get_unicode(url))
        if 'rate' in j:
            # shit, we've been banned...
            raise BrowserBanned('Flood - Banned for today')
        return j

    def get_mails(self, boxid, after=None):
        mails = self._get_json('http://mailinator.com/api/webinbox?to=%s&time=%d' % (boxid, millis()))
        for mail in mails['messages']:
            d = {'id': mail['id'],
                 'from': mail['fromfull'],
                 'to': mail['to'],
                 'from_name': mail['from'],
                 'datetime': frommillis(mail['time']),
                 'subject': mail['subject'],
                 'read': mail['been_read'],
                 'box': boxid
                 }
            yield d

    def get_mail_content(self, mailid):
        frame = self._get_unicode('http://mailinator.com/rendermail.jsp?msgid=%s&time=%s&text=true' % (mailid, millis())).strip()
        if not len(frame):
            # likely we're banned
            return ''
        doc = lxml.html.fromstring(frame)
        pre = doc.xpath('//pre')[0]
        msg = email.message_from_string(pre.text_content().strip().encode('utf-8'))
        if msg.is_multipart():
            return msg.get_payload(0).get_payload()

        return msg.get_payload()


def millis():
    return int(time.time() * 1000)


def frommillis(millis):
    return datetime.fromtimestamp(millis / 1000)
