# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re

from datetime import datetime

from weboob.tools.browser import BasePage


__all__ = ['BoardPage']


class Message(object):
    def __init__(self, browser, board, id, filename=u'', url=u''):
        self.id = id
        self.browser = browser
        self.board = board
        self.filename = filename
        self.datetime = datetime.now()
        self.url = url
        self.author = u''
        self.text = u''
        self.comments = []

    def add_comment(self, div):
        comment = Message(self.browser, self.board, int(div.attrib.get('id', '')))
        comment.author = div.cssselect('span.commentpostername')[0].text
        comment.text = self.browser.parser.tostring(div.find('blockquote'))
        self.comments.append(comment)

    def __repr__(self):
        return '<Message id=%s filename=%s url=%s comments=%d>' % (self.id, self.filename, self.url, len(self.comments))


class BoardPage(BasePage):
    URL_REGEXP = re.compile('http://boards.4chan.org/(\w+)/')

    def on_loaded(self):
        self.articles = []

        m = self.URL_REGEXP.match(self.url)
        if m:
            self.board = m.group(1)
        else:
            self.logger.warning('Unable to find board')
            self.board = 'unknown'

        forms = self.document.getroot().cssselect('form')
        form = None

        for f in forms:
            if f.attrib.get('name', '') == 'delform':
                form = f
                break

        if form is None:
            self.logger.warning('No delform :(')

        article = None
        for div in form.getchildren():
            if div.tag == 'span' and div.attrib.get('class', '') == 'filesize':
                url = div.find('a').get('href', '')
                filename = 'unknown.jpg'
                span = div.find('span')
                if span is not None:
                    filename = span.text
                article = Message(self.browser, self.board, 0, filename, url)
                self.articles.append(article)
            if div.tag == 'input' and div.attrib.get('type', 'checkbox') and div.attrib.get('value', 'delete'):
                article.id = int(div.attrib.get('name', '0'))
            if div.tag == 'blockquote':
                article.text = self.browser.parser.tostring(div)
            if div.tag == 'table':
                tags = div.cssselect('td.reply')
                if tags:
                    article.add_comment(tags[0])
