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

from weboob.browser import DomainBrowser
from weboob.tools.date import datetime


__all__ = ['GuerrillamailBrowser']


class GuerrillamailBrowser(DomainBrowser):
    BASEURL = 'https://www.guerrillamail.com'

    def get_mails(self, boxid):
        params = {'email_user': boxid, 'lang': 'en', 'domain': 'guerrillamail.com'}
        d = self.open('https://www.guerrillamail.com/ajax.php?f=set_email_user', data=params).json()

        d = self.open('https://www.guerrillamail.com/ajax.php?f=get_email_list&offset=0&domain=guerrillamail.com').json()
        for m in d['list']:
            info = {}
            info['id'] = m['mail_id']
            info['from'] = m['mail_from']
#            info['to'] = m['mail_recipient']
            info['to'] = '%s@guerrillamail.com' % boxid
            info['subject'] = m['mail_subject']
            info['datetime'] = datetime.fromtimestamp(int(m['mail_timestamp']))
            info['read'] = bool(int(m['mail_read']))
            yield info

    def get_mail_content(self, mailid):
        d = self.open('https://www.guerrillamail.com/ajax.php?f=fetch_email&email_id=mr_%s&domain=guerrillamail.com' % mailid).json()
        return d['mail_body']

    def send_mail(self, from_, to, subject, body):
        params = {'from': from_, 'to': to, 'subject': subject, 'body': body, 'attach': '', 'domain': 'guerrillamail.com'}
        self.open('https://www.guerrillamail.com/ajax.php?f=send_email', data=params)
