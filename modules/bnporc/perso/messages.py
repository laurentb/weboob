# -*- coding: utf-8 -*-

# Copyright(C) 2012 Laurent Bachelier
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


from weboob.deprecated.browser import Page, BrokenPageError
from weboob.capabilities.messages import Message, Thread
from weboob.capabilities.base import NotLoaded
from weboob.tools.capabilities.messages.genericArticle import try_drop_tree

import re
from datetime import datetime

from lxml.html import make_links_absolute


class MessagesPage(Page):
    def iter_threads(self):
        table = self.parser.select(self.document.getroot(), 'table#listeMessages', 1)
        for tr in table.xpath('./tr'):
            if tr.attrib.get('class', '') not in ('msgLu', 'msgNonLu'):
                continue
            author = unicode(self.parser.select(tr, 'td.colEmetteur', 1).text)
            link = self.parser.select(tr, 'td.colObjet a', 1)
            date_raw = self.parser.select(tr, 'td.colDate1', 1).attrib['data']
            jsparams = re.search('\((.+)\)', link.attrib['onclick']).groups()[0]
            jsparams = [i.strip('\'" ') for i in jsparams.split(',')]
            page_id, _id, unread = jsparams
            # this means unread on the website
            unread = False if unread == "false" else True
            # 2012/02/29:01h30min45sec
            dt_match = re.match('(\d+)/(\d+)/(\d+):(\d+)h(\d+)min(\d+)sec', date_raw).groups()
            dt_match = [int(d) for d in dt_match]
            thread = Thread(_id)
            thread._link_id = (page_id, unread)
            thread.date = datetime(*dt_match)
            thread.title = unicode(link.text)
            message = Message(thread, 0)
            message.set_empty_fields(None)
            message.flags = message.IS_HTML
            message.title = thread.title
            message.date = thread.date
            message.sender = author
            message.content = NotLoaded  # This is the only thing we are missing
            thread.root = message
            yield thread


class MessagePage(Page):
    def get_content(self):
        """
        Get the message content.
        This page has a date, but it is less precise than the main list page,
        so we only use it for the message content.
        """
        try:
            content = self.parser.select(self.document.getroot(),
                    'div.txtMessage div.contenu', 1)
        except BrokenPageError:
            # This happens with some old messages (2007)
            content = self.parser.select(self.document.getroot(), 'div.txtMessage', 1)

        content = make_links_absolute(content, self.url)
        try_drop_tree(self.parser, content, 'script')
        return self.parser.tostring(content)
