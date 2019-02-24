# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.browser.browsers import APIBrowser, ClientError
from weboob.tools.date import datetime
from weboob.tools.decorators import retry


__all__ = ['MailinatorBrowser']


class MailinatorBrowser(APIBrowser):
    BASEURL = 'https://www.mailinator.com'
    ENCODING = 'utf-8'

    @retry(ClientError)
    def get_mails(self, boxid, after=None):
        mails = self.request('/api/webinbox2?x=0&public_to=%s' % boxid)

        for mail in mails['public_msgs']:
            d = {
                'id': mail['id'],
                'from': mail['fromfull'],
                'to': mail['to'],
                'from_name': mail['from'],
                'datetime': frommillis(mail['time']),
                'subject': mail['subject'],
                'box': boxid
            }
            yield d

    @retry(ClientError)
    def get_mail_content(self, mailid):
        data = self.request('/fetchmail?msgid=%s&zone=public' % mailid)['data']
        if 'parts' not in data:
            return 'text', ''

        for part in data['parts']:
            content_type = part['headers'].get('content-type', '')
            if content_type.startswith('text/plain'):
                return 'text', part['body']
            elif content_type.startswith('text/html'):
                return 'html', part['body']

        return 'text', ''


def frommillis(millis):
    return datetime.fromtimestamp(millis / 1000)
